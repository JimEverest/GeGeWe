from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Form, Body, Request, WebSocket, WebSocketDisconnect
from app.services.wechat_service import WechatService
from app.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import logging
import httpx
from app.core.config import settings
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from sqlalchemy import select
from app.database.models import WechatAccount

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["wechat"])

# 存储活跃的WebSocket连接
active_connections: Dict[str, List[WebSocket]] = {}

@router.post("/token")
async def set_token(
    token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """设置Gewechat API Token"""
    try:
        wechat_service = WechatService(db)
        result = await wechat_service.set_token(token)
        return {"status": "success", "message": "Token设置成功"}
    except Exception as e:
        logger.error(f"设置Token时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置Token失败: {str(e)}"
        )

@router.post("/qrcode")
async def get_login_qrcode(
    db: AsyncSession = Depends(get_db)
):
    """获取微信登录二维码"""
    try:
        wechat_service = WechatService(db)
        qrcode_data = await wechat_service.get_login_qrcode()
        return qrcode_data
    except Exception as e:
        logger.error(f"获取登录二维码时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取登录二维码失败: {str(e)}"
        )

@router.get("/login/status")
async def check_login_status(
    db: AsyncSession = Depends(get_db)
):
    """检查微信登录状态"""
    try:
        wechat_service = WechatService(db)
        status_data = await wechat_service.check_login_status()
        return status_data
    except Exception as e:
        logger.error(f"检查登录状态时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查登录状态失败: {str(e)}"
        )

@router.get("/contacts")
async def get_contacts(
    db: AsyncSession = Depends(get_db)
):
    """获取联系人列表"""
    try:
        wechat_service = WechatService(db)
        
        # 获取账号信息
        account = await wechat_service._get_or_create_account()
        
        # 确保有 app_id
        if not account.appid or account.appid == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到有效的微信账号"
            )
        
        # 调用修改后的 get_contacts 方法，传递 app_id 参数
        contacts_data = await wechat_service.get_contacts(app_id=account.appid)
        
        # 处理返回的数据
        if contacts_data.get("ret") == 200 and "data" in contacts_data:
            data = contacts_data["data"]
            
            # 根据API文档，处理返回的数据结构
            friends = data.get("friends", [])
            chatrooms = data.get("chatrooms", [])
            ghs = data.get("ghs", [])
            
            # 转换为前端需要的格式
            contacts = []
            
            # 处理好友
            for wxid in friends:
                contacts.append({
                    "wxid": wxid,
                    "nickname": wxid,  # 暂时用wxid作为昵称
                    "type": "friend"
                })
            
            # 处理群聊
            for wxid in chatrooms:
                contacts.append({
                    "wxid": wxid,
                    "nickname": wxid,  # 暂时用wxid作为昵称
                    "type": "group"
                })
            
            # 处理公众号
            for wxid in ghs:
                contacts.append({
                    "wxid": wxid,
                    "nickname": wxid,  # 暂时用wxid作为昵称
                    "type": "official"
                })
            
            return {"contacts": contacts}
        
        # 如果API返回错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取联系人失败: {contacts_data.get('msg', '未知错误')}"
        )
        
    except Exception as e:
        logger.error(f"获取联系人时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取联系人时出错: {str(e)}"
        )

@router.post("/message/text")
async def send_text_message(
    to_wxid: str = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """发送文本消息"""
    try:
        wechat_service = WechatService(db)
        account = await wechat_service._get_or_create_account()
        
        if not account.appid or account.appid == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到有效的微信账号"
            )
        
        # 调用服务发送消息
        result = await wechat_service.send_text_message(to_wxid, content)
        
        if result.get("ret") == 200:
            return {"status": "success", "message": "消息发送成功"}
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {result.get('msg', '未知错误')}"
        )
        
    except Exception as e:
        logger.error(f"发送消息时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息时出错: {str(e)}"
        )

@router.post("/message/image")
async def send_image_message(
    to_wxid: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """发送图片消息"""
    try:
        wechat_service = WechatService(db)
        result = await wechat_service.send_image_message(to_wxid, image)
        return result
    except Exception as e:
        logger.error(f"发送图片消息时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送图片消息失败: {str(e)}"
        )

@router.get("/api-check")
async def check_api_connection():
    """检查API连接是否正常"""
    try:
        url = settings.GEWE_API_URL.rstrip('/')
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{url}/")
            return {
                "status": "success" if response.status_code == 200 else "error",
                "api_url": url,
                "response_status": response.status_code,
                "response_text": response.text[:100] if response.status_code == 200 else None
            }
    except Exception as e:
        return {
            "status": "error",
            "api_url": settings.GEWE_API_URL,
            "error": str(e)
        }

@router.get("/test-token")
async def test_get_token():
    """测试获取 Token"""
    try:
        url = settings.GEWE_API_URL.rstrip('/')
        test_url = f"{url}/tools/getTokenId"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(test_url)
            
            try:
                json_data = response.json()
            except:
                json_data = None
                
            return {
                "status": "success" if response.status_code == 200 else "error",
                "api_url": test_url,
                "response_status": response.status_code,
                "response_json": json_data,
                "response_text": response.text[:500]
            }
    except Exception as e:
        return {
            "status": "error",
            "api_url": settings.GEWE_API_URL,
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.post("/contacts/brief")
async def get_contacts_brief_info(
    wxids: List[str] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """获取联系人简要信息"""
    try:
        wechat_service = WechatService(db)
        account = await wechat_service._get_or_create_account()
        
        if not account.appid or account.appid == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到有效的微信账号"
            )
        
        # 调用 API 获取联系人简要信息
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{wechat_service.api_base_url}/contacts/getBriefInfo",
                headers={"X-GEWE-TOKEN": wechat_service.token},
                json={
                    "appId": account.appid,
                    "wxids": wxids
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("ret") == 200 and "data" in data:
                return {"contacts": data["data"]}
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取联系人简要信息失败: {data.get('msg', '未知错误')}"
            )
            
    except Exception as e:
        logger.error(f"获取联系人简要信息时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取联系人简要信息时出错: {str(e)}"
        )

@router.post("/contacts/delete")
async def delete_contact(
    wxid: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """删除联系人"""
    try:
        wechat_service = WechatService(db)
        account = await wechat_service._get_or_create_account()
        
        if not account.appid or account.appid == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到有效的微信账号"
            )
        
        # 调用 API 删除联系人
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{wechat_service.api_base_url}/contacts/deleteFriend",
                headers={"X-GEWE-TOKEN": wechat_service.token},
                json={
                    "appId": account.appid,
                    "wxid": wxid
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("ret") == 200:
                return {"status": "success", "message": "联系人删除成功"}
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除联系人失败: {data.get('msg', '未知错误')}"
            )
            
    except Exception as e:
        logger.error(f"删除联系人时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除联系人时出错: {str(e)}"
        )

@router.post("/callback", dependencies=[])
async def wechat_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """接收微信消息回调"""
    try:
        # 获取原始请求体
        body = await request.json()
        logger.info(f"收到微信消息回调: {json.dumps(body)}")
        
        # 提取消息类型和数据
        type_name = body.get("TypeName")
        app_id = body.get("Appid")
        wxid = body.get("Wxid")
        data = body.get("Data", {})
        
        # 消息排重处理
        if type_name == "AddMsg" and "NewMsgId" in data:
            new_msg_id = data["NewMsgId"]
            # 检查消息是否已处理过
            # TODO: 实现消息排重逻辑
            
        # 处理不同类型的消息
        if type_name == "AddMsg":
            # 处理聊天消息
            await process_chat_message(db, app_id, wxid, data)
        elif type_name == "Offline":
            # 处理离线通知
            logger.warning(f"微信账号 {wxid} 已离线")
            # TODO: 更新账号状态并尝试重连
        
        # 返回成功响应
        return {"status": "success"}
    except Exception as e:
        logger.error(f"处理微信消息回调时出错: {str(e)}", exc_info=True)
        # 即使处理失败，也返回成功以避免重复推送
        return {"status": "success"}

async def process_chat_message(db: AsyncSession, app_id: str, wxid: str, data: dict):
    """处理聊天消息并通过WebSocket推送到前端"""
    try:
        # 提取消息基本信息
        msg_id = data.get("NewMsgId")
        msg_type = data.get("MsgType")
        from_user = data.get("FromUserName", {}).get("string", "")
        to_user = data.get("ToUserName", {}).get("string", "")
        content = data.get("Content", {}).get("string", "")
        create_time = data.get("CreateTime", 0)
        
        # 判断消息类型
        if msg_type == 1:  # 文本消息
            logger.info(f"收到文本消息: {from_user} -> {to_user}: {content}")
            
            # 保存消息到数据库
            # TODO: 实现消息存储逻辑
            
            # 如果需要，可以在这里实现自动回复功能
            
        elif msg_type == 3:  # 图片消息
            logger.info(f"收到图片消息: {from_user} -> {to_user}")
            # TODO: 处理图片消息
            
        elif msg_type == 34:  # 语音消息
            logger.info(f"收到语音消息: {from_user} -> {to_user}")
            # TODO: 处理语音消息
            
        elif msg_type == 43:  # 视频消息
            logger.info(f"收到视频消息: {from_user} -> {to_user}")
            # TODO: 处理视频消息
            
        elif msg_type == 49:  # 链接/文件消息
            logger.info(f"收到链接或文件消息: {from_user} -> {to_user}")
            # TODO: 处理链接或文件消息
            
        elif msg_type == 10002:  # 系统消息（如撤回、拍一拍等）
            logger.info(f"收到系统消息: {from_user} -> {to_user}: {content}")
            # TODO: 处理系统消息
            
        else:
            logger.info(f"收到未知类型消息: 类型={msg_type}, {from_user} -> {to_user}")
            
        # 构建推送消息
        push_message = {
            "type": "chat_message",
            "app_id": app_id,
            "wxid": wxid,
            "data": data
        }
        
        # 推送到所有活跃连接
        for client_id, connections in active_connections.items():
            for connection in connections:
                await connection.send_json(push_message)
        
    except Exception as e:
        logger.error(f"处理聊天消息时出错: {str(e)}", exc_info=True)

@router.post("/set_callback")
async def set_callback(
    callback_url: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """设置微信消息回调URL"""
    try:
        wechat_service = WechatService(db)
        result = await wechat_service.set_callback_url(callback_url)
        
        if result.get("ret") == 200:
            return {"status": "success", "message": "回调URL设置成功"}
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置回调URL失败: {result.get('msg', '未知错误')}"
        )
    except Exception as e:
        logger.error(f"设置回调URL时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置回调URL时出错: {str(e)}"
        )

@router.get("/set_callback_url")
async def set_callback_url_get(
    callback_url: str,
    db: AsyncSession = Depends(get_db)
):
    """通过GET方法设置微信消息回调URL（仅用于测试）"""
    try:
        wechat_service = WechatService(db)
        result = await wechat_service.set_callback_url(callback_url)
        
        if result.get("ret") == 200:
            return {"status": "success", "message": "回调URL设置成功", "callback_url": callback_url}
        
        return {"status": "error", "message": f"设置回调URL失败: {result.get('msg', '未知错误')}"}
    except Exception as e:
        logger.error(f"设置回调URL时出错: {str(e)}")
        return {"status": "error", "message": f"设置回调URL时出错: {str(e)}"}

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接，用于实时推送消息"""
    await websocket.accept()
    logger.info(f"WebSocket连接已建立: {client_id}")
    
    # 将连接添加到活跃连接列表
    if client_id not in active_connections:
        active_connections[client_id] = []
    active_connections[client_id].append(websocket)
    
    logger.info(f"添加连接后，活跃连接: {list(active_connections.keys())}")
    logger.info(f"客户端 {client_id} 现有 {len(active_connections[client_id])} 个连接")
    logger.info(f"当前活跃连接总数: {sum(len(connections) for connections in active_connections.values())}")
    
    # 发送测试消息
    test_message = {
        "type": "test_message",
        "message": "WebSocket连接测试",
        "time": datetime.now().isoformat()
    }
    await websocket.send_json(test_message)
    logger.info(f"已发送测试消息到客户端 {client_id}")
    
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            logger.info(f"从客户端 {client_id} 收到消息: {data}")
            # 可以处理从客户端接收的消息，如果需要
    except WebSocketDisconnect:
        # 连接断开时，从活跃连接列表中移除
        logger.info(f"WebSocket连接已断开: {client_id}")
        if client_id in active_connections:
            active_connections[client_id].remove(websocket)
            if not active_connections[client_id]:
                del active_connections[client_id]
        logger.info(f"断开连接后，活跃连接: {list(active_connections.keys())}")
        logger.info(f"当前活跃连接总数: {sum(len(connections) for connections in active_connections.values())}")

@router.post("/test_callback")
async def test_callback(
    request: Request
):
    """测试回调接口"""
    try:
        body = await request.json()
        logger.info(f"收到测试回调: {json.dumps(body)}")
        return {"status": "success", "received": body}
    except Exception as e:
        logger.error(f"处理测试回调时出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/callback")
async def wechat_callback_verification():
    """验证回调URL有效性"""
    logger.info("收到回调URL验证请求")
    return {"status": "success", "message": "Callback URL is valid"}

@router.get("/get_callback_url")
async def get_callback_url(db: AsyncSession = Depends(get_db)):
    """获取当前设置的回调URL"""
    try:
        wechat_service = WechatService(db)
        callback_url = await wechat_service.get_callback_url()
        return {"status": "success", "callback_url": callback_url}
    except Exception as e:
        logger.error(f"获取回调URL失败: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/status")
async def check_status(db: AsyncSession = Depends(get_db)):
    """检查当前登录状态"""
    try:
        # 获取最近登录的微信账号
        query = select(WechatAccount).where(WechatAccount.status == 1).order_by(WechatAccount.last_online.desc())
        result = await db.execute(query)
        account = result.scalars().first()
        
        if account:
            return {
                "status": "success",
                "is_logged_in": True,
                "wxid": account.wxid,
                "nickname": account.nickname
            }
        else:
            return {
                "status": "success",
                "is_logged_in": False
            }
    except Exception as e:
        logger.error(f"检查登录状态出错: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/logout")
async def logout_wechat(
    db: AsyncSession = Depends(get_db)
):
    """登出微信账号"""
    try:
        wechat_service = WechatService(db)
        result = await wechat_service.logout()
        
        # 返回登出结果
        if result.get("ret") == 200:
            return {"status": "success", "message": "成功登出微信账号"}
        else:
            return {"status": "error", "message": f"登出失败: {result.get('msg', '未知错误')}"}
    except Exception as e:
        logger.error(f"登出微信账号时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出微信账号失败: {str(e)}"
        )