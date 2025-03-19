from typing import Dict, List, Any
import json
from fastapi import WebSocket, WebSocketDisconnect
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃的WebSocket连接 {user_id: {chat_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, chat_id: str = "global"):
        """建立新的WebSocket连接"""
        await websocket.accept()
        
        # 初始化用户的连接字典（如果不存在）
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        # 保存连接
        self.active_connections[user_id][chat_id] = websocket
        logger.info(f"WebSocket connected: user={user_id}, chat={chat_id}")
    
    def disconnect(self, user_id: str, chat_id: str = "global"):
        """断开WebSocket连接"""
        if user_id in self.active_connections and chat_id in self.active_connections[user_id]:
            del self.active_connections[user_id][chat_id]
            
            # 如果用户没有任何活跃连接，则移除用户
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
            logger.info(f"WebSocket disconnected: user={user_id}, chat={chat_id}")
    
    async def send_personal_message(self, message: Any, user_id: str, chat_id: str = "global"):
        """向特定用户的特定聊天发送消息"""
        if user_id in self.active_connections and chat_id in self.active_connections[user_id]:
            websocket = self.active_connections[user_id][chat_id]
            await websocket.send_text(json.dumps(message))
            logger.debug(f"Message sent to user={user_id}, chat={chat_id}")
    
    async def broadcast(self, message: Any):
        """广播消息给所有连接的WebSocket"""
        disconnected = []
        
        for user_id, chats in self.active_connections.items():
            for chat_id, websocket in chats.items():
                try:
                    await websocket.send_text(json.dumps(message))
                except WebSocketDisconnect:
                    disconnected.append((user_id, chat_id))
        
        # 移除断开的连接
        for user_id, chat_id in disconnected:
            self.disconnect(user_id, chat_id)

# 创建全局连接管理器
manager = ConnectionManager()

async def notify_clients(message_data: Dict[str, Any]):
    """通知前端客户端有新消息"""
    # 这里可以根据消息类型和内容，决定通知哪些用户
    # 简单实现：广播给所有连接的客户端
    await manager.broadcast({
        "type": "new_message",
        "data": message_data
    }) 