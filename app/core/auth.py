from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import APIKeyCookie
from app.core.config import settings
from typing import Optional
import secrets
import hashlib
import logging

logger = logging.getLogger(__name__)

# 简单的会话存储 - 生产环境应使用Redis或数据库
session_store = {}

def create_session() -> str:
    """创建新的会话标识符"""
    session_id = secrets.token_hex(16)
    session_store[session_id] = {
        "authenticated": True,
        "created_at": secrets.token_hex(8)  # 简单模拟创建时间
    }
    return session_id

def verify_auth_code(auth_code: str) -> bool:
    """验证授权码"""
    return auth_code == settings.AUTH_CODE

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

async def verify_session(session: Optional[str] = Cookie(None)):
    """验证会话中间件"""
    if not session or session not in session_store:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要有效的会话",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 获取会话数据
    session_data = session_store[session]
    
    # 检查是否已认证
    if not session_data.get("authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的会话",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 返回会话数据，可在后续处理中使用
    return session_data