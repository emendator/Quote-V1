"""API Key 管理 —— 获取用户 API Key、更新 token 消耗"""
import logging
from typing import Optional, Tuple
from sqlalchemy import text
from app.database import sync_engine
from app.config import DEEPSEEK_API_URL, DEEPSEEK_MODEL
from app.utils.crypto_utils import decrypt_api_key
import httpx

logger = logging.getLogger("api_key_service")


def get_user_api_key(user_id: int) -> str:
    """获取指定用户的解密后 API Key（从数据库读取加密存储的 key）"""
    try:
        with sync_engine.connect() as conn:
            row = conn.execute(
                text("SELECT api_key FROM users WHERE id = :uid"),
                {"uid": user_id}
            ).fetchone()
            if row and row[0]:
                plain = decrypt_api_key(row[0])
                if plain:
                    return plain
    except Exception as e:
        logger.warning(f"获取用户 API Key 失败: {e}")
    return ""


def get_user_api_key_for_company_id(company_id: int) -> str:
    """获取指定公司ID对应的用户 API Key（取该公司第一个有 key 的用户）"""
    try:
        with sync_engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, api_key FROM users WHERE company_id = :c AND api_key != '' AND is_active = 1 LIMIT 1"),
                {"c": company_id}
            ).fetchone()
            if row and row[1]:
                plain = decrypt_api_key(row[1])
                if plain:
                    return plain
    except Exception as e:
        logger.warning(f"获取公司 API Key 失败: {e}")
    return ""


def add_token_usage(user_id: int, tokens: int):
    """给指定用户累计 token 消耗"""
    if tokens <= 0:
        return
    try:
        with sync_engine.connect() as conn:
            conn.execute(
                text("UPDATE users SET total_tokens_used = total_tokens_used + :tokens WHERE id = :uid"),
                {"tokens": tokens, "uid": user_id}
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"更新 token 消耗失败: {e}")


async def call_deepseek_with_user_key(
    user_id: int,
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> Tuple[Optional[dict], int]:
    """使用指定用户的 API Key 调用 DeepSeek，返回 (响应JSON, 消耗token数)"""
    api_key = get_user_api_key(user_id)
    if not api_key:
        logger.warning(f"用户 {user_id} 未配置 API Key")
        return None, 0

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # 从响应中提取 token 消耗
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            # 记录 token 消耗
            add_token_usage(user_id, total_tokens)
            return data, total_tokens
    except httpx.TimeoutException:
        logger.error("DeepSeek API 请求超时")
        return None, 0
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")
        return None, 0
