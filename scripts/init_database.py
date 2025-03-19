import asyncio
import sys
import os
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
logger.info(f"添加项目根目录到路径: {project_root}")

# 确保数据目录存在
data_dir = Path(os.path.join(project_root, "data"))
data_dir.mkdir(exist_ok=True)
logger.info(f"确保数据目录存在: {data_dir}")

try:
    from app.database.database import init_db, AsyncSessionLocal
    from app.database.models import User
    logger.info("成功导入必要模块")
except ImportError as e:
    logger.error(f"导入错误: {e}")
    logger.error(f"当前Python路径: {sys.path}")
    sys.exit(1)

async def create_default_user():
    """创建默认管理员用户"""
    try:
        async with AsyncSessionLocal() as session:
            # 检查是否已存在用户
            from sqlalchemy.future import select
            result = await session.execute(select(User).filter(User.username == "admin"))
            user = result.scalars().first()
            
            if not user:
                # 创建默认用户
                default_user = User(
                    username="admin",
                    auth_level=2  # 管理员级别
                )
                session.add(default_user)
                await session.commit()
                logger.info("创建默认用户: admin")
            else:
                logger.info("默认用户已存在，跳过创建")
    except Exception as e:
        logger.error(f"创建默认用户时出错: {e}")
        raise

async def main():
    """初始化数据库并创建默认数据"""
    logger.info("开始初始化数据库...")
    try:
        await init_db()
        logger.info("数据库表创建完成")
        
        logger.info("开始创建默认用户...")
        await create_default_user()
        logger.info("数据库初始化完成！")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"运行初始化脚本时出错: {e}")
        sys.exit(1) 