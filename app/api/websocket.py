from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.websockets.manager import manager
from app.core.auth import verify_session_websocket
import logging

router = APIRouter(prefix="/ws", tags=["websocket"])

logger = logging.getLogger(__name__)

@router.websocket("/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(...),
    chat_id: str = Query("global")
):
    """WebSocket端点，用于实时更新聊天消息"""
    # 验证会话(这需要自定义实现)
    # session_data = await verify_session_websocket(websocket)
    
    try:
        # 接受WebSocket连接
        await manager.connect(websocket, user_id, chat_id)
        
        # 发送欢迎消息
        await manager.send_personal_message(
            {"type": "system", "message": "Connected to chat server"},
            user_id,
            chat_id
        )
        
        # 持续接收消息（可用于双向通信）
        while True:
            try:
                data = await websocket.receive_text()
                # 处理收到的消息（例如可以实现输入状态提示）
                # 这里暂不处理客户端消息
            except WebSocketDisconnect:
                manager.disconnect(user_id, chat_id)
                logger.info(f"WebSocket disconnected: user={user_id}, chat={chat_id}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(user_id, chat_id) 