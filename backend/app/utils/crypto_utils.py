"""加密工具 —— 用于用户名、API Key 等敏感信息的加密存储

采用 Fernet (AES-128-CBC) 加密：每次加密使用随机 IV，密文不可直接比较；
查询/唯一性校验通过确定性的 HMAC-SHA256 (hash_* 系列) 完成。
"""
import os
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import JWT_SECRET_KEY

# 使用 JWT_SECRET_KEY 派生加密密钥（固定 salt，保证重启后仍可解密）
def _derive_key(salt: bytes = b'smart_quotation_salt') -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(JWT_SECRET_KEY.encode()))
    return key

# 加密密钥与 HMAC 密钥（模块加载时计算一次）
_encryption_key = _derive_key()
_cipher = Fernet(_encryption_key)


def encrypt_text(plain_text: str) -> str:
    """加密敏感文本，返回加密后的字符串（空值返回空串）"""
    if not plain_text:
        return ""
    return _cipher.encrypt(plain_text.encode()).decode()


def decrypt_text(encrypted_text: str) -> str:
    """解密敏感文本，返回明文（失败返回空串）"""
    if not encrypted_text:
        return ""
    try:
        return _cipher.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return ""


def hash_text(plain_text: str) -> str:
    """计算确定性的 HMAC-SHA256 十六进制串（不可逆，用于唯一校验与等值查询）"""
    if not plain_text:
        return ""
    return hmac.new(_encryption_key, plain_text.encode(), hashlib.sha256).hexdigest()


# ========== 用户名 ==========
def encrypt_username(plain_text: str) -> str:
    """加密用户名（数据库以密文存储）"""
    return encrypt_text(plain_text)


def decrypt_username(encrypted_text: str) -> str:
    """解密用户名，返回明文"""
    return decrypt_text(encrypted_text)


def hash_username(plain_text: str) -> str:
    """计算用户名的 HMAC（用于登录/注册时的唯一查询，保证等值可查）"""
    return hash_text(plain_text)


# ========== API Key（保留原有函数名，兼容既有调用） ==========
def encrypt_api_key(plain_text: str) -> str:
    """加密 API Key，返回加密后的字符串"""
    return encrypt_text(plain_text)


def decrypt_api_key(encrypted_text: str) -> str:
    """解密 API Key，返回明文"""
    return decrypt_text(encrypted_text)
