"""Pydantic 请求/响应模型"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer


# ========== 商品相关 ==========

class ProductCreate(BaseModel):
    brand: str = ""
    product_image: str = ""
    category: str = ""
    product_model: str = ""
    specification: str = ""
    jd_price: Optional[float] = Field(default=0, alias="jd_price")
    cost_price: Optional[float] = Field(default=0, alias="cost_price")
    price: float = 0
    barcode_69: str = Field(default="", alias="barcode_69")
    supplier: str = ""
    shop_url: str = ""
    stock: int = 0
    remark: str = ""

    class Config:
        populate_by_name = True


class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    product_image: Optional[str] = None
    category: Optional[str] = None
    product_model: Optional[str] = None
    specification: Optional[str] = None
    jd_price: Optional[float] = Field(default=None, alias="jd_price")
    cost_price: Optional[float] = Field(default=None, alias="cost_price")
    price: Optional[float] = None
    barcode_69: Optional[str] = Field(default=None, alias="barcode_69")
    supplier: Optional[str] = None
    shop_url: Optional[str] = None
    stock: Optional[int] = None
    remark: Optional[str] = None

    class Config:
        populate_by_name = True


class ProductResponse(BaseModel):
    id: int
    brand: str
    product_image: str
    category: str
    product_model: str
    specification: str
    jd_price: Optional[float] = None
    cost_price: Optional[float] = None
    price: float
    barcode_69: str
    supplier: str
    shop_url: str
    discount_rate: float = 0.0
    stock: int
    remark: str
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
    parsed_params: dict = {}
    parsed_queries: List[ParsedQuery] = []
    results: List[ProductResponse] = []
    result_count: int = 0
    message: str = ""
    unrecognized_text: str = ""


# ========== 通用响应包装 ==========

class ApiResponse(BaseModel):
    code: int = 200
    data: Any = None
    message: str = "success"
