from app.database.database import engine, Base
from app.database.models import Message, User, WechatAccount, Contact, Group, GroupMember, MediaFile
import asyncio

async def recreate_tables():
    """重新创建所有表（警告：这将删除所有现有数据）"""
    async with engine.begin() as conn:
        # 删除现有表
        await conn.run_sync(Base.metadata.drop_all)
        # 创建新表
        await conn.run_sync(Base.metadata.create_all)
        print("数据库表已重新创建")

if __name__ == "__main__":
    asyncio.run(recreate_tables()) 