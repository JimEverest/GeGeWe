from fastapi import APIRouter, Request, Depends, WebSocket, Form
from app.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List
import socket
from app.api.messages import notify_new_message
from app.database.models import Message

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器，不设置前缀
router = APIRouter()

# 存储活跃的WebSocket连接
active_connections: Dict[str, List[WebSocket]] = {}

# 存储最近处理的消息ID，用于消息排重
processed_messages = {}

@router.post("/callback")
async def wechat_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """接收微信消息回调"""
    logger.info("====== 开始处理微信回调 ======")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求URL: {request.url}")
    logger.info(f"请求头: {dict(request.headers)}")
    
    try:
        # 获取原始请求体
        body = await request.json()
        logger.info(f"收到微信消息回调: {json.dumps(body, ensure_ascii=False)}")
        
        # 提取消息类型和数据
        type_name = body.get("TypeName")
        app_id = body.get("Appid")
        wxid = body.get("Wxid")
        data = body.get("Data", {})
        
        # 消息排重处理
        if type_name == "AddMsg" and "NewMsgId" in data:
            new_msg_id = data["NewMsgId"]
            msg_key = f"{app_id}:{new_msg_id}"
            
            # 检查消息是否已处理过
            if msg_key in processed_messages:
                logger.info(f"消息已处理过，跳过: {msg_key}")
                return {"status": "success"}
            
            # 标记消息为已处理
            processed_messages[msg_key] = datetime.now()
            
            # 清理过期的处理记录（保留最近1小时的记录）
            current_time = datetime.now()
            for key in list(processed_messages.keys()):
                if (current_time - processed_messages[key]) > timedelta(hours=1):
                    del processed_messages[key]
        
        # 处理不同类型的消息
        if type_name == "AddMsg":
            # 处理聊天消息
            logger.info(f"收到聊天消息: {json.dumps(data, ensure_ascii=False)}")
            
            # 提取消息详情
            msg_id = data.get("NewMsgId")
            msg_type = data.get("MsgType")
            from_user = data.get("FromUserName", {}).get("string", "")
            to_user = data.get("ToUserName", {}).get("string", "")
            content = data.get("Content", {}).get("string", "")
            create_time = data.get("CreateTime", 0)
            
            logger.info(f"消息ID: {msg_id}, 类型: {msg_type}, 发送者: {from_user}, 接收者: {to_user}")
            logger.info(f"消息内容: {content}")
            
            # 存储消息到数据库
            new_message = Message(
                id=str(msg_id),
                app_id=app_id,
                from_user=from_user,
                to_user=to_user,
                content=content,
                msg_type=msg_type,
                create_time=datetime.fromtimestamp(create_time),
                raw_data=json.dumps(data)
            )
            db.add(new_message)
            await db.commit()
            logger.info(f"消息已存储到数据库: {msg_id}")
            
            # 通知相关用户有新消息（使用长轮询通知）
            await notify_new_message(from_user)  # 通知发送者
            await notify_new_message(to_user)    # 通知接收者
            
        elif type_name == "Offline":
            # 处理离线通知
            logger.warning(f"微信账号 {wxid} 已离线")
            
            # 通知所有客户端
            await notify_new_message()
        
        # 返回成功响应
        logger.info("回调处理成功，返回成功响应")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"处理微信消息回调时出错: {str(e)}", exc_info=True)
        # 即使处理失败，也返回成功以避免重复推送
        return {"status": "success"}
    finally:
        logger.info("====== 结束处理微信回调 ======")

async def broadcast_message(message):
    """广播消息到所有活跃的WebSocket连接"""
    from app.api.wechat import active_connections
    
    logger.info(f"广播消息到 {len(active_connections)} 个客户端")
    logger.info(f"活跃连接: {active_connections.keys()}")
    
    if not active_connections:
        logger.warning("没有活跃的WebSocket连接，消息无法推送")
        return
    
    success_count = 0
    for client_id, connections in active_connections.items():
        logger.info(f"客户端 {client_id} 有 {len(connections)} 个连接")
        for connection in connections:
            try:
                await connection.send_json(message)
                success_count += 1
                logger.info(f"消息已推送到客户端 {client_id}")
            except Exception as e:
                logger.error(f"推送消息到客户端 {client_id} 时出错: {str(e)}", exc_info=True)
    
    logger.info(f"消息广播完成，成功推送到 {success_count} 个连接")

@router.get("/callback")
async def wechat_callback_verification():
    """验证回调URL有效性"""
    logger.info("收到回调URL验证请求")
    return {"status": "success", "message": "Callback URL is valid"}

@router.post("/test_callback")
async def test_callback(
    request: Request
):
    """测试回调接口"""
    try:
        body = await request.json()
        logger.info(f"收到测试回调: {json.dumps(body)}")
        
        # 构建推送消息
        push_message = {
            "type": "chat_message",
            "app_id": "test_app_id",
            "wxid": "test_wxid",
            "data": {
                "MsgId": 1040356095,
                "FromUserName": {
                    "string": "wxid_sender"
                },
                "ToUserName": {
                    "string": "wxid_receiver"
                },
                "MsgType": 1,
                "Content": {
                    "string": "这是一条测试消息"
                },
                "CreateTime": int(datetime.now().timestamp()),
                "NewMsgId": 1765700414095721113
            }
        }
        
        # 推送到所有活跃连接
        await broadcast_message(push_message)
        
        return {"status": "success", "received": body}
    except Exception as e:
        logger.error(f"处理测试回调时出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/test")
async def test_endpoint():
    """测试回调接口是否可访问"""
    logger.info("测试回调接口被访问")
    return {"status": "success", "message": "回调接口可访问"}

@router.post("/send_test_message")
async def send_test_message(
    from_wxid: str = Form(...),
    to_wxid: str = Form(...),
    content: str = Form(...)
):
    """发送测试消息到WebSocket"""
    try:
        # 构建测试消息
        test_message = {
            "type": "chat_message",
            "app_id": "test_app_id",
            "wxid": from_wxid,
            "data": {
                "MsgId": 1040356095,
                "FromUserName": {
                    "string": from_wxid
                },
                "ToUserName": {
                    "string": to_wxid
                },
                "MsgType": 1,
                "Content": {
                    "string": content
                },
                "CreateTime": int(datetime.now().timestamp()),
                "NewMsgId": int(datetime.now().timestamp() * 1000)
            }
        }
        
        # 推送到所有活跃连接
        await broadcast_message(test_message)
        
        return {"status": "success", "message": "测试消息已发送"}
    except Exception as e:
        logger.error(f"发送测试消息时出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/test_broadcast")
async def test_broadcast():
    """测试广播消息"""
    try:
        # 构建测试消息
        test_message = {
            "type": "test_message",
            "message": "这是一条测试广播消息",
            "time": datetime.now().isoformat()
        }
        
        # 推送到所有活跃连接
        await broadcast_message(test_message)
        
        return {"status": "success", "message": "测试消息已广播"}
    except Exception as e:
        logger.error(f"测试广播消息时出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/test_external")
async def test_external_access():
    """测试回调URL是否可从外部访问"""
    try:
        # 获取本机IP地址
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # 获取当前服务器端口
        port = 8000  # 假设服务器运行在8000端口
        
        # 构建回调URL
        callback_url = f"http://{local_ip}:{port}/wechat/callback"
        
        return {
            "status": "success", 
            "message": "此端点可访问", 
            "server_info": {
                "hostname": hostname,
                "local_ip": local_ip,
                "port": port,
                "suggested_callback_url": callback_url
            }
        }
    except Exception as e:
        logger.error(f"测试外部访问时出错: {str(e)}")
        return {"status": "error", "message": f"测试外部访问时出错: {str(e)}"}

@router.get("/test_callback")
async def test_callback():
    """测试回调端点是否可访问"""
    logger.info("测试回调端点被访问")
    return {"status": "success", "message": "回调端点可访问", "timestamp": datetime.now().isoformat()}