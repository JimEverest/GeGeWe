import os
import shutil

def create_directory(path):
    """创建目录，如果已存在则跳过"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"创建目录: {path}")
    else:
        print(f"目录已存在: {path}")

def create_file(path, content=""):
    """创建文件，如果已存在则跳过"""
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"创建文件: {path}")
    else:
        print(f"文件已存在: {path}")

def create_init_file(directory):
    """在目录中创建__init__.py文件"""
    create_file(os.path.join(directory, "__init__.py"))

def create_project_structure():
    """创建项目目录结构和基础文件"""
    # 根目录
    root_dir = "."
    
    # 主要目录
    main_dirs = [
        "app",
        "app/api",
        "app/core",
        "app/database",
        "app/services",
        "app/websockets",
        "static",
        "static/css",
        "static/js",
        "static/images",
        "templates",
        "tests",
        "tests/test_api",
        "tests/test_services",
        "scripts"
    ]
    
    # 创建主要目录
    for directory in main_dirs:
        create_directory(os.path.join(root_dir, directory))
        if directory.startswith("app") or directory.startswith("tests"):
            create_init_file(os.path.join(root_dir, directory))
    
    # 创建基础配置文件
    create_file(os.path.join(root_dir, ".env.example"), 
"""# 应用配置
APP_NAME=Gewechat Web Client
DEBUG=True

# 安全配置
AUTH_CODE=your-secret-auth-code
SECRET_KEY=your-very-secure-secret-key-for-session-encryption

# Gewechat配置
GEWE_TOKEN=
CALLBACK_URL=
""")
    
    create_file(os.path.join(root_dir, "requirements.txt"),
"""fastapi==0.104.1
uvicorn==0.23.2
sqlalchemy==2.0.23
pydantic==2.4.2
python-dotenv==1.0.0
aiosqlite==0.19.0
websockets==11.0.3
python-multipart==0.0.6
httpx==0.25.1
pytest==7.4.3
pytest-asyncio==0.21.1
""")
    
    create_file(os.path.join(root_dir, "README.md"),
"""# Gewechat Web Client

基于Gewechat API的Web微信客户端，提供扫码登录、消息收发、联系人管理等功能。

## 功能特点

- 扫码登录与状态管理
- 消息接收与发送
- 联系人与群组管理
- 多媒体消息支持

## 安装与使用

1. 克隆仓库
2. 安装依赖: `pip install -r requirements.txt`
3. 配置环境变量: 复制`.env.example`为`.env`并修改
4. 启动应用: `uvicorn app.main:app --reload`

## 技术栈

- 后端: FastAPI
- 数据库: SQLite
- 前端: 原生JS/CSS
""")
    
    # 创建入口文件
    create_file(os.path.join(root_dir, "app/main.py"),
"""from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, callback, wechat
from app.core.auth import verify_session
from app.database.database import init_db

app = FastAPI(title="Gewechat Web Client")

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
    await init_db()

# 公共接口（不需要验证）
app.include_router(auth.router)

# 需要验证会话的接口
app.include_router(callback.router)
app.include_router(
    wechat.router,
    dependencies=[Depends(verify_session)]  # 所有微信API需要验证会话
)

@app.get("/")
async def root():
    return {"message": "Gewechat Web Client API is running"}
""")

    # 创建一个启动脚本
    create_file(os.path.join(root_dir, "run.py"),
"""import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
""")

    print("项目结构创建完成！")

if __name__ == "__main__":
    create_project_structure() 