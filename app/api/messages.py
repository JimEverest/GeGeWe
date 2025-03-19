from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.models import Message
from sqlalchemy import select, and_, or_, func, Integer
from typing import Optional, Dict, List, Any
import asyncio
import logging
import json
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/messages", tags=["messages"])
logger = logging.getLogger(__name__)

# 存储每个客户端的新消息通知
message_notifications = {}
# 存储最近处理的消息ID，用于消息排重
processed_messages = {}

@router.get("/poll")
async def poll_messages(
    request: Request,
    last_msg_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """长轮询获取新消息"""
    client_id = f"{request.client.host}:{user_id or 'anonymous'}"
    logger.info(f"收到长轮询请求: client_id={client_id}, last_msg_id={last_msg_id}")
    
    # 设置轮询超时时间（25秒）
    timeout = 25
    start_time = asyncio.get_event_loop().time()
    
    # 首先检查是否有新消息
    new_messages = await get_new_messages(db, last_msg_id, user_id)
    if new_messages:
        logger.info(f"立即返回 {len(new_messages)} 条新消息")
        return {"messages": new_messages}
    
    # 如果没有新消息，则等待新消息通知或超时
    logger.info(f"没有立即可用的消息，等待新消息或超时...")
    
    # 创建一个future用于通知
    if client_id not in message_notifications:
        message_notifications[client_id] = asyncio.Future()
    else:
        # 如果已存在但已完成，则重置
        if message_notifications[client_id].done():
            message_notifications[client_id] = asyncio.Future()
    
    try:
        # 等待通知或超时
        await asyncio.wait_for(
            message_notifications[client_id], 
            timeout=timeout
        )
        logger.info(f"客户端 {client_id} 收到新消息通知")
        
        # 收到通知，检查新消息
        new_messages = await get_new_messages(db, last_msg_id, user_id)
        # 重置通知
        message_notifications[client_id] = asyncio.Future()
        return {"messages": new_messages}
    except asyncio.TimeoutError:
        logger.info(f"客户端 {client_id} 轮询超时，返回空消息列表")
        # 超时，返回空消息列表
        return {"messages": []}
    except Exception as e:
        logger.error(f"轮询消息时出错: {str(e)}", exc_info=True)
        return {"messages": [], "error": str(e)}

async def get_new_messages(db: AsyncSession, last_msg_id: Optional[str] = None, user_id: Optional[str] = None):
    """获取新消息"""
    # logger.info(f"获取新消息: last_msg_id={last_msg_id}, user_id={user_id}")
    
    # 构建基本查询
    query = select(Message).order_by(Message.create_time, Message.id)
    
    # 如果指定了last_msg_id，则只获取更新的消息
    if last_msg_id:
        # 不使用ID比较，而是使用创建时间比较
        # 首先获取last_msg_id对应消息的创建时间
        try:
            last_msg_query = select(Message.create_time).where(Message.id == last_msg_id)
            last_msg_result = await db.execute(last_msg_query)
            last_msg_time = last_msg_result.scalar_one_or_none()
            
            if last_msg_time:
                # logger.info(f"找到last_msg_id={last_msg_id}的消息，创建时间={last_msg_time}")
                # 使用创建时间比较
                query = query.where(
                    or_(
                        Message.create_time > last_msg_time,
                        and_(
                            Message.create_time == last_msg_time,
                            Message.id > last_msg_id
                        )
                    )
                )
            else:
                logger.warning(f"未找到last_msg_id={last_msg_id}的消息，将获取所有消息")
        except Exception as e:
            logger.error(f"查询last_msg_id时出错: {str(e)}")
    
    # 如果指定了user_id，则只获取与该用户相关的消息
    if user_id:
        query = query.where(
            (Message.to_user == user_id) | (Message.from_user == user_id)
        )
    
    # 添加日志，显示完整的SQL查询
    compiled_query = query.compile(dialect=db.bind.dialect, compile_kwargs={"literal_binds": True})
    logger.info(f"SQL查询: {str(compiled_query)}")
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    logger.info(f"查询到 {len(messages)} 条新消息")
    if messages:
        logger.info(f"消息ID: {[msg.id for msg in messages]}")
    
    # 转换为字典列表
    message_list = [message.to_dict() for message in messages]
    
    return message_list

# 在消息回调处理中调用此函数通知所有客户端
async def notify_new_message(user_id: Optional[str] = None):
    """通知客户端有新消息"""
    logger.info(f"通知新消息: user_id={user_id}")
    
    # 如果指定了用户ID，只通知相关客户端
    if user_id:
        for client_id, future in list(message_notifications.items()):
            if user_id in client_id and not future.done():
                future.set_result(True)
                logger.info(f"已通知客户端: {client_id}")
    else:
        # 否则通知所有客户端
        for client_id, future in list(message_notifications.items()):
            if not future.done():
                future.set_result(True)
                logger.info(f"已通知所有客户端: {client_id}")

# 清理过期的通知
async def cleanup_notifications():
    """定期清理过期的通知"""
    current_time = datetime.now()
    for client_id in list(message_notifications.keys()):
        # 如果客户端超过30分钟没有轮询，则移除
        if client_id in message_notifications and message_notifications[client_id].done():
            del message_notifications[client_id]
            logger.info(f"已清理过期通知: {client_id}")

@router.get("/test_poll")
async def test_poll():
    """测试长轮询功能"""
    logger.info("测试长轮询端点被访问")
    return {
        "status": "success", 
        "message": "长轮询测试端点可访问", 
        "timestamp": datetime.now().isoformat()
    }

@router.get("/fetch")
async def fetch_messages(
    last_msg_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取新消息（定时轮询）"""
    logger.info(f"获取新消息: last_msg_id={last_msg_id}, user_id={user_id}")
    
    # 获取数据库中的所有消息ID，方便调试
    try:
        all_msgs_query = select(Message.id, Message.create_time).order_by(Message.create_time)
        if user_id:
            all_msgs_query = all_msgs_query.where(
                (Message.to_user == user_id) | (Message.from_user == user_id)
            )
        all_msgs_result = await db.execute(all_msgs_query)
        all_msgs = all_msgs_result.fetchall()
        
        if all_msgs:
            logger.info(f"数据库中的所有消息: {[(msg.id, msg.create_time) for msg in all_msgs]}")
        else:
            logger.info("数据库中没有消息")
    except Exception as e:
        logger.error(f"获取所有消息时出错: {str(e)}")
    
    # 获取新消息
    new_messages = await get_new_messages(db, last_msg_id, user_id)
    
    logger.info(f"返回 {len(new_messages)} 条新消息")
    if new_messages:
        logger.info(f"返回的消息ID: {[msg['id'] for msg in new_messages]}")
    
    return {"messages": new_messages}

@router.get("/history")
async def get_chat_history(
    user_id: str,
    chat_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取与特定联系人的聊天历史"""
    logger.info(f"获取聊天历史: user_id={user_id}, chat_id={chat_id}, limit={limit}")
    
    # 构建查询
    query = select(Message).where(
        or_(
            and_(Message.from_user == user_id, Message.to_user == chat_id),
            and_(Message.from_user == chat_id, Message.to_user == user_id)
        )
    ).order_by(Message.create_time.desc()).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    logger.info(f"查询到 {len(messages)} 条历史消息")
    
    # 转换为字典列表并按时间正序排列
    message_list = [message.to_dict() for message in messages]
    message_list.reverse()  # 反转列表，使最早的消息在前
    
    return {"messages": message_list}

@router.get("/all")
async def get_all_messages(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取所有消息（用于调试）"""
    logger.info(f"获取所有消息: user_id={user_id}")
    
    # 构建查询
    query = select(Message).order_by(Message.create_time)
    
    if user_id:
        query = query.where(
            (Message.to_user == user_id) | (Message.from_user == user_id)
        )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    logger.info(f"查询到 {len(messages)} 条消息")
    
    # 转换为字典列表
    message_list = [message.to_dict() for message in messages]
    
    return {"messages": message_list} 