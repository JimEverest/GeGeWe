from pydantic_settings import BaseSettings
import os
from pathlib import Path

# 确保配置目录存在
CONFIG_DIR = Path("./config")
CONFIG_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Gewechat Web Client"
    DEBUG: bool = True
    APP_VERSION: str = "0.1.0"  # 添加版本号字段
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/gewechat.db"  # 添加数据库URL字段
    
    # 安全配置
    AUTH_CODE: str = "your-secret-auth-code"  # 预设授权码
    SECRET_KEY: str = "your-very-secure-secret-key-for-session-encryption"
    
    # Gewechat配置
    GEWE_TOKEN: str = "484e412380744c7eac7690045a23c875"
    CALLBACK_URL: str = "https://c260-172-235-216-15.ngrok-free.app/wechat/callback"  # 使用 ngrok 生成的 URL
    
    # Gewechat API 配置
    GEWE_API_URL: str = "http://1113.44.176.165:2531/v2/api/"
    
    # 新增配置项
    APP_ID: str = "wx_1Evjqp0uqLMBC8HLZFyX0"  # 默认值或初始值
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量字段

# 创建全局设置实例
settings = Settings() 