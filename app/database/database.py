from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# 确保数据目录存在
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

# 数据库URL - 使用SQLite
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/gewechat.db"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,  # 设为True可以查看SQL语句，调试时有用
    future=True
)

# 创建会话类
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建Base类
Base = declarative_base()

# 获取数据库会话
async def get_db():
    """每个请求获取一个独立的数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 添加一个生成器函数，用于获取数据库会话
async def get_db_session():
    """异步生成器，用于获取数据库会话"""
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# 初始化数据库（创建表）
async def init_db():
    """初始化数据库，创建所有表"""
    from app.database import models  # 导入所有模型
    
    async with engine.begin() as conn:
        # 在开发阶段可以使用drop_all清空所有表，生产环境应移除
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("数据库初始化完成") 