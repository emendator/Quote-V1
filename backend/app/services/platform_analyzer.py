"""
平台 API 文档智能分析服务 —— 根据用户提供的电商平台 API 文档网址，
利用大模型自动提取对接所需的信息，生成配置字段模板。
"""
import json
import re
import logging
from typing import Dict, Any, Optional
import httpx
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

logger = logging.getLogger("platform_analyzer")

# AI 分析提示词
ANALYZE_SYSTEM_PROMPT = """你是一个电商平台 API 对接专家。请分析用户提供的 API 文档页面内容，提取该平台的对接信息。

你需要识别并返回以下 JSON 结构：

{
  "platform_name": "平台名称（中文，如'淘宝'、'京东'、'拼多多'）",
  "platform_type": "平台类型标识（英文小写，如 taobao、jd、pdd、douyin、kuaishou、weixin 等）",
  "api_endpoint": "API 网关地址（如 https://eco.taobao.com/router/rest）",
  "auth_method": "认证方式（oauth2 / apikey / none）",
  "auth_description": "认证流程的简要说明",
  "fields": [
    {
      "key": "api_key",
      "label": "显示名称（如'App Key'、'client_id'）",
      "type": "text / password / select",
      "required": true,
      "placeholder": "输入提示",
      "description": "字段说明",
      "options": []  // 仅 type=select 时提供
    },
    {
      "key": "api_secret",
      "label": "显示名称",
      "type": "password",
      "required": true,
      "placeholder": "",
      "description": ""
    },
    {
      "key": "shop_id",
      "label": "显示名称",
      "type": "text",
      "required": false,
      "placeholder": "",
      "description": ""
    },
    // 可能还有其他字段，如 callback_url、auth_code、seller_nick 等
  ],
  "extra_fields": [
    // 需要放在 extra_config 中的额外字段，如类目ID、运费模板ID等
    {
      "key": "province",
      "label": "所在省",
      "type": "text",
      "required": false,
      "placeholder": "浙江省",
      "description": "商品发货地所在省份"
    }
  ],
  "submit_api": {
    "method": "商品发布接口名（如 taobao.item.add）",
    "description": "接口说明"
  },
  "notes": "其他注意事项"
}

规则：
- 只返回 JSON，不要额外解释
- 如果页面内容不足以提取信息，fields 中至少返回 api_key、api_secret 两个基本字段
- platform_type 尽量使用通用英文标识
- 字段 key 尽量使用已有的标准名称：api_key、api_secret、shop_id、callback_url、auth_code
- extra_fields 中的字段会以 JSON 格式存入额外配置中
- 不确定的字段设置 required: false
"""


async def fetch_page_content(url: str) -> Optional[str]:
    """获取网页内容，提取有用的文本"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            resp.raise_for_status()
            html = resp.text

        # 提取页面标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # 去除 HTML 标签，提取纯文本
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # 限制内容长度（取前 30000 字符）
        content = text[:30000]

        result = f"页面标题: {title}\n\n页面内容:\n{content}"
        return result
    except httpx.TimeoutException:
        logger.warning(f"获取页面超时: {url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"获取页面HTTP错误 [{e.response.status_code}]: {url}")
        return None
    except Exception as e:
        logger.warning(f"获取页面失败: {url} - {e}")
        return None


async def analyze_doc_with_ai(page_content: str, url: str) -> Dict[str, Any]:
    """调用 DeepSeek 分析 API 文档内容"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    user_content = (
        f"请分析以下 API 文档内容，提取该电商平台的对接信息。\n\n"
        f"文档来源网址: {url}\n\n"
        f"文档内容:\n{page_content[:25000]}"
    )
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            # 清理可能的 markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content.strip())
            return result
    except json.JSONDecodeError as e:
        logger.error(f"AI 返回非 JSON: {e}")
        return _fallback_schema(url)
    except Exception as e:
        logger.error(f"AI 分析失败: {e}")
        return _fallback_schema(url)


def _fallback_schema(url: str) -> Dict[str, Any]:
    """AI 分析失败时的降级方案"""
    return {
        "platform_name": "未识别",
        "platform_type": "other",
        "api_endpoint": "",
        "auth_method": "apikey",
        "auth_description": "",
        "fields": [
            {
                "key": "api_key",
                "label": "App Key / client_id",
                "type": "text",
                "required": True,
                "placeholder": "请输入 App Key",
                "description": "平台应用的唯一标识"
            },
            {
                "key": "api_secret",
                "label": "App Secret / client_secret",
                "type": "password",
                "required": True,
                "placeholder": "请输入 App Secret",
                "description": "平台应用的密钥"
            },
            {
                "key": "shop_id",
                "label": "店铺ID",
                "type": "text",
                "required": False,
                "placeholder": "选填",
                "description": "店铺ID或商户号"
            },
        ],
        "extra_fields": [],
        "submit_api": {"method": "", "description": ""},
        "notes": f"AI 分析失败，已使用默认配置模板。源网址: {url}"
    }


async def analyze_platform_doc(url: str) -> Dict[str, Any]:
    """
    对外接口：输入 API 文档网址，返回分析后的平台配置字段模板
    """
    page_content = await fetch_page_content(url)
    if not page_content:
        return _fallback_schema(url)

    result = await analyze_doc_with_ai(page_content, url)
    # 保证必填字段存在
    if "fields" not in result:
        result["fields"] = []
    if "extra_fields" not in result:
        result["extra_fields"] = []
    return result
