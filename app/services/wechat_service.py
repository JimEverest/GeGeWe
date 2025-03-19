from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database.models import WechatAccount, Contact
from app.core.config import settings
import httpx
import logging
import json
from typing import Dict, List, Any, Optional
from fastapi import UploadFile
import os
import aiofiles
from datetime import datetime

# 增强日志设置
logger = logging.getLogger(__name__)

class WechatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token = settings.GEWE_TOKEN
        # 确保 API URL 末尾没有斜杠，因为我们会在各个方法中添加路径
        self.api_base_url = settings.GEWE_API_URL.rstrip('/')
        
        # 从配置获取APP_ID（添加错误处理）
        try:
            self.app_id = settings.APP_ID
            # 移除对默认APP_ID的特殊判断
            app_id_log = self.app_id if self.app_id else "未设置APP_ID"
        except AttributeError:
            logger.warning("配置中未找到APP_ID，使用默认值")
            self.app_id = "wx_1Evjqp0uqLMBC8HLZFyX0"
            app_id_log = "未在配置中定义，使用默认值"
        
        logger.info(f"初始化 WechatService, API基础URL: {self.api_base_url}, "
                   f"Token: {self.token[:5] if len(self.token) > 5 else '未设置'}...")
        logger.info(f"从配置中获取APP_ID: {app_id_log}")
        
        # 禁用数据库相关日志
        self.disable_db_logs()
    
    @staticmethod
    def disable_db_logs():
        """禁用所有数据库相关的日志"""
        # 禁用 aiosqlite 日志
        logging.getLogger('aiosqlite').setLevel(logging.WARNING)
        
        # 禁用 SQLAlchemy 日志
        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
        
        # 禁用应用中的数据库相关日志
        messages_logger = logging.getLogger('app.api.messages')
        
        # 创建一个过滤器，过滤掉包含"数据库"或"SQL"的日志
        class DatabaseLogFilter(logging.Filter):
            def filter(self, record):
                # 如果日志消息包含以下任何关键词，则不记录
                keywords = ["数据库中的所有消息", "SQL查询", "查询到", "返回"]
                return not any(keyword in record.getMessage() for keyword in keywords)
        
        # 添加过滤器到 messages_logger
        messages_logger.addFilter(DatabaseLogFilter())
        
        logger.info("已禁用数据库相关日志")
    
    @staticmethod
    def configure_logging(enable_db_logs=False):
        """配置日志级别
        
        Args:
            enable_db_logs: 是否启用数据库日志，默认为False
        """
        if enable_db_logs:
            # 启用数据库日志
            logging.getLogger('aiosqlite').setLevel(logging.DEBUG)
            logging.getLogger('sqlalchemy').setLevel(logging.INFO)
            logging.getLogger('app.api.messages').setLevel(logging.INFO)
            
            # 移除过滤器
            messages_logger = logging.getLogger('app.api.messages')
            for filter in messages_logger.filters:
                messages_logger.removeFilter(filter)
            
            logger.info("已启用数据库日志")
        else:
            # 禁用数据库日志
            WechatService.disable_db_logs()
    
    async def set_token(self, token: str) -> bool:
        """设置Gewechat API Token"""
        logger.info(f"设置新的Gewechat Token: {token[:5]}...")
        
        # 保存到全局设置
        settings.GEWE_TOKEN = token
        self.token = token
        
        # 保存到数据库中的第一个账号（或创建新账号）
        account = await self._get_or_create_account()
        account.token = token
        
        self.db.add(account)
        await self.db.commit()
        logger.info(f"Token已更新，账号ID: {account.id}")
        
        return True
    
    async def get_token(self) -> str:
        """获取 GeWechat API Token ID"""
        logger.info(f"开始获取 GeWechat API Token...")
        
        try:
            request_url = f"{self.api_base_url}/tools/getTokenId"
            logger.info(f"API请求: URL={request_url}, 无需请求头和请求体")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(request_url)
                
                logger.info(f"API响应: 状态码={response.status_code}")
                logger.info(f"API完整响应体: {response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                # 记录完整响应内容
                logger.info(f"Token API 响应数据: {json.dumps(data)}")
                
                # 判断是否成功，并从data字段中获取token
                if data.get("ret") == 200 and isinstance(data.get("data"), str) and len(data.get("data")) > 10:
                    token = data["data"]
                    logger.info(f"成功获取Token: {token[:5]}...")
                    
                    # 保存到全局设置和当前实例
                    settings.GEWE_TOKEN = token
                    self.token = token
                    
                    # 保存到数据库中的账号
                    account = await self._get_or_create_account()
                    account.token = token
                    self.db.add(account)
                    await self.db.commit()
                    
                    return token
                else:
                    error_msg = f"获取Token失败: 无效响应格式或返回码: {data}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
        except httpx.HTTPError as e:
            logger.error(f"获取Token HTTP错误: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"获取Token时发生未预期错误: {str(e)}", exc_info=True)
            raise
    
    async def get_login_qrcode(self) -> Dict[str, Any]:
        """获取微信登录二维码"""
        # 先获取Token，确保有最新的Token
        if not self.token or self.token == "your_token_here":
            await self.get_token()
        
        # 获取账号信息
        account = await self._get_or_create_account()
        
        # 使用账号的APP_ID，如果没有则使用配置中的APP_ID
        app_id_to_use = None
        if account.appid and account.appid != "pending":
            app_id_to_use = account.appid
            logger.info(f"使用数据库中的APP_ID: {app_id_to_use}")
        elif self.app_id:
            app_id_to_use = self.app_id
            logger.info(f"使用配置文件中的APP_ID: {app_id_to_use}")
        else:
            logger.info("没有找到有效的APP_ID，将使用空APP_ID获取新的二维码")
        
        logger.info(f"获取登录二维码, 账号ID: {account.id}, 使用的AppID: {app_id_to_use or '未指定'}")
        
        # 调用API获取二维码，添加超时和重试
        try:
            request_url = f"{self.api_base_url}/login/getLoginQrCode"
            # 使用 X-GEWE-TOKEN 作为请求头名称
            request_headers = {"X-GEWE-TOKEN": self.token}
            request_json = {"appId": app_id_to_use} if app_id_to_use else {"appId": self.app_id}
            
            logger.info(f"API请求: URL={request_url}, Headers={json.dumps({'X-GEWE-TOKEN': self.token[:5] + '...'})}, Body={json.dumps(request_json)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    request_url,
                    headers=request_headers,
                    json=request_json
                )
                
                logger.info(f"API响应: 状态码={response.status_code}")
                # 记录完整响应，帮助调试
                logger.info(f"二维码API完整响应: {response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                # 记录完整的响应数据结构
                logger.info(f"二维码响应数据: {json.dumps(data)}")
                
                # 查找 appId 字段 - 可能在多个位置
                app_id = None
                status = None
                
                # 检查 data.data.appId 格式
                if "data" in data and isinstance(data["data"], dict):
                    # 先检查嵌套的 data 字段
                    data_obj = data["data"]
                    if "appId" in data_obj:
                        app_id = data_obj["appId"]
                    elif "app_id" in data_obj:
                        app_id = data_obj["app_id"]
                    elif "appID" in data_obj:
                        app_id = data_obj["appID"]
                    
                    # 检查状态字段
                    if "status" in data_obj:
                        status = data_obj["status"]
                
                # 如果没找到再检查顶层
                if not app_id:
                    if "appId" in data:
                        app_id = data["appId"]
                    elif "app_id" in data:
                        app_id = data["app_id"]
                    elif "appID" in data:
                        app_id = data["appID"]
                
                # 记录发现的 appId 和状态
                logger.info(f"解析出的 AppID: {app_id or 'unknown'}, Status: {status or 'unknown'}")
                
                # 更新账号 appId（如果找到有效值）
                if app_id and (not account.appid or account.appid == "pending"):
                    old_appid = account.appid
                    account.appid = app_id
                    self.db.add(account)
                    await self.db.commit()
                    logger.info(f"已更新账号AppID: {old_appid} -> {account.appid}")
                    
                    # 更新当前实例和全局配置
                    self.app_id = app_id
                    try:
                        settings.APP_ID = app_id
                        logger.info(f"已更新全局APP_ID设置: {app_id}")
                    except (AttributeError, TypeError) as e:
                        logger.warning(f"无法更新全局APP_ID设置: {str(e)}")
                
                # 在解析响应数据时，提取并保存uuid
                uuid = None
                if "data" in data and isinstance(data["data"], dict):
                    data_obj = data["data"]
                    if "uuid" in data_obj:
                        uuid = data_obj["uuid"]
                
                if uuid:
                    # 保存uuid到账号记录中
                    account.login_uuid = uuid
                    self.db.add(account)
                    await self.db.commit()
                    logger.info(f"已保存登录二维码UUID: {uuid}")
                
                return data
        except httpx.HTTPError as e:
            logger.error(f"获取登录二维码HTTP错误: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"获取登录二维码时发生未预期错误: {str(e)}", exc_info=True)
            raise
    
    async def check_login_status(self) -> Dict[str, Any]:
        """检查微信登录状态"""
        # 确保有Token
        if not self.token or self.token == "your_token_here":
            await self.get_token()
        
        account = await self._get_or_create_account()
        
        # 获取账号的APPID和UUID
        app_id_to_use = account.appid if account.appid and account.appid != "pending" else self.app_id
        uuid = account.login_uuid
        
        logger.info(f"检查登录状态, 账号ID: {account.id}, 使用的AppID: {app_id_to_use}, UUID: {uuid or '未知'}")
        
        # 必须有UUID才能检查登录状态
        if not uuid:
            logger.warning("没有找到登录UUID，无法检查登录状态，请先获取登录二维码")
            return {"status": "error", "message": "请先获取登录二维码"}
        
        try:
            request_url = f"{self.api_base_url}/login/checkLogin"
            request_headers = {"X-GEWE-TOKEN": self.token}
            request_json = {
                "appId": app_id_to_use,
                "uuid": uuid
            }
            
            logger.info(f"API请求: URL={request_url}, Headers={json.dumps({'X-GEWE-TOKEN': self.token[:5] + '...'})}, Body={json.dumps(request_json)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    request_url,
                    headers=request_headers,
                    json=request_json
                )
                
                logger.info(f"API响应: 状态码={response.status_code}")
                logger.info(f"登录状态API完整响应: {response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                # 记录完整响应结构
                logger.info(f"登录状态响应数据: {json.dumps(data)}")
                
                # 检查是否成功登录，如果有wxid则更新账号信息
                if "data" in data and isinstance(data["data"], dict) and "loginInfo" in data["data"]:
                    login_info = data["data"]["loginInfo"]
                    if login_info and "wxid" in login_info:
                        # 更新账号wxid和状态
                        old_wxid = account.wxid
                        account.wxid = login_info["wxid"]
                        account.status = 1  # 已登录
                        
                        # 更新nickname如果存在
                        if "nickName" in login_info:
                            account.nickname = login_info["nickName"]
                        
                        self.db.add(account)
                        await self.db.commit()
                        logger.info(f"登录成功，已更新账号信息: {old_wxid} -> {account.wxid}")
                
                return data
        except Exception as e:
            logger.error(f"检查登录状态时出错: {str(e)}", exc_info=True)
            raise
    
    def _get_headers(self):
        """获取API请求头"""
        return {
            "X-GEWE-TOKEN": self.token
        }

    async def get_contacts(self, app_id: str) -> dict:
        """获取联系人列表"""
        try:
            account = await self._get_or_create_account()
            
            if not account.appid or not account.wxid:
                return {"status": "error", "message": "未登录微信账号"}
            
            # 使用正确的API路径
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/contacts/fetchContactsList",
                    headers={"X-GEWE-TOKEN": self.token},
                    json={"appId": app_id}
                )
                
                response.raise_for_status()
                data = response.json()
                
                return data
        except Exception as e:
            logger.error(f"获取联系人列表失败: {str(e)}")
            raise
    
    async def send_text_message(self, to_wxid: str, content: str) -> Dict[str, Any]:
        """发送文本消息"""
        try:
            account = await self._get_or_create_account()
            
            if not account.appid or not account.wxid:
                return {"ret": 500, "msg": "未登录微信账号"}
            
            logger.info(f"发送文本消息: 接收人={to_wxid}, 内容={content[:20]}...")
            
            async with httpx.AsyncClient() as client:
                # 修正 API 端点
                url = f"{self.api_base_url}/message/postText"
                
                # 根据 API 文档修正参数名
                payload = {
                    "appId": account.appid,
                    "toWxid": to_wxid,  # 修改为 toWxid
                    "content": content
                }
                
                logger.info(f"API请求: URL={url}, Headers={{'X-GEWE-TOKEN': '{self.token[:5]}...'}}, Body={payload}")
                
                response = await client.post(
                    url,
                    headers={"X-GEWE-TOKEN": self.token},
                    json=payload
                )
                
                logger.info(f"API响应: 状态码={response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"发送消息API响应: {data}")
                
                return data
        except Exception as e:
            logger.error(f"发送文本消息失败: {str(e)}", exc_info=True)
            # 记录完整的异常堆栈
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            raise
    
    async def send_image_message(self, to_wxid: str, image: UploadFile) -> Dict[str, Any]:
        """发送图片消息"""
        try:
            account = await self._get_or_create_account()
            
            if not account.appid or not account.wxid:
                return {"ret": 500, "msg": "未登录微信账号"}
            
            # 保存上传的图片到临时文件
            temp_file_path = f"temp/{image.filename}"
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            
            async with aiofiles.open(temp_file_path, 'wb') as out_file:
                content = await image.read()
                await out_file.write(content)
            
            # 上传图片到Gewechat
            async with httpx.AsyncClient() as client:
                with open(temp_file_path, 'rb') as f:
                    response = await client.post(
                        f"{self.api_base_url}/message/postImage",
                        headers={"X-GEWE-TOKEN": self.token},  # 修改为 X-GEWE-TOKEN
                        data={
                            "appId": account.appid,
                            "toWxid": to_wxid  # 修改为 toWxid
                        },
                        files={"file": f}
                    )
            
            # 删除临时文件
            os.remove(temp_file_path)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"发送图片消息失败: {str(e)}", exc_info=True)
            raise
    
    async def _get_or_create_account(self) -> WechatAccount:
        """获取第一个账号或创建新账号"""
        logger.debug("尝试获取WechatAccount记录")
        # 使用 SQLAlchemy ORM 查询
        result = await self.db.execute(select(WechatAccount).limit(1))
        account = result.scalars().first()
        
        if not account:
            logger.info("未找到WechatAccount记录，创建新记录")
            # 创建新账号，为所有必填字段提供初始值
            account = WechatAccount(
                token=self.token,
                status=0,  # 未登录
                wxid="pending",  # 提供占位值，登录成功后会更新
                appid=self.app_id if self.app_id and self.app_id != "wx_1Evjqp0uqLMBC8HLZFyX0" else "pending"  # 使用配置中的APP_ID或占位值
            )
            self.db.add(account)
            await self.db.commit()
            await self.db.refresh(account)
            logger.info(f"已创建新账号，ID: {account.id}, 初始APP_ID: {account.appid}")
        else:
            logger.debug(f"找到现有账号，ID: {account.id}, AppID: {account.appid}, Status: {account.status}")
            
            # 如果账号没有app_id但配置中有，则更新账号
            if (not account.appid or account.appid == "pending") and self.app_id and self.app_id != "wx_1Evjqp0uqLMBC8HLZFyX0":
                account.appid = self.app_id
                self.db.add(account)
                await self.db.commit()
                logger.info(f"从配置更新账号APP_ID: {account.appid}")
            # 如果账号有app_id但配置中没有或不同，则更新配置
            elif account.appid and account.appid != "pending" and (not self.app_id or self.app_id == "wx_1Evjqp0uqLMBC8HLZFyX0" or self.app_id != account.appid):
                self.app_id = account.appid
                settings.APP_ID = account.appid
                logger.info(f"从账号更新全局APP_ID设置: {self.app_id}")
        
        return account
    
    async def _update_contacts(self, account_id: int, contacts_data: List[Dict[str, Any]]):
        """更新联系人信息"""
        # 此处可实现将联系人信息保存到数据库的逻辑
        # 这里暂时只做日志记录，实际项目中应该实现完整的更新逻辑
        logger.info(f"更新账号 {account_id} 的联系人信息，共 {len(contacts_data)} 个联系人")
        pass

    async def set_callback_url(self, callback_url: str) -> Dict[str, Any]:
        """设置回调URL"""
        try:
            logger.info(f"设置回调URL: {callback_url}")
            
            url = f"{self.api_base_url}/tools/setCallback"
            payload = {
                "token": self.token,
                "callbackUrl": callback_url
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"X-GEWE-TOKEN": self.token},
                    json=payload,
                    timeout=30.0
                )
                
                logger.info(f"API响应: 状态码={response.status_code}, 响应内容={response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"设置回调URL响应: {data}")
                
                return data
        except Exception as e:
            logger.error(f"设置回调URL失败: {str(e)}", exc_info=True)
            raise

    async def get_callback_url(self) -> str:
        """获取当前设置的回调URL"""
        try:
            logger.info("获取回调URL")
            
            url = f"{self.api_base_url}/tools/getCallback"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"X-GEWE-TOKEN": self.token},
                    json={"token": self.token},
                    timeout=30.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"获取回调URL响应: {data}")
                
                return data.get("data", {}).get("callbackUrl", "")
        except Exception as e:
            logger.error(f"获取回调URL失败: {str(e)}", exc_info=True)
            raise

    async def logout(self) -> Dict[str, Any]:
        """退出微信登录"""
        try:
            account = await self._get_or_create_account()
            
            if not account.appid or account.appid == "pending":
                logger.warning("尝试登出，但没有有效的APP_ID")
                return {"ret": 400, "msg": "没有有效的APP_ID，无法登出"}
            
            logger.info(f"开始登出微信账号, APP_ID: {account.appid}")
            
            request_url = f"{self.api_base_url}/login/logout"
            request_headers = {"X-GEWE-TOKEN": self.token}
            request_json = {"appId": account.appid}
            
            logger.info(f"API请求: URL={request_url}, Headers={json.dumps({'X-GEWE-TOKEN': self.token[:5] + '...'})}, Body={json.dumps(request_json)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    request_url,
                    headers=request_headers,
                    json=request_json
                )
                
                logger.info(f"API响应: 状态码={response.status_code}")
                logger.info(f"登出API完整响应: {response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                # 记录完整响应结构
                logger.info(f"登出响应数据: {json.dumps(data)}")
                
                # 如果登出成功，更新账号状态
                if data.get("ret") == 200:
                    account.status = 0  # 设置为未登录状态
                    account.last_logout = datetime.now()
                    self.db.add(account)
                    await self.db.commit()
                    logger.info(f"账号 {account.wxid} 已成功登出")
                
                return data
        except Exception as e:
            logger.error(f"登出微信账号时出错: {str(e)}", exc_info=True)
            raise