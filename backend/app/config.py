"""应用配置"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录：数据库、上传文件等运行时数据统一放在项目 data 目录下（删除后可自动重建）
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库配置 - SQLite 文件存放在项目 data 目录下
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR / 'data.db'}")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", f"sqlite:///{DATA_DIR / 'data.db'}")

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS 配置 - 允许前端开发服务器跨域
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

# 上传文件配置（位于 data 目录下，随 data 一起可重建）
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 输出文件配置（导出/生成文件的输出缓存，位于 data 目录下，删除后可重建）
OUTPUT_DIR = DATA_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# DeepSeek API 配置（AI 智能查询）
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# JWT 配置（用户认证）
# 开发默认值仅用于开箱即用；生产环境必须通过环境变量 JWT_SECRET_KEY 覆盖（该密钥同时用于敏感信息加密）
JWT_SECRET_KEY_DEFAULT = "***REMOVED-SECRET***"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", JWT_SECRET_KEY_DEFAULT)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

# 超级管理员预设账号（永久固定：每次重建数据库时以此创建，不可更改）
SUPER_ADMIN_USERNAME = "admin"
SUPER_ADMIN_PASSWORD = "***REMOVED-PASSWORD***"
SUPER_ADMIN_EMAIL = "***REMOVED-EMAIL***"
SUPER_ADMIN_COMPANY = "***REMOVED-COMPANY***"
SUPER_ADMIN_COMPANY_PASSWORD = "***REMOVED-PASSWORD***"  # 最高级管理员公司对应的公司数据库密码
