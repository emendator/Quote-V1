"""FastAPI 应用入口"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import CORS_ORIGINS, HOST, PORT
from app.database import init_db
from app.routers import products, import_data, query, platforms
from app.services.cleanup_service import clean_all, FILE_MAX_AGE_HOURS, CLEANUP_INTERVAL_HOURS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


async def periodic_cleanup():
    """定时清理过期缓存文件"""
    while True:
        try:
            result = clean_all()
            if result["files_removed"] > 0 or result["cache_entries_removed"] > 0:
                logger.info(f"缓存清理完成: 文件 {result['files_removed']} 个, 缓存 {result['cache_entries_removed']} 条")
        except Exception as e:
            logger.warning(f"缓存清理异常: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库并开始定时清理"""
    await init_db()
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
app.include_router(platforms.router)


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
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
