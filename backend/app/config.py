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
# 密钥不写入源码：优先读取环境变量 JWT_SECRET_KEY；未设置时读取/生成 data/.jwt_secret_key
# （data/ 已被 .gitignore 忽略）。该密钥同时用于用户名、API Key 等敏感信息的加密，
# 生产环境请显式设置并妥善保管。
_JWT_SECRET_FILE = DATA_DIR / ".jwt_secret_key"


def _load_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if env_secret:
        return env_secret
    if _JWT_SECRET_FILE.exists():
        value = _JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = os.urandom(48).hex()
    _JWT_SECRET_FILE.write_text(value, encoding="utf-8")
    return value


JWT_SECRET_KEY = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

# 超级管理员预设账号（首次建库时用于创建；仓库不含任何默认口令，可用环境变量覆盖）
SUPER_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME", "admin")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "")
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "")
SUPER_ADMIN_COMPANY = os.getenv("SUPER_ADMIN_COMPANY", "默认公司")
SUPER_ADMIN_COMPANY_PASSWORD = os.getenv("SUPER_ADMIN_COMPANY_PASSWORD", "")
