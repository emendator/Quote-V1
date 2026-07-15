"""数据库连接与初始化"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import DATABASE_URL, SYNC_DATABASE_URL

logger = logging.getLogger("database")

# 异步引擎（用于 FastAPI）
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# 同步引擎（用于 pandas 批量导入等同步操作）
from sqlalchemy import create_engine
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _migrate_db(conn):
    """执行数据库迁移：添加缺失的列"""
    # 检查并添加 image 列
    migrations = [
        ("products", "image", "TEXT DEFAULT ''"),
    ]
    for table, column, col_def in migrations:
        try:
            # SQLite: 检查列是否存在
            result = await conn.execute(
                text(f"PRAGMA table_info({table})")
            )
            columns = [row[1] for row in result.fetchall()]
            if column not in columns:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                )
                logger.info(f"数据库迁移: 表 {table} 添加列 {column}")
        except Exception as e:
            logger.warning(f"数据库迁移跳过 ({table}.{column}): {e}")


async def init_db():
    """初始化数据库：创建所有表并执行迁移"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_db(conn)
