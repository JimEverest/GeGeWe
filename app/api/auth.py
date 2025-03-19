from fastapi import APIRouter, HTTPException, Depends, Response, status, Form
from fastapi.security import APIKeyCookie
from app.core.auth import create_session, verify_auth_code, get_password_hash
from app.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(auth_code: str = Form(...), response: Response = None):
    """
    通过认证码登录系统
    """
    if verify_auth_code(auth_code):
        # 认证成功，创建会话
        session_id = create_session()
        
        # 设置Cookie
        if response:
            response.set_cookie(
                key="session",
                value=session_id,
                httponly=True,
                max_age=86400,  # 24小时
                secure=False,  # 开发环境设为False
                samesite="lax"
            )
        
        return {"status": "success", "message": "登录成功"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证码无效"
    )

@router.post("/logout")
async def logout(response: Response):
    """
    登出系统并清除会话
    """
    response.delete_cookie(key="session")
    return {"status": "success", "message": "已登出"} 