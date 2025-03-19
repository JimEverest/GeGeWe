from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional, Dict, Any, TypeVar, Generic, Type
from app.database.models import User, WechatAccount, Contact, Group, GroupMember, Message, MediaFile

# 通用类型
T = TypeVar('T')

# 通用CRUD操作类
class CRUDBase(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
    
    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> T:
        """创建记录"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get(self, db: AsyncSession, id: int) -> Optional[T]:
        """通过ID获取记录"""
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()
    
    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[T]:
        """获取多条记录"""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def update(self, db: AsyncSession, *, id: int, obj_in: Dict[str, Any]) -> Optional[T]:
        """更新记录"""
        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
        )
        await db.commit()
        return await self.get(db, id)
    
    async def delete(self, db: AsyncSession, *, id: int) -> None:
        """删除记录"""
        await db.execute(delete(self.model).where(self.model.id == id))
        await db.commit()

# 创建各实体的CRUD对象
user_crud = CRUDBase(User)
wechat_account_crud = CRUDBase(WechatAccount)
contact_crud = CRUDBase(Contact)
group_crud = CRUDBase(Group)
group_member_crud = CRUDBase(GroupMember)
message_crud = CRUDBase(Message)
media_file_crud = CRUDBase(MediaFile)

# 用户相关特定CRUD操作
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

# 微信账号相关特定CRUD操作
async def get_wechat_account_by_wxid(db: AsyncSession, wxid: str) -> Optional[WechatAccount]:
    """通过wxid获取微信账号"""
    result = await db.execute(select(WechatAccount).filter(WechatAccount.wxid == wxid))
    return result.scalars().first()

async def get_wechat_account_by_appid(db: AsyncSession, appid: str) -> Optional[WechatAccount]:
    """通过appid获取微信账号"""
    result = await db.execute(select(WechatAccount).filter(WechatAccount.appid == appid))
    return result.scalars().first()

# 消息相关特定CRUD操作
async def is_duplicate_message(db: AsyncSession, app_id: str, new_msg_id: str) -> bool:
    """检查是否为重复消息"""
    result = await db.execute(
        select(Message).filter(
            Message.app_id == app_id,
            Message.new_msg_id == new_msg_id
        )
    )
    return result.scalars().first() is not None

async def get_messages_by_chat(
    db: AsyncSession, 
    account_id: int, 
    chat_id: str, 
    skip: int = 0, 
    limit: int = 20
) -> List[Message]:
    """获取与特定联系人或群组的聊天记录"""
    result = await db.execute(
        select(Message)
        .filter(
            Message.account_id == account_id,
            (
                (Message.from_wxid == chat_id) | 
                (Message.to_wxid == chat_id)
            )
        )
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all() 