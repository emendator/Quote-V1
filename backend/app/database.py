"""数据库连接与初始化"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, select
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


async def seed_super_admin(db_session):
    """初始化超级管理员账号（系统预设）"""
    from app.models import User
    from app.utils.auth_utils import hash_password
    result = await db_session.execute(select(User).where(User.username == "admin"))
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("超级管理员已存在，跳过初始化")
        return existing

    now = datetime.now(timezone(timedelta(hours=8)))
    admin = User(
        username="admin",
        password_hash=hash_password("***REMOVED-PASSWORD***"),
        email="***REMOVED-EMAIL***",
        role="super_admin",
        company_name="***REMOVED-COMPANY***",
        created_at=now,
        updated_at=now,
    )
    db_session.add(admin)
    await db_session.flush()
    logger.info("超级管理员初始化完成: admin / ***REMOVED-PASSWORD***")
    return admin


async def _migrate_db(conn):
    """执行数据库迁移：添加缺失的列，移除旧约束"""
    # 移除 quick_model 上的 UNIQUE 索引（改为 6 字段联合去重）
    try:
        # SQLite 中 UNIQUE 约束对应的索引名
        unique_indexes = ["ix_products_quick_model", "uq_products_quick_model"]
        for idx_name in unique_indexes:
            await conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
            logger.info(f"数据库迁移: 已移除索引 {idx_name}")
    except Exception as e:
        logger.warning(f"数据库迁移: 移除索引跳过: {e}")

    # 检查并添加缺失的列
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

    # 迁移：为 users 表添加 last_login_at 列
    try:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        cols = [row[1] for row in result.fetchall()]
        if "last_login_at" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME DEFAULT NULL"))
            logger.info("数据库迁移: users 表添加 last_login_at 列")
    except Exception as e:
        logger.warning(f"数据库迁移: 添加 last_login_at 跳过: {e}")

    # 迁移：为 products 表添加 owner_id 列
    try:
        result = await conn.execute(text("PRAGMA table_info(products)"))
        cols = [row[1] for row in result.fetchall()]
        if "owner_id" not in cols:
            await conn.execute(text("ALTER TABLE products ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 0"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_owner_id ON products(owner_id)"))
            logger.info("数据库迁移: products 表添加 owner_id 列")
    except Exception as e:
        logger.warning(f"数据库迁移: 添加 owner_id 跳过: {e}")

    # 迁移：为 solution_plans 表添加 owner_id 列
    try:
        result = await conn.execute(text("PRAGMA table_info(solution_plans)"))
        cols = [row[1] for row in result.fetchall()]
        if "owner_id" not in cols:
            await conn.execute(text("ALTER TABLE solution_plans ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 0"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_solution_plans_owner_id ON solution_plans(owner_id)"))
            logger.info("数据库迁移: solution_plans 表添加 owner_id 列")
    except Exception as e:
        logger.warning(f"数据库迁移: solution_plans 添加 owner_id 跳过: {e}")

    # 迁移：将 barcode_69 和 product_model 改为可空（之前是 NOT NULL）
    try:
        result = await conn.execute(text("PRAGMA table_info(products)"))
        cols_info = {row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]} for row in result.fetchall()}

        needs_rebuild = False
        # 检查 barcode_69 是否仍为 NOT NULL
        if cols_info.get("barcode_69", {}).get("notnull") == 1:
            needs_rebuild = True
        # 检查 product_model 是否仍为 NOT NULL
        if cols_info.get("product_model", {}).get("notnull") == 1:
            needs_rebuild = True

        if needs_rebuild:
            logger.info("数据库迁移: 重建 products 表（将 barcode_69 和 product_model 改为可空）")

            # 构建新的列定义（barcode_69 和 product_model 去掉 NOT NULL，其余保持不变）
            col_defs = []
            for col_name, info in cols_info.items():
                nullable = "NULL" if info["notnull"] == 0 else "NOT NULL"
                # 强制这两个字段为可空
                if col_name in ("barcode_69", "product_model"):
                    nullable = "NULL"
                col_type = info["type"]
                pk_clause = "PRIMARY KEY" if info["pk"] == 1 else ""
                dflt = f"DEFAULT {info['dflt']}" if info["dflt"] is not None else ""
                col_defs.append(f'"{col_name}" {col_type} {nullable} {dflt} {pk_clause}'.strip())

            col_names = [f'"{c}"' for c in cols_info.keys()]
            create_sql = f'CREATE TABLE products_new ({", ".join(col_defs)})'
            insert_sql = f'INSERT INTO products_new ({", ".join(col_names)}) SELECT {", ".join(col_names)} FROM products'

            await conn.execute(text("PRAGMA foreign_keys=OFF"))
            await conn.execute(text("BEGIN TRANSACTION"))
            await conn.execute(text(create_sql))
            await conn.execute(text(insert_sql))
            await conn.execute(text("DROP TABLE products"))
            await conn.execute(text('ALTER TABLE products_new RENAME TO products'))
            await conn.execute(text("COMMIT"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))

            # 重新创建索引
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_quick_model ON products(quick_model)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_product_model ON products(product_model)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_brand ON products(brand)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_category_level1 ON products(category_level1)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_category_level2 ON products(category_level2)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_category_level3 ON products(category_level3)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_price ON products(price)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_specification ON products(specification)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_barcode_69 ON products(barcode_69)"))

            logger.info("数据库迁移: products 表重建完成")
    except Exception as e:
        logger.warning(f"数据库迁移: 重建 products 表跳过: {e}")


async def init_db():
    """初始化数据库：创建所有表并执行迁移"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_db(conn)

    # 初始化超级管理员
    async with AsyncSessionLocal() as session:
        try:
            await seed_super_admin(session)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"超级管理员初始化跳过: {e}")
