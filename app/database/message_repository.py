from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import AsyncSessionLocal
from app.database.models import Message, MediaFile
from app.database.crud import is_duplicate_message as crud_is_duplicate_message
from sqlalchemy.future import select
from typing import Dict, Any, Optional

async def save_message(message_data: Dict[str, Any]) -> Optional[Message]:
    """保存接收到的消息到数据库"""
    async with AsyncSessionLocal() as session:
        # 提取消息数据
        type_name = message_data.get("TypeName")
        app_id = message_data.get("Appid")
        wxid = message_data.get("Wxid")
        
        if type_name == "AddMsg":
            data = message_data.get("Data", {})
            from_user = data.get("FromUserName", {}).get("string", "")
            to_user = data.get("ToUserName", {}).get("string", "")
            content = data.get("Content", {}).get("string", "")
            msg_id = data.get("MsgId", 0)
            new_msg_id = data.get("NewMsgId", 0)
            msg_type = data.get("MsgType", 0)
            
            # 创建消息记录
            message = Message(
                msg_id=str(msg_id),
                new_msg_id=str(new_msg_id),
                app_id=app_id,
                from_wxid=from_user,
                to_wxid=to_user,
                content=content,
                type=msg_type,
                status=0,  # 初始状态：未处理
                raw_data=message_data
            )
            
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message
        
        # 其他类型的消息也可以保存，但格式不同
        return None

async def is_duplicate_message(app_id: str, new_msg_id: str) -> bool:
    """检查是否为重复消息"""
    async with AsyncSessionLocal() as session:
        return await crud_is_duplicate_message(session, app_id, new_msg_id)

async def update_message_status(message_data: Dict[str, Any], status: str, error_msg: str = None) -> None:
    """更新消息处理状态"""
    async with AsyncSessionLocal() as session:
        # 查找消息
        app_id = message_data.get("Appid")
        new_msg_id = message_data.get("Data", {}).get("NewMsgId", 0)
        
        if app_id and new_msg_id:
            result = await session.execute(
                select(Message).filter(
                    Message.app_id == app_id,
                    Message.new_msg_id == str(new_msg_id)
                )
            )
            message = result.scalars().first()
            
            if message:
                # 更新状态
                if status == "processed":
                    message.status = 1
                elif status == "error":
                    message.status = 2
                    # 可以在这里记录错误信息，比如添加一个error_msg字段
                
                await session.commit() 