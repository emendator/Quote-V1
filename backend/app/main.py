"""FastAPI 应用入口"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import CORS_ORIGINS, HOST, PORT, JWT_SECRET_KEY, JWT_SECRET_KEY_DEFAULT
from app.database import init_db, sync_engine
from app.routers import products, import_data, query, solutions, auth, invites, column_display, company
from app.services.cleanup_service import clean_all, FILE_MAX_AGE_HOURS, CLEANUP_INTERVAL_HOURS
from app.services.company_service import cleanup_orphan_companies, cleanup_expired_guests
from app.utils.crypto_utils import encrypt_api_key, hash_username
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


def auto_cleanup() -> dict:
    """自动清理：
    - 已过期的游客账号及其独立公司、业务数据（游客未主动退出时兜底清除使用痕迹）
    - 没有任何用户账号的公司及其业务数据
    返回清理统计。
    """
    try:
        with sync_engine.connect() as conn:
            expired_guests = cleanup_expired_guests(conn)
            removed_companies = cleanup_orphan_companies(conn)
            conn.commit()
        if expired_guests:
            logger.info(f"自动清理过期游客 {len(expired_guests)} 个: {expired_guests}")
        if removed_companies:
            logger.info(f"自动清理无账号公司 {len(removed_companies)} 家: {', '.join(removed_companies)}")
        return {"guests": expired_guests, "companies": removed_companies}
    except Exception as e:
        logger.warning(f"自动清理跳过: {e}")
        return {"guests": [], "companies": []}


async def periodic_cleanup():
    """定时清理过期缓存文件、过期游客与无账号公司"""
    while True:
        try:
            result = clean_all()
            if result["files_removed"] > 0 or result["cache_entries_removed"] > 0:
                logger.info(f"缓存清理完成: 文件 {result['files_removed']} 个, 缓存 {result['cache_entries_removed']} 条")
            auto_cleanup()
        except Exception as e:
            logger.warning(f"缓存清理异常: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库并开始定时清理"""
    # 安全提醒：若未通过环境变量覆盖 JWT_SECRET_KEY（其同时用于敏感信息加密），给出醒目提示
    if JWT_SECRET_KEY == JWT_SECRET_KEY_DEFAULT:
        logger.warning("当前使用默认 JWT_SECRET_KEY，生产环境请务必通过环境变量 JWT_SECRET_KEY 设置随机密钥（该密钥同时用于用户名/API Key 等敏感信息加密）")
    await init_db()
    # 启动时自动清理（过期游客、无账号公司；seed 已确保超级管理员公司绑定，不会被误删）
    auto_cleanup()
    # 初始化最高级管理员的 API Key（仅从环境变量读取；未配置则不写入，避免密钥硬编码在源码中）
    _default_admin_key = os.getenv("ADMIN_API_KEY", "")
    if _default_admin_key:
        try:
            with sync_engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id, api_key FROM users WHERE username_hash = :h"),
                    {"h": hash_username("admin")}
                ).fetchone()
                if row and not row[1]:
                    encrypted = encrypt_api_key(_default_admin_key)
                    conn.execute(
                        text("UPDATE users SET api_key = :key WHERE id = :id"),
                        {"key": encrypted, "id": row[0]}
                    )
                    conn.commit()
                    logger.info("已初始化最高级管理员的 DeepSeek API Key")
        except Exception as e:
            logger.warning(f"初始化 API Key 跳过: {e}")
    else:
        logger.warning("未设置 ADMIN_API_KEY 环境变量，最高级管理员 API Key 未自动初始化（可在个人菜单手动配置）")

    # 启动时立即执行一次清理
    result = clean_all()
    if result["files_removed"] > 0 or result["cache_entries_removed"] > 0:
        logger.info(f"启动清理: 文件 {result['files_removed']} 个, 缓存 {result['cache_entries_removed']} 条")
    # 启动后台定时清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    # 关闭时取消定时任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="智能报价系统 API",
    description="基于公司内部商品数据库的智能报价查询系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(products.router)
app.include_router(import_data.router)
app.include_router(query.router)
app.include_router(solutions.router)
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(column_display.router)
app.include_router(company.router)


# 健康检查
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "智能报价系统运行正常"}


# 手动触发缓存清理
@app.post("/api/cleanup")
async def trigger_cleanup():
    from app.services.cleanup_service import clean_all
    result = clean_all()
    return {
        "status": "ok",
        "files_removed": result["files_removed"],
        "cache_entries_removed": result["cache_entries_removed"],
    }


# 生产环境：serve 前端静态文件
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # reload=True 会启用文件监听器，在 Windows 上长时间运行可能不稳定
    # 开发时如需热重载可临时改为 reload=True，但生产/正式使用建议设为 False
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
