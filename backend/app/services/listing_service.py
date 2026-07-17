"""
一键上架服务 —— 平台适配器模式 + 上架业务逻辑

架构说明：
- BaseAdapter: 抽象基类，定义平台适配器接口
- TaobaoAdapter / JDAdapter / PinduoduoAdapter: 各平台具体实现
- ListingService: 上架业务编排，选择适配器、执行上架、记录日志

扩展新平台：只需继承 BaseAdapter 并实现抽象方法，然后在 ADAPTER_REGISTRY 中注册即可。

各平台 API 参考文档：
- 淘宝开放平台: https://open.taobao.com/docs/api_list.htm
- 京东宙斯: https://jos.jd.com/apilist
- 拼多多开放平台: https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5
"""
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models import Product, PlatformConfig, ListingLog

logger = logging.getLogger("listing_service")


# ======================================================================
# 工具函数：签名算法
# ======================================================================

def _md5_sign(params: Dict[str, str], secret: str) -> str:
    """
    MD5 签名算法（淘宝/京东/拼多多通用）

    规则: 将所有参数按 key 升序排列，拼接为 key1value1key2value2...，
    首尾加上 secret，MD5 加密后转大写。
    """
    sorted_keys = sorted(params.keys())
    raw = secret + "".join(f"{k}{params[k]}" for k in sorted_keys) + secret
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def _hmac_sha256_sign(params: Dict[str, str], secret: str) -> str:
    """HMAC-SHA256 签名（淘宝可选）"""
    sorted_keys = sorted(params.keys())
    raw = "".join(f"{k}{params[k]}" for k in sorted_keys)
    import hmac
    h = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256)
    return h.hexdigest().upper()


# ======================================================================
# 平台适配器基类
# ======================================================================

class BaseAdapter(ABC):
    """平台适配器抽象基类"""

    # ==================== 子类需覆盖的常量 ====================
    PLATFORM_TYPE = ""          # 平台类型标识
    API_ENDPOINT = ""           # API 网关地址（正式环境）
    API_ENDPOINT_DEV = ""       # API 网关地址（沙箱/预发环境）

    def __init__(self, config: PlatformConfig):
        self.config = config
        self._extra = json.loads(config.extra_config) if isinstance(config.extra_config, str) else (config.extra_config or {})
        self._access_token: Optional[str] = None

    # ==================== 必须实现的抽象方法 ====================

    @abstractmethod
    async def authenticate(self) -> str:
        """
        OAuth2.0 认证，获取 access_token

        各平台 OAuth 文档：
        - 淘宝: https://open.taobao.com/doc.htm?docId=102635&docType=1
        - 京东: https://jos.jd.com/commondoc?listId=32
        - 拼多多: https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5
        """
        ...

    @abstractmethod
    async def transform_product(self, product: Product) -> Dict[str, Any]:
        """将本地商品数据转换为目标平台要求的商品发布格式"""
        ...

    @abstractmethod
    async def submit_product(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        调用平台商品发布 API 提交商品
        返回 (是否成功, 平台商品ID, 错误信息)
        """
        ...

    # ==================== 可选覆写的方法 ====================

    def _get_endpoint(self) -> str:
        """获取 API 地址（优先使用配置的，否则使用默认）"""
        if self.config.api_base_url:
            return self.config.api_base_url
        return self._extra.get("use_sandbox", False) and self.API_ENDPOINT_DEV or self.API_ENDPOINT

    async def test_connection(self) -> Tuple[bool, str]:
        """测试平台连接是否可用"""
        try:
            await self.authenticate()
            return True, "连接测试成功"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"


# ======================================================================
# 淘宝/天猫适配器
# ======================================================================
# API 文档: https://open.taobao.com/docs/api_list.htm
# 商品发布接口: taobao.item.add
# 正式环境: https://eco.taobao.com/router/rest
# 沙箱环境: https://apitest.taobao.com/router/rest

class TaobaoAdapter(BaseAdapter):
    """淘宝/天猫平台适配器"""

    PLATFORM_TYPE = "taobao"
    API_ENDPOINT = "https://eco.taobao.com/router/rest"
    API_ENDPOINT_DEV = "https://apitest.taobao.com/router/rest"

    async def authenticate(self) -> str:
        """
        淘宝 OAuth2.0 认证

        文档: https://open.taobao.com/doc.htm?docId=102635&docType=1
        流程:
        1. 引导用户访问授权页:
           https://oauth.taobao.com/authorize?response_type=code&client_id={app_key}&redirect_uri={callback_url}&state={state}
        2. 用户授权后回调得到 code
        3. 用 code 换取 access_token:
           POST https://oauth.taobao.com/token
           ?grant_type=authorization_code&code={code}&client_id={app_key}
           &client_secret={app_secret}&redirect_uri={callback_url}
        4. 得到 access_token（有效期约 1 天，需用 refresh_token 刷新）
        """
        logger.info(f"[Taobao] 认证平台: {self.config.name}")
        if not self.config.api_key:
            raise ValueError("API密钥(app_key)未配置")
        if not self.config.api_secret:
            raise ValueError("API密钥(app_secret)未配置")

        # 如果已有 token 且未过期，直接返回
        if self._access_token:
            return self._access_token

        # === 以下为 OAuth2.0 获取 token 的完整实现（取消注释即可使用）===
        #
        # async with httpx.AsyncClient(timeout=30.0) as client:
        #     token_resp = await client.post(
        #         "https://oauth.taobao.com/token",
        #         data={
        #             "grant_type": "authorization_code",
        #             "code": self._extra.get("auth_code", ""),
        #             "client_id": self.config.api_key,
        #             "client_secret": self.config.api_secret,
        #             "redirect_uri": self._extra.get("callback_url", ""),
        #         },
        #     )
        #     token_data = token_resp.json()
        #     if "access_token" not in token_data:
        #         raise ValueError(f"淘宝授权失败: {token_data.get('error_description', '未知错误')}")
        #     self._access_token = token_data["access_token"]
        #     # 保存 refresh_token 和过期时间到 extra_config
        #     self._extra["refresh_token"] = token_data.get("refresh_token", "")
        #     self._extra["expires_in"] = token_data.get("expires_in", 0)
        #     return self._access_token

        # 模拟返回
        self._access_token = f"taobao_token_{self.config.id}_{int(datetime.now().timestamp())}"
        return self._access_token

    async def transform_product(self, product: Product) -> Dict[str, Any]:
        """
        转换为 taobao.item.add 接口请求参数

        文档: https://open.taobao.com/docs/api.htm?docId=4&docType=2
        必填字段: num_iid(外部商品ID), title(标题), price(价格), desc(描述),
                 cat_id(类目ID), props(属性), location.state(所在地省),
                 location.city(所在地市)
        """
        # 生成商品描述（纯文本或HTML）
        desc_text = (
            f"品牌: {product.brand or '无'}\\n"
            f"型号: {product.product_model or '无'}\\n"
            f"规格: {product.specification or '无'}\\n"
            f"{product.recommendation or ''}\\n"
            f"69码: {product.barcode_69 or '无'}"
        )

        return {
            # ----- 基本字段 -----
            "outer_id": product.quick_model or product.product_model,
            "title": (product.product_name or product.product_model)[:60],  # 淘宝标题最长60字符
            "price": str(product.price),
            "num": str(product.sales_volume or 999),  # 库存数量
            "cat_id": self._extra.get("taobao_cat_id", "50008055"),  # 类目ID，需在淘宝开放平台查询

            # ----- 商品描述 -----
            "desc": desc_text,
            "sell_point": (product.recommendation or "")[:30],  # 卖点，最长30字

            # ----- 属性信息 -----
            "props": [
                {"pid": "品牌", "value": product.brand or "其他"},
                {"pid": "型号", "value": product.product_model or ""},
                {"pid": "规格", "value": product.specification or ""},
                {"pid": "货号", "value": product.quick_model or ""},
            ],

            # ----- 图片 -----
            "images": [product.image] if product.image and product.image.startswith("http") else [],
            "input_pids": "",  # 自定义属性ID
            "input_str": "",   # 自定义属性值

            # ----- 物流信息 -----
            "weight": str(product.gross_weight or 0),
            "freight_id": self._extra.get("taobao_freight_id", ""),  # 运费模板ID

            # ----- 条码 -----
            "barcode": product.barcode_69,

            # ----- 销售属性 -----
            "location.state": self._extra.get("province", "浙江省"),
            "location.city": self._extra.get("city", "杭州市"),
        }

    async def submit_product(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        调用 taobao.item.add 发布商品

        文档: https://open.taobao.com/docs/api.htm?docId=4&docType=2
        SDK 方式:
            TaobaoClient client = new DefaultTaobaoClient(url, appKey, appSecret);
            ItemAddRequest req = new ItemAddRequest();
            // ... 设置参数
            ItemAddResponse rsp = client.execute(req, sessionKey);

        HTTP 直调:
            https://eco.taobao.com/router/rest?method=taobao.item.add
            &app_key={app_key}&session={access_token}&timestamp={ts}
            &v=2.0&sign_method=md5&format=json&sign={sign}
            &title={title}&price={price}&num={num}&desc={desc}...
        """
        logger.info(f"[Taobao] 提交商品: {data.get('title')}")

        # === 真实 HTTP 调用实现（取消注释即可使用）===
        #
        # try:
        #     # 1. 组装系统参数
        #     sys_params = {
        #         "method": "taobao.item.add",
        #         "app_key": self.config.api_key,
        #         "session": self._access_token or "",
        #         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #         "v": "2.0",
        #         "sign_method": "md5",
        #         "format": "json",
        #     }
        #
        #     # 2. 组装业务参数（扁平化）
        #     biz_params = {
        #         "outer_id": data["outer_id"],
        #         "title": data["title"],
        #         "price": data["price"],
        #         "num": data["num"],
        #         "cat_id": data["cat_id"],
        #         "desc": data["desc"],
        #         "sell_point": data.get("sell_point", ""),
        #         "weight": data.get("weight", "0"),
        #         "barcode": data.get("barcode", ""),
        #         "location.state": data.get("location.state", "浙江省"),
        #         "location.city": data.get("location.city", "杭州市"),
        #     }
        #     if data.get("freight_id"):
        #         biz_params["freight_id"] = data["freight_id"]
        #
        #     # 3. 所有参数合并签名
        #     all_params = {**sys_params, **biz_params}
        #     sign = _md5_sign(all_params, self.config.api_secret)
        #     all_params["sign"] = sign
        #
        #     # 4. 发起请求
        #     async with httpx.AsyncClient(timeout=60.0) as client:
        #         resp = await client.post(
        #             self._get_endpoint(),
        #             data=all_params,
        #         )
        #         result = resp.json()
        #
        #     # 5. 解析响应
        #     # 成功响应: {"item_add_response": {"item": {"num_iid": 12345678901, ...}}}
        #     # 失败响应: {"error_response": {"code": 50, "msg": "...", "sub_code": "...", "sub_msg": "..."}}
        #     if "error_response" in result:
        #         error = result["error_response"]
        #         error_msg = f"[{error.get('sub_code', '')}] {error.get('sub_msg', error.get('msg', '未知错误'))}"
        #         logger.error(f"[Taobao] 上架失败: {error_msg}")
        #         return False, "", error_msg
        #
        #     item = result.get("item_add_response", {}).get("item", {})
        #     platform_id = str(item.get("num_iid", ""))
        #     logger.info(f"[Taobao] 上架成功, 商品ID: {platform_id}")
        #     return True, platform_id, ""
        #
        # except httpx.TimeoutException:
        #     return False, "", "请求超时，请稍后重试"
        # except Exception as e:
        #     return False, "", f"请求异常: {str(e)}"

        # === 模拟实现 ===
        import random
        platform_id = f"tb_{random.randint(1000000000, 9999999999)}"
        return True, platform_id, ""


# ======================================================================
# 京东适配器
# ======================================================================
# API 文档: https://jos.jd.com/apilistnewdetail.html?first=440&second=442
# 商品创建接口: jingdong.ware.add
# 正式环境: https://api.jd.com/routerjson
# 网关文档: https://jos.jd.com/commondoc?listId=33

class JDAdapter(BaseAdapter):
    """京东平台适配器"""

    PLATFORM_TYPE = "jd"
    API_ENDPOINT = "https://api.jd.com/routerjson"
    API_ENDPOINT_DEV = "https://api-dev.jd.com/routerjson"

    async def authenticate(self) -> str:
        """
        京东 OAuth2.0 认证

        文档: https://jos.jd.com/commondoc?listId=32
        流程:
        1. 引导用户访问授权页:
           https://open-oauth.jd.com/oauth2/to_login?app_key={app_key}
           &response_type=code&redirect_uri={callback_url}&state={state}
        2. 用户授权后回调得到 code
        3. 用 code 换取 access_token:
           POST https://open-oauth.jd.com/oauth2/access_token
           ?app_key={app_key}&app_secret={app_secret}&grant_type=authorization_code
           &code={code}&redirect_uri={callback_url}
        """
        logger.info(f"[JD] 认证平台: {self.config.name}")
        if not self.config.api_key:
            raise ValueError("API密钥(app_key)未配置")
        if not self.config.api_secret:
            raise ValueError("API密钥(app_secret)未配置")

        if self._access_token:
            return self._access_token

        # === OAuth2.0 获取 token（取消注释即可使用）===
        #
        # async with httpx.AsyncClient(timeout=30.0) as client:
        #     token_resp = await client.post(
        #         "https://open-oauth.jd.com/oauth2/access_token",
        #         data={
        #             "app_key": self.config.api_key,
        #             "app_secret": self.config.api_secret,
        #             "grant_type": "authorization_code",
        #             "code": self._extra.get("auth_code", ""),
        #             "redirect_uri": self._extra.get("callback_url", ""),
        #         },
        #     )
        #     token_data = token_resp.json()
        #     if "access_token" not in token_data:
        #         raise ValueError(f"京东授权失败: {token_data}")
        #     self._access_token = token_data["access_token"]
        #     return self._access_token

        self._access_token = f"jd_token_{self.config.id}_{int(datetime.now().timestamp())}"
        return self._access_token

    async def transform_product(self, product: Product) -> Dict[str, Any]:
        """
        转换为 jingdong.ware.add 接口请求参数

        文档: https://jos.jd.com/apilistnewdetail.html?first=440&second=442
        注意: 京东商品 API 的业务参数需放入 360buy_param_json 字段（JSON 字符串）
        """
        return {
            # ----- 基本字段 -----
            "ware_id": 0,                              # 商品ID(新添0)
            "title": (product.product_name or product.product_model)[:60],  # 商品名(最长60)
            "cid": int(self._extra.get("jd_category_id", 0)),  # 类目ID
            "shop_category": self._extra.get("jd_shop_category", ""),  # 店内分类

            # ----- 价格与库存 -----
            "stock_num": product.sales_volume or 999,   # 库存
            "price": product.price,                     # 价格
            "market_price": product.retail_price or product.price,  # 市场价
            "cost_price": product.purchase_price or 0,  # 成本价

            # ----- 商品信息 -----
            "brand_name": product.brand or "",
            "model": product.product_model or "",
            "barcode": product.barcode_69 or "",
            "weight": str(product.gross_weight or 0),
            "packing": product.box_spec or "",
            "sku_properties": product.specification or "",

            # ----- 描述 -----
            "description": (
                f"品牌: {product.brand}\\n"
                f"型号: {product.product_model}\\n"
                f"规格: {product.specification}\\n"
                f"{product.recommendation or ''}"
            ),
            "introduction": product.recommendation or "",  # 促销语
            "warranty": self._extra.get("warranty", ""),   # 保修期

            # ----- 图片 -----
            "images": [product.image] if product.image and product.image.startswith("http") else [],
            "logo": product.image if product.image and product.image.startswith("http") else "",

            # ----- 物流 -----
            "freight_id": int(self._extra.get("jd_freight_id", 0)),  # 运费模板
            "delivery": self._extra.get("delivery", "T"),  # 是否送货(T/F)

            # ----- 参数 -----
            "param": product.parameters or "",
            "remark": product.remark or "",
            "upc": product.barcode_69 or "",
        }

    async def submit_product(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        调用 jingdong.ware.add 创建商品

        文档: https://jos.jd.com/apilistnewdetail.html?first=440&second=442
        京东 API 调用特点:
        - 业务参数用 JSON 字符串放入 360buy_param_json 字段
        - 签名算法: MD5(appSecret + key1value1key2value2... + appSecret)
        - 所有参数需要 URL encode
        """
        logger.info(f"[JD] 提交商品: {data.get('title')}")

        # === 真实 HTTP 调用实现（取消注释即可使用）===
        #
        # try:
        #     # 1. 业务参数（放入 360buy_param_json）
        #     biz_json = json.dumps({
        #         "ware_id": 0,
        #         "title": data["title"],
        #         "cid": data["cid"],
        #         "stock_num": data.get("stock_num", 999),
        #         "price": data["price"],
        #         "brand_name": data.get("brand_name", ""),
        #         "barcode": data.get("barcode", ""),
        #         "weight": data.get("weight", "0"),
        #     }, ensure_ascii=False)
        #
        #     # 2. 系统参数
        #     sys_params = {
        #         "method": "jingdong.ware.add",
        #         "access_token": self._access_token or "",
        #         "app_key": self.config.api_key,
        #         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #         "v": "2.0",
        #         "360buy_param_json": biz_json,
        #     }
        #
        #     # 3. 生成签名
        #     sign = _md5_sign(sys_params, self.config.api_secret)
        #     sys_params["sign"] = sign
        #
        #     # 4. 发起请求（GET 或 POST）
        #     async with httpx.AsyncClient(timeout=60.0) as client:
        #         resp = await client.get(
        #             self._get_endpoint(),
        #             params=sys_params,
        #         )
        #         result = resp.json()
        #
        #     # 5. 解析响应
        #     # 成功: {"jingdong_ware_add_response": {"ware_id": 12345, ...}}
        #     # 失败: {"error_response": {"code": 120, "msg": "...", ...}}
        #     add_response = result.get("jingdong_ware_add_responce")  # 注意文档中的拼写
        #     if not add_response:
        #         error = result.get("error_response", {})
        #         error_msg = error.get("msg", "未知错误")
        #         logger.error(f"[JD] 上架失败: {error_msg}")
        #         return False, "", error_msg
        #
        #     platform_id = str(add_response.get("ware_id", ""))
        #     logger.info(f"[JD] 上架成功, 商品ID: {platform_id}")
        #     return True, platform_id, ""
        #
        # except httpx.TimeoutException:
        #     return False, "", "请求超时"
        # except Exception as e:
        #     return False, "", f"请求异常: {str(e)}"

        # === 模拟实现 ===
        import random
        platform_id = f"jd_{random.randint(1000000000, 9999999999)}"
        return True, platform_id, ""


# ======================================================================
# 拼多多适配器
# ======================================================================
# API 文档: https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5
# 商品发布接口: pdd.goods.add
# 正式环境: https://gw-api.pinduoduo.com/api/router
# 授权文档: https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5

class PinduoduoAdapter(BaseAdapter):
    """拼多多平台适配器"""

    PLATFORM_TYPE = "pinduoduo"
    API_ENDPOINT = "https://gw-api.pinduoduo.com/api/router"
    API_ENDPOINT_DEV = "https://gw-api.pinduoduo.com/api/router"  # 拼多多无独立沙箱

    async def authenticate(self) -> str:
        """
        拼多多 OAuth2.0 认证

        文档: https://open.pinduoduo.com/application/document/browse?idStr=BD3A776A4D41D5F5
        流程:
        1. 引导用户访问授权页:
           WEB: https://fuwu.pinduoduo.com/service-market/auth
                ?response_type=code&client_id={client_id}
                &redirect_uri={callback_url}&state={state}
           H5: https://mai.pinduoduo.com/h5-login.html
                ?response_type=code&client_id={client_id}
                &redirect_uri={callback_url}&state={state}
        2. 用户授权后回调得到 code
        3. 用 code 换取 access_token:
           https://gw-api.pinduoduo.com/api/router
           ?type=pdd.pop.auth.token.create&client_id={client_id}
           &code={code}&timestamp={ts}&sign={sign}
        """
        logger.info(f"[Pinduoduo] 认证平台: {self.config.name}")
        if not self.config.api_key:
            raise ValueError("client_id 未配置")
        if not self.config.api_secret:
            raise ValueError("client_secret 未配置")

        if self._access_token:
            return self._access_token

        # === OAuth2.0 获取 token（取消注释即可使用）===
        #
        # params = {
        #     "type": "pdd.pop.auth.token.create",
        #     "client_id": self.config.api_key,
        #     "code": self._extra.get("auth_code", ""),
        #     "timestamp": str(int(datetime.now().timestamp())),
        #     "data_type": "JSON",
        # }
        # sign = _md5_sign(params, self.config.api_secret)
        # params["sign"] = sign
        #
        # async with httpx.AsyncClient(timeout=30.0) as client:
        #     resp = await client.post(self._get_endpoint(), data=params)
        #     token_data = resp.json()
        #
        # auth_resp = token_data.get("pop_auth_token_create_response", {})
        # if "access_token" not in auth_resp:
        #     raise ValueError(f"拼多多授权失败: {token_data}")
        # self._access_token = auth_resp["access_token"]
        # # 保存刷新信息
        # self._extra["refresh_token"] = auth_resp.get("refresh_token", "")
        # return self._access_token

        self._access_token = f"pdd_token_{self.config.id}_{int(datetime.now().timestamp())}"
        return self._access_token

    async def transform_product(self, product: Product) -> Dict[str, Any]:
        """
        转换为 pdd.goods.add 接口请求参数

        文档: https://open.pinduoduo.com/application/document/api?id=pdd.goods.add
        必填字段: goods_name, goods_desc, goods_price, goods_quantity, cat_id
        """
        return {
            # ----- 基本字段 -----
            "goods_name": (product.product_name or product.product_model)[:60],  # 商品名称(最长60)
            "goods_desc": (
                f"品牌: {product.brand}\\n"
                f"型号: {product.product_model}\\n"
                f"规格: {product.specification}\\n"
                f"{product.recommendation or ''}"
            ),
            "cat_id": int(self._extra.get("pdd_cat_id", 0)),  # 类目ID，必填
            "market_price": int((product.retail_price or product.price) * 100),  # 市场价(分)
            "goods_price": int(product.price * 100),     # 拼团价(分)
            "single_goods_price": int(product.price * 100),  # 单买价(分)
            "goods_quantity": product.sales_volume or 999,   # 库存

            # ----- 商品属性 -----
            "brand_id": int(self._extra.get("pdd_brand_id", 0)),  # 品牌ID
            "specification": product.specification or "",
            "model": product.product_model or "",
            "barcode": product.barcode_69 or "",

            # ----- 物流 -----
            "weight": int(product.gross_weight or 0),    # 重量(g)
            "freight_id": int(self._extra.get("pdd_freight_id", 0)),  # 运费模板ID
            "country_id": int(self._extra.get("country_id", 0)),  # 国家ID(0=中国)

            # ----- 图片 -----
            "image_url": product.image if product.image and product.image.startswith("http") else "",
            "carousel_gallery": (
                [{"image_url": product.image}]
                if product.image and product.image.startswith("http") else []
            ),

            # ----- 其他 -----
            "out_goods_id": product.quick_model or product.product_model,  # 外部商品ID
            "is_refundable": 1,   # 是否支持退款
            "is_sku_preview": 0,  # 是否预览
            "need_delivery": 1,   # 是否需要配送
        }

    async def submit_product(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        调用 pdd.goods.add 发布商品

        文档: https://open.pinduoduo.com/application/document/api?id=pdd.goods.add
        拼多多 API 调用特点:
        - 业务参数直接作为顶层参数
        - 签名算法: MD5(client_secret + key1value1key2value2... + client_secret)
        - 系统参数: type, data_type, client_id, timestamp, sign, access_token
        """
        logger.info(f"[Pinduoduo] 提交商品: {data.get('goods_name')}")

        # === 真实 HTTP 调用实现（取消注释即可使用）===
        #
        # try:
        #     # 1. 系统参数
        #     sys_params = {
        #         "type": "pdd.goods.add",
        #         "data_type": "JSON",
        #         "client_id": self.config.api_key,
        #         "timestamp": str(int(datetime.now().timestamp())),
        #         "access_token": self._access_token or "",
        #     }
        #
        #     # 2. 业务参数（直接扁平化）
        #     biz_params = {
        #         "goods_name": data["goods_name"],
        #         "goods_desc": data["goods_desc"],
        #         "cat_id": str(data["cat_id"]),
        #         "market_price": str(data["market_price"]),
        #         "goods_price": str(data["goods_price"]),
        #         "goods_quantity": str(data.get("goods_quantity", 999)),
        #         "out_goods_id": data.get("out_goods_id", ""),
        #         "is_refundable": "1",
        #         "need_delivery": "1",
        #     }
        #
        #     # 3. 合并并签名
        #     all_params = {**sys_params, **biz_params}
        #     sign = _md5_sign(all_params, self.config.api_secret)
        #     all_params["sign"] = sign
        #
        #     # 4. POST 请求
        #     async with httpx.AsyncClient(timeout=60.0) as client:
        #         resp = await client.post(self._get_endpoint(), data=all_params)
        #         result = resp.json()
        #
        #     # 5. 解析响应
        #     # 成功: {"goods_add_response": {"goods_id": 123456789, ...}}
        #     # 失败: {"error_response": {"error_code": 50000, "error_msg": "...", "sub_msg": "..."}}
        #     add_response = result.get("goods_add_response", {})
        #     if not add_response or "goods_id" not in add_response:
        #         error = result.get("error_response", {})
        #         sub_msg = error.get("sub_msg", "")
        #         error_msg = error.get("error_msg", sub_msg or "未知错误")
        #         logger.error(f"[Pinduoduo] 上架失败: {error_msg}")
        #         return False, "", error_msg
        #
        #     platform_id = str(add_response.get("goods_id", ""))
        #     logger.info(f"[Pinduoduo] 上架成功, 商品ID: {platform_id}")
        #     return True, platform_id, ""
        #
        # except httpx.TimeoutException:
        #     return False, "", "请求超时"
        # except Exception as e:
        #     return False, "", f"请求异常: {str(e)}"

        # === 模拟实现 ===
        import random
        platform_id = f"pdd_{random.randint(1000000000, 9999999999)}"
        return True, platform_id, ""


# ======================================================================
# 适配器注册表
# ======================================================================

ADAPTER_REGISTRY = {
    "taobao": TaobaoAdapter,
    "jd": JDAdapter,
    "pinduoduo": PinduoduoAdapter,
}


def get_adapter(config: PlatformConfig) -> BaseAdapter:
    """根据平台配置获取对应的适配器实例"""
    adapter_cls = ADAPTER_REGISTRY.get(config.platform_type)
    if not adapter_cls:
        raise ValueError(f"不支持的平台类型: {config.platform_type}，支持的平台: {list(ADAPTER_REGISTRY.keys())}")
    return adapter_cls(config)


# ======================================================================
# 上架服务
# ======================================================================

class ListingService:
    """一键上架服务"""

    async def submit_listing(
        self,
        db: AsyncSession,
        product_ids: List[int],
        platform_ids: List[int],
    ) -> Dict[str, Any]:
        """
        提交商品上架到指定平台

        返回:
        {
            "total": int,
            "success": int,
            "failed": int,
            "results": [
                {"product_id": int, "platform_id": int, "status": str, "platform_product_id": str, "error_message": str},
            ]
        }
        """
        # 1. 查询商品
        product_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in product_result.scalars().all()}

        # 2. 查询平台配置（仅已启用的）
        platform_result = await db.execute(
            select(PlatformConfig).where(
                PlatformConfig.id.in_(platform_ids),
                PlatformConfig.is_active == 1,
            )
        )
        platforms = {p.id: p for p in platform_result.scalars().all()}

        # 3. 执行上架
        results = []
        success_count = 0
        failed_count = 0

        for pid in product_ids:
            product = products.get(pid)
            if not product:
                results.append({
                    "product_id": pid,
                    "platform_id": 0,
                    "status": "failed",
                    "platform_product_id": "",
                    "error_message": "商品不存在",
                })
                failed_count += 1
                continue

            for plat_id in platform_ids:
                platform = platforms.get(plat_id)
                if not platform:
                    results.append({
                        "product_id": pid,
                        "platform_id": plat_id,
                        "status": "failed",
                        "platform_product_id": "",
                        "error_message": "平台配置不存在或已禁用",
                    })
                    failed_count += 1
                    continue

                # 执行上架
                result = await self._list_single_product(db, product, platform)
                results.append(result)
                if result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1

        return {
            "total": len(product_ids) * len(platform_ids),
            "success": success_count,
            "failed": failed_count,
            "results": results,
        }

    async def _list_single_product(
        self,
        db: AsyncSession,
        product: Product,
        platform: PlatformConfig,
    ) -> Dict[str, Any]:
        """将单个商品上架到单个平台"""
        try:
            # 获取适配器
            adapter = get_adapter(platform)

            # 认证
            await adapter.authenticate()

            # 转换商品数据
            platform_data = await adapter.transform_product(product)

            # 记录请求数据
            request_data = json.dumps(platform_data, ensure_ascii=False, default=str)

            # 提交到平台
            is_success, platform_product_id, error_msg = await adapter.submit_product(platform_data)

            # 记录日志
            log = ListingLog(
                product_id=product.id,
                product_model=product.product_model or "",
                product_name=product.product_name or "",
                platform_id=platform.id,
                platform_name=platform.name,
                status="success" if is_success else "failed",
                platform_product_id=platform_product_id,
                request_data=request_data,
                response_data=json.dumps({
                    "success": is_success,
                    "platform_product_id": platform_product_id,
                    "error": error_msg,
                }),
                error_message=error_msg,
            )
            db.add(log)
            await db.flush()

            if is_success:
                logger.info(f"上架成功: 商品[{product.id}] → 平台[{platform.name}], 平台ID: {platform_product_id}")
                return {
                    "product_id": product.id,
                    "platform_id": platform.id,
                    "status": "success",
                    "platform_product_id": platform_product_id,
                    "error_message": "",
                }
            else:
                logger.warning(f"上架失败: 商品[{product.id}] → 平台[{platform.name}]: {error_msg}")
                return {
                    "product_id": product.id,
                    "platform_id": platform.id,
                    "status": "failed",
                    "platform_product_id": "",
                    "error_message": error_msg,
                }

        except ValueError as e:
            # 不支持的平台类型
            log = ListingLog(
                product_id=product.id,
                product_model=product.product_model or "",
                product_name=product.product_name or "",
                platform_id=platform.id,
                platform_name=platform.name,
                status="failed",
                error_message=str(e),
            )
            db.add(log)
            await db.flush()
            return {
                "product_id": product.id,
                "platform_id": platform.id,
                "status": "failed",
                "platform_product_id": "",
                "error_message": str(e),
            }
        except Exception as e:
            logger.error(f"上架异常: 商品[{product.id}] → 平台[{platform.name}]: {e}")
            log = ListingLog(
                product_id=product.id,
                product_model=product.product_model or "",
                product_name=product.product_name or "",
                platform_id=platform.id,
                platform_name=platform.name,
                status="failed",
                error_message=f"系统异常: {str(e)}",
            )
            db.add(log)
            await db.flush()
            return {
                "product_id": product.id,
                "platform_id": platform.id,
                "status": "failed",
                "platform_product_id": "",
                "error_message": f"系统异常: {str(e)}",
            }

    async def get_listing_logs(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        platform_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> Tuple[List[ListingLog], int]:
        """查询上架日志（分页）"""
        query = select(ListingLog)
        count_query = select(func.count(ListingLog.id))

        if status:
            query = query.where(ListingLog.status == status)
            count_query = count_query.where(ListingLog.status == status)
        if platform_id:
            query = query.where(ListingLog.platform_id == platform_id)
            count_query = count_query.where(ListingLog.platform_id == platform_id)
        if product_id:
            query = query.where(ListingLog.product_id == product_id)
            count_query = count_query.where(ListingLog.product_id == product_id)

        # 按时间倒序
        query = query.order_by(desc(ListingLog.created_at))

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_listing_log_detail(self, db: AsyncSession, log_id: int) -> Optional[ListingLog]:
        """查询上架日志详情"""
        result = await db.execute(select(ListingLog).where(ListingLog.id == log_id))
        return result.scalar_one_or_none()

    async def test_platform_connection(self, db: AsyncSession, platform_id: int) -> Dict[str, Any]:
        """测试平台连接"""
        result = await db.execute(select(PlatformConfig).where(PlatformConfig.id == platform_id))
        platform = result.scalar_one_or_none()
        if not platform:
            return {"success": False, "message": "平台配置不存在"}

        try:
            adapter = get_adapter(platform)
            success, message = await adapter.test_connection()
            return {"success": success, "message": message}
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            return {"success": False, "message": f"连接测试异常: {str(e)}"}


# 全局单例
listing_service = ListingService()
