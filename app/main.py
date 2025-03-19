from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.auth import router as auth_router
from app.api.callback import router as callback_router
from app.api.wechat import router as wechat_router
from app.core.auth import verify_session
from app.database.database import init_db, engine, Base, AsyncSessionLocal, get_db
from app.core.config import settings
import logging
import asyncio
from app.services.wechat_service import WechatService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import json
import time
from app.api import messages

app = FastAPI(title="Gewechat Web Client")

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用 DEBUG 级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 让httpx库的日志级别更高，避免过多输出
logging.getLogger("httpx").setLevel(logging.WARNING)

# 创建logger
logger = logging.getLogger(__name__)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 启动事件 - 初始化数据库
@app.on_event("startup")
async def startup_event():
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("数据库初始化完成")
    
    # 设置回调URL
    if settings.CALLBACK_URL:
        try:
            # 使用已定义的会话工厂
            async with AsyncSessionLocal() as db:
                wechat_service = WechatService(db)
                await wechat_service.set_callback_url(settings.CALLBACK_URL)
                logger.info(f"已设置回调URL: {settings.CALLBACK_URL}")
        except Exception as e:
            logger.error(f"设置回调URL失败: {str(e)}")

# 公共接口（不需要验证）
app.include_router(auth_router)

# 添加回调路由，不需要验证
app.include_router(
    callback_router,
    prefix="/wechat",
    tags=["wechat_callback"],
    dependencies=[]  # 不需要验证
)

# 需要验证会话的接口
app.include_router(
    wechat_router,
    dependencies=[Depends(verify_session)]  # 所有微信API需要验证会话
)

app.include_router(messages.router)

@app.get("/")
async def root():
    return {"message": "Gewechat Web Client API is running"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"请求开始: {request.method} {request.url.path}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(f"请求结束: {request.method} {request.url.path} - 状态码: {response.status_code} - 处理时间: {process_time:.4f}秒")
    
    return response
