"""Pydantic 请求/响应模型"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer


# ========== 商品相关 ==========

class ProductCreate(BaseModel):
    quick_model: str = Field(..., alias="quick_model")
    product_model: str = Field(..., alias="product_model")
    product_name: str = ""
    brand: str = ""
    category_level1: str = ""
    category_level2: str = ""
    category_level3: str = ""
    negotiation_price: Optional[float] = Field(default=0, alias="negotiation_price")
    price_update: str = ""
    last_purchase_price: Optional[float] = Field(default=0, alias="last_purchase_price")
    purchase_price: Optional[float] = Field(default=0, alias="purchase_price")
    retail_price: Optional[float] = Field(default=0, alias="retail_price")
    new_event_price: Optional[float] = Field(default=0, alias="new_event_price")
    shop_url: str = ""
    bid_price: Optional[float] = Field(default=0, alias="bid_price")
    group_purchase_price: Optional[float] = Field(default=0, alias="group_purchase_price")
    price: float = 0
    gross_weight: Optional[float] = Field(default=0, alias="gross_weight")
    box_spec: str = ""
    cooperation_level: str = ""
    supply_status: str = ""
    specification: str = ""
    remark: str = ""
    shipping_fee: Optional[float] = Field(default=0, alias="shipping_fee")
    barcode_69: str = Field(default="", alias="barcode_69")
    sales_volume: int = 0
    recommendation: str = ""
    parameters: str = ""
    cert_3c: str = ""
    image: str = ""

    class Config:
        populate_by_name = True


class ProductUpdate(BaseModel):
    quick_model: Optional[str] = None
    product_model: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category_level1: Optional[str] = None
    category_level2: Optional[str] = None
    category_level3: Optional[str] = None
    negotiation_price: Optional[float] = Field(default=None, alias="negotiation_price")
    price_update: Optional[str] = None
    last_purchase_price: Optional[float] = Field(default=None, alias="last_purchase_price")
    purchase_price: Optional[float] = Field(default=None, alias="purchase_price")
    retail_price: Optional[float] = Field(default=None, alias="retail_price")
    new_event_price: Optional[float] = Field(default=None, alias="new_event_price")
    shop_url: Optional[str] = None
    bid_price: Optional[float] = Field(default=None, alias="bid_price")
    group_purchase_price: Optional[float] = Field(default=None, alias="group_purchase_price")
    price: Optional[float] = None
    gross_weight: Optional[float] = Field(default=None, alias="gross_weight")
    box_spec: Optional[str] = None
    cooperation_level: Optional[str] = None
    supply_status: Optional[str] = None
    specification: Optional[str] = None
    remark: Optional[str] = None
    shipping_fee: Optional[float] = Field(default=None, alias="shipping_fee")
    barcode_69: Optional[str] = Field(default=None, alias="barcode_69")
    sales_volume: Optional[float] = None
    recommendation: Optional[str] = None
    parameters: Optional[str] = None
    cert_3c: Optional[str] = None
    image: Optional[str] = None

    class Config:
        populate_by_name = True


class ProductResponse(BaseModel):
    id: int
    quick_model: str = ""
    product_model: str = ""
    product_name: Optional[str] = ""
    brand: Optional[str] = ""
    category_level1: Optional[str] = ""
    category_level2: Optional[str] = ""
    category_level3: Optional[str] = ""
    negotiation_price: Optional[float] = None
    price_update: Optional[str] = ""
    last_purchase_price: Optional[float] = None
    purchase_price: Optional[float] = None
    retail_price: Optional[float] = None
    discount_rate: float = 0.0
    new_event_price: Optional[float] = None
    shop_url: Optional[str] = ""
    bid_price: Optional[float] = None
    group_purchase_price: Optional[float] = None
    price: float
    gross_weight: Optional[float] = None
    box_spec: Optional[str] = ""
    cooperation_level: Optional[str] = ""
    supply_status: Optional[str] = ""
    specification: Optional[str] = ""
    remark: Optional[str] = ""
    shipping_fee: Optional[float] = None
    barcode_69: str
    sales_volume: Optional[float] = 0
    recommendation: Optional[str] = ""
    parameters: Optional[str] = ""
    cert_3c: Optional[str] = ""
    image: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat()


class PaginatedResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int


class BatchDeleteRequest(BaseModel):
    ids: List[int]


# ========== 导入相关 ==========

class UploadResponse(BaseModel):
    file_id: str
    file_name: str
    columns: List[str]
    preview_rows: List[List[Any]]
    total_rows: int
    suggested_mapping: dict


class ConfirmImportRequest(BaseModel):
    file_id: str
    column_mapping: dict
    duplicate_strategy: str = "skip"  # skip / overwrite / error


class ImportResultResponse(BaseModel):
    total_rows: int
    success_rows: int
    skip_rows: int
    error_rows: int
    errors: List[dict] = []


# ========== 智能查询相关 ==========

class SmartQueryRequest(BaseModel):
    query_text: str


class ParsedQuery(BaseModel):
    type: str
    value: Optional[str] = None
    results: List[ProductResponse] = []
    count: int = 0
    message: str = ""


class SmartQueryResponse(BaseModel):
    query_intent: str


# ========== 批量快查型号查询 ==========

class BatchModelQueryRequest(BaseModel):
    """批量快查型号查询请求"""
    queries: List[str]
    fuzzy: bool = True  # 是否模糊匹配


class BatchModelQueryItem(BaseModel):
    query: str
    results: List[ProductResponse] = []
    count: int = 0
    message: str = ""


class BatchModelQueryResponse(BaseModel):
    total_queries: int
    total_results: int
    items: List[BatchModelQueryItem]
    parsed_params: dict = {}
    parsed_queries: List[ParsedQuery] = []
    results: List[ProductResponse] = []
    result_count: int = 0
    message: str = ""
    unrecognized_text: str = ""


# ========== 平台配置相关 ==========

class PlatformConfigCreate(BaseModel):
    name: str
    platform_type: str
    api_base_url: str = ""
    api_key: str = ""
    api_secret: str = ""
    shop_id: str = ""
    extra_config: dict = {}
    is_active: bool = True


class PlatformConfigUpdate(BaseModel):
    name: Optional[str] = None
    platform_type: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    shop_id: Optional[str] = None
    extra_config: Optional[dict] = None
    is_active: Optional[bool] = None


class PlatformConfigResponse(BaseModel):
    id: int
    name: str
    platform_type: str
    api_base_url: str
    api_key: str
    api_secret: str
    shop_id: str
    extra_config: dict = {}
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat() + 'Z'


# ========== 一键上架相关 ==========

class ListingSubmitRequest(BaseModel):
    product_ids: List[int]
    platform_ids: List[int]


class ListingResultItem(BaseModel):
    product_id: int
    platform_id: int
    status: str
    platform_product_id: str = ""
    error_message: str = ""


class ListingSubmitResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[ListingResultItem] = []


class ListingLogQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    status: Optional[str] = None
    platform_id: Optional[int] = None
    product_id: Optional[int] = None


class ListingLogResponse(BaseModel):
    id: int
    product_id: int
    product_model: str = ""
    product_name: str = ""
    platform_id: int
    platform_name: str = ""
    status: str
    platform_product_id: str = ""
    error_message: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat() + 'Z'


class ListingLogDetailResponse(ListingLogResponse):
    request_data: dict = {}
    response_data: dict = {}


# ========== 通用响应包装 ==========

class ApiResponse(BaseModel):
    code: int = 200
    data: Any = None
    message: str = "success"
