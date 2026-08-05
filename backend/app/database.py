"""数据库连接与初始化"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, select
from app.config import (
    DATABASE_URL,
    SYNC_DATABASE_URL,
    SUPER_ADMIN_USERNAME,
    SUPER_ADMIN_PASSWORD,
    SUPER_ADMIN_EMAIL,
    SUPER_ADMIN_COMPANY,
    SUPER_ADMIN_COMPANY_PASSWORD,
)

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
    """初始化超级管理员账号与公司（预设信息固定于 config，每次重建不可变）"""
    from app.models import User, Company
    from app.utils.auth_utils import hash_password
    from app.utils.crypto_utils import encrypt_username, hash_username
    admin_username_hash = hash_username(SUPER_ADMIN_USERNAME)

    # 1. 确保超级管理员公司存在（公司数据库密码固定于 config）
    company = (await db_session.execute(
        select(Company).where(Company.company_name == SUPER_ADMIN_COMPANY)
    )).scalar_one_or_none()
    if not company:
        company = Company(
            company_name=SUPER_ADMIN_COMPANY,
            password_hash=hash_password(SUPER_ADMIN_COMPANY_PASSWORD),
            created_by=0,
        )
        db_session.add(company)
        await db_session.flush()
        logger.info(f"超级管理员公司初始化完成: {SUPER_ADMIN_COMPANY}")

    # 2. 确保超级管理员账号存在
    result = await db_session.execute(select(User).where(User.username_hash == admin_username_hash))
    existing = result.scalar_one_or_none()
    if existing:
        # 兜底：若管理员尚未绑定公司，则绑定到超级管理员公司
        if not existing.company_id:
            existing.company_id = company.id
            existing.company_name = company.company_name
            logger.info("超级管理员已绑定默认公司")
        logger.info("超级管理员已存在，跳过初始化")
        return existing

    now = datetime.now(timezone(timedelta(hours=8)))
    admin = User(
        username=encrypt_username(SUPER_ADMIN_USERNAME),
        username_hash=admin_username_hash,
        password_hash=hash_password(SUPER_ADMIN_PASSWORD),
        email=SUPER_ADMIN_EMAIL,
        role="super_admin",
        company_name=SUPER_ADMIN_COMPANY,
        company_id=company.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(admin)
    await db_session.flush()
    logger.info(
        f"超级管理员初始化完成: {SUPER_ADMIN_USERNAME} / {SUPER_ADMIN_COMPANY}"
    )
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
        ("solution_items", "category_level1", "VARCHAR(200) DEFAULT ''"),
        ("solution_items", "category_level2", "VARCHAR(200) DEFAULT ''"),
        ("solution_items", "retail_price", "FLOAT DEFAULT 0"),
        ("solution_items", "image", "TEXT DEFAULT ''"),
        ("invite_codes", "company_name", "VARCHAR(200) DEFAULT ''"),
        ("import_logs", "owner_id", "INTEGER DEFAULT 0"),
        ("import_logs", "company_name", "VARCHAR(200) DEFAULT ''"),
        ("users", "api_key", "VARCHAR(500) DEFAULT ''"),
        ("users", "total_tokens_used", "INTEGER DEFAULT 0"),
        ("users", "expires_at", "DATETIME DEFAULT NULL"),
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

    # 迁移：users 表用户名加密存储（username 存密文，username_hash 存 HMAC 用于查询与唯一校验）
    try:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        cols = [row[1] for row in result.fetchall()]
        if "username_hash" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN username_hash VARCHAR(64) DEFAULT ''"))
            logger.info("数据库迁移: users 表添加 username_hash 列")

        from app.utils.crypto_utils import encrypt_username, decrypt_username, hash_username
        rows = (await conn.execute(text("SELECT id, username, username_hash FROM users"))).fetchall()
        for uid, uname, uh in rows:
            if uh:
                continue  # 已处理过
            if not uname:
                continue
            # 兼容：若 username 已是密文（能成功解密）则直接算 hash，否则先加密再算 hash
            plain = decrypt_username(uname)
            if plain:
                enc = uname
            else:
                plain = uname
                enc = encrypt_username(uname)
            await conn.execute(
                text("UPDATE users SET username = :enc, username_hash = :h WHERE id = :id"),
                {"enc": enc, "h": hash_username(plain), "id": uid}
            )

        # 用户名唯一性改由 username_hash 承担（旧 username 唯一索引针对密文无意义，移除）
        await conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username_hash ON users(username_hash)"))
        logger.info("数据库迁移: users 表用户名加密存储完成")
    except Exception as e:
        logger.warning(f"数据库迁移: 用户名加密跳过: {e}")

    # 迁移：为 products 表添加 company_name 列（v2.0 数据隔离基于公司名）
    try:
        result = await conn.execute(text("PRAGMA table_info(products)"))
        cols = [row[1] for row in result.fetchall()]
        if "company_name" not in cols:
            await conn.execute(text("ALTER TABLE products ADD COLUMN company_name VARCHAR(200) NOT NULL DEFAULT ''"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_company_name ON products(company_name)"))
            logger.info("数据库迁移: products 表添加 company_name 列")
        # 保留 owner_id 列作为兼容
        if "owner_id" not in cols:
            await conn.execute(text("ALTER TABLE products ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 0"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_owner_id ON products(owner_id)"))
            logger.info("数据库迁移: products 表添加 owner_id 列（兼容保留）")
    except Exception as e:
        logger.warning(f"数据库迁移: products 列添加跳过: {e}")

    # 迁移：为 solution_plans 表添加 company_name 列
    try:
        result = await conn.execute(text("PRAGMA table_info(solution_plans)"))
        cols = [row[1] for row in result.fetchall()]
        if "company_name" not in cols:
            await conn.execute(text("ALTER TABLE solution_plans ADD COLUMN company_name VARCHAR(200) NOT NULL DEFAULT ''"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_solution_plans_company_name ON solution_plans(company_name)"))
            logger.info("数据库迁移: solution_plans 表添加 company_name 列")
    except Exception as e:
        logger.warning(f"数据库迁移: solution_plans 添加 company_name 跳过: {e}")

    # 迁移：创建 column_display_configs 表（如果不存在）
    try:
        # Base.metadata.create_all 已自动创建表，这里只做兼容性检查
        result = await conn.execute(text("PRAGMA table_info(column_display_configs)"))
        cols = [row[1] for row in result.fetchall()]
        if "id" not in cols:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS column_display_configs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    page_type     VARCHAR(50) NOT NULL,
                    config_json   TEXT NOT NULL DEFAULT '[]',
                    created_at    DATETIME NOT NULL DEFAULT (datetime('now', '+8 hours')),
                    updated_at    DATETIME NOT NULL DEFAULT (datetime('now', '+8 hours')),
                    UNIQUE(user_id, page_type)
                )
            """))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_column_display_user_page ON column_display_configs(user_id, page_type)"
            ))
            logger.info("数据库迁移: 创建 column_display_configs 表")
    except Exception as e:
        logger.warning(f"数据库迁移: 创建 column_display_configs 表跳过: {e}")

    # 迁移：将 owner_id 改为可空（v2.0 数据隔离从 owner_id 改为 company_name）
    try:
        result = await conn.execute(text("PRAGMA table_info(products)"))
        cols_info = {row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]} for row in result.fetchall()}
        if cols_info.get("owner_id", {}).get("notnull") == 1:
            logger.info("数据库迁移: 重建 products 表（将 owner_id 改为可空）")
            col_defs = []
            for col_name, info in cols_info.items():
                nullable = "NULL" if info["notnull"] == 0 else "NOT NULL"
                if col_name == "owner_id":
                    nullable = "NULL"
                col_type = info["type"]
                pk_clause = "PRIMARY KEY" if info["pk"] == 1 else ""
                dflt = f"DEFAULT {info['dflt']}" if info["dflt"] is not None else ""
                col_defs.append(f'"{col_name}" {col_type} {nullable} {dflt} {pk_clause}'.strip())
            col_names = [f'"{c}"' for c in cols_info.keys()]
            await conn.execute(text("PRAGMA foreign_keys=OFF"))
            await conn.execute(text("BEGIN TRANSACTION"))
            await conn.execute(text(f'CREATE TABLE products_new ({", ".join(col_defs)})'))
            await conn.execute(text(f'INSERT INTO products_new ({", ".join(col_names)}) SELECT {", ".join(col_names)} FROM products'))
            await conn.execute(text("DROP TABLE products"))
            await conn.execute(text('ALTER TABLE products_new RENAME TO products'))
            await conn.execute(text("COMMIT"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            # 重新创建索引
            index_cols = ["quick_model", "product_model", "brand",
                          "category_level1", "category_level2", "category_level3",
                          "price", "specification", "barcode_69",
                          "company_name", "owner_id"]
            for col in index_cols:
                idx_name = f"ix_products_{col}"
                try:
                    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON products({col})"))
                except:
                    pass
            logger.info("数据库迁移: products 表 owner_id 改为可空完成")
    except Exception as e:
        logger.warning(f"数据库迁移: owner_id 改可空跳过: {e}")

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

    # 迁移：创建 companies 表（公司名 + 公司数据库密码，v3.0 数据隔离基于公司ID）
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS companies (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name  VARCHAR(200) NOT NULL UNIQUE,
                password_hash VARCHAR(256) NOT NULL,
                created_by    INTEGER DEFAULT 0,
                created_at    DATETIME,
                updated_at    DATETIME
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_company_name ON companies(company_name)"))
        logger.info("数据库迁移: companies 表就绪")
    except Exception as e:
        logger.warning(f"数据库迁移: companies 表跳过: {e}")

    # 迁移：为业务表添加 company_id 列（数据隔离基于公司ID）
    try:
        for table in ("users", "products", "solution_plans", "import_logs"):
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            cols = [row[1] for row in result.fetchall()]
            if "company_id" not in cols:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN company_id INTEGER DEFAULT 0"))
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_company_id ON {table}(company_id)"))
                logger.info(f"数据库迁移: {table} 表添加 company_id 列")
    except Exception as e:
        logger.warning(f"数据库迁移: company_id 列添加跳过: {e}")

    # 迁移：清除旧版测试数据（存量数据为测试数据，直接清除后重新初始化）
    # 判定条件：companies 表为空且存在非超级管理员账号 → 说明是从旧版（仅 company_name 隔离）升级而来
    try:
        company_count = (await conn.execute(text("SELECT COUNT(*) FROM companies"))).scalar() or 0
        user_count = (await conn.execute(text("SELECT COUNT(*) FROM users WHERE role != 'super_admin'"))).scalar() or 0
        if company_count == 0 and user_count > 0:
            for table in ("products", "solution_items", "solution_plans", "import_logs",
                          "column_display_configs", "invite_codes"):
                try:
                    await conn.execute(text(f"DELETE FROM {table}"))
                except Exception:
                    pass
            await conn.execute(text("DELETE FROM users WHERE role != 'super_admin'"))
            await conn.execute(text("UPDATE users SET company_id = 0, company_name = '' WHERE role = 'super_admin'"))
            logger.info("数据库迁移: 已清除旧版测试数据，等待重新初始化（seed 将重建公司/管理员绑定）")
    except Exception as e:
        logger.warning(f"数据库迁移: 清除旧版测试数据跳过: {e}")


async def init_db():
    """初始化数据库：创建所有表并执行迁移"""
    # 确保所有模型已注册到 metadata（真实应用由 main.py 导入 routers 间接导入 models；
    # 此处兜底导入，保证删除 data 目录后单独调用也能完整重建所有表）
    import app.models  # noqa: F401
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
