from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Message, MediaFile, Contact
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_message(self, message_data: dict) -> dict:
        """处理接收到的回调消息"""
        try:
            # 消息排重 - 检查是否已存在相同的消息
            if await self._is_duplicate_message(message_data):
                logger.info("检测到重复消息，跳过处理")
                return {"status": "duplicate", "message": "重复消息已跳过"}
            
            # 解析消息
            parsed_message = self._parse_message(message_data)
            
            # 存储消息到数据库
            message_id = await self._save_message(parsed_message)
            
            # 处理媒体消息（如果有）
            if parsed_message.get("type") in [3, 4, 5, 6]:  # 图片、视频、语音、文件
                await self._process_media_message(parsed_message, message_id)
            
            return {"status": "success", "message_id": message_id}
            
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            raise
    
    async def _is_duplicate_message(self, message_data: dict) -> bool:
        """检查消息是否重复"""
        app_id = message_data.get("Appid")
        
        # 获取新消息ID (可能位置不同，取决于消息类型)
        new_msg_id = None
        if "Data" in message_data and isinstance(message_data["Data"], dict):
            new_msg_id = message_data["Data"].get("NewMsgId")
        
        if not app_id or not new_msg_id:
            return False
        
        # 查询数据库检查是否存在
        query = await self.db.execute(
            "SELECT id FROM messages WHERE app_id = :app_id AND new_msg_id = :new_msg_id",
            {"app_id": app_id, "new_msg_id": new_msg_id}
        )
        
        result = query.first()
        return result is not None
    
    def _parse_message(self, message_data: dict) -> dict:
        """解析回调消息数据"""
        msg_type = self._determine_message_type(message_data)
        
        # 基础消息数据
        parsed = {
            "type": msg_type,
            "app_id": message_data.get("Appid"),
            "wxid": message_data.get("Wxid"),
            "raw_data": json.dumps(message_data),
            "created_at": datetime.utcnow()
        }
        
        # 从Data中提取详细信息
        data = message_data.get("Data", {})
        if isinstance(data, dict):
            parsed["msg_id"] = data.get("MsgId")
            parsed["new_msg_id"] = data.get("NewMsgId")
            parsed["from_wxid"] = data.get("FromUserName", {}).get("string", "")
            parsed["to_wxid"] = data.get("ToUserName", {}).get("string", "")
            parsed["content"] = data.get("Content", {}).get("string", "")
        
        return parsed
    
    def _determine_message_type(self, message_data: dict) -> int:
        """确定消息类型"""
        type_name = message_data.get("TypeName", "")
        
        if type_name == "AddMsg":
            # 进一步检查消息内容确定具体类型
            data = message_data.get("Data", {})
            if isinstance(data, dict):
                msg_type = data.get("MsgType", 1)
                return msg_type
        
        # 默认为文本消息
        return 1
    
    async def _save_message(self, message_data: dict) -> int:
        """保存消息到数据库"""
        # 创建消息对象
        new_message = Message(
            msg_id=message_data.get("msg_id"),
            new_msg_id=message_data.get("new_msg_id"),
            app_id=message_data.get("app_id"),
            from_wxid=message_data.get("from_wxid"),
            to_wxid=message_data.get("to_wxid"),
            content=message_data.get("content"),
            type=message_data.get("type", 1),
            status=0,  # 未处理
            created_at=message_data.get("created_at"),
            raw_data=message_data.get("raw_data")
        )
        
        # 保存到数据库
        self.db.add(new_message)
        await self.db.commit()
        await self.db.refresh(new_message)
        
        return new_message.id
    
    async def _process_media_message(self, message_data: dict, message_id: int):
        """处理媒体消息，如图片、视频等"""
        # 这里将实现下载和保存媒体文件的逻辑
        pass