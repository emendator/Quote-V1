"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import CORS_ORIGINS, HOST, PORT
from app.database import init_db
from app.routers import products, import_data, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    await init_db()
    yield


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

# 服务上传的静态文件（图片等）
from app.config import UPLOAD_DIR
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# 健康检查
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "智能报价系统运行正常"}


# 生产环境：serve 前端静态文件
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
