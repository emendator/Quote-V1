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


# ========== 批量快查型号查询 ==========

class BatchModelQueryRequest(BaseModel):
    """批量快查型号查询请求"""
    queries: List[str]
    fuzzy: bool = True  # 是否模糊匹配


class QueryExportRequest(BaseModel):
    """查询结果导出请求"""
    product_ids: List[int]


# ========== 智能方案相关（v2.0 组合方案）==========

class SolutionSlotInput(BaseModel):
    """结构化方案输入：一个商品信息块"""
    category: str = ""                   # 三级品类（必填，用户从三级品类列表选择）
    quantity: int = 1                    # 数量
    price_op: str = ""                   # 价格限制方式：gt(大于) / lt(小于) / around(左右)
    price: Optional[float] = None        # 价格限制值
    discount_op: str = ""                # 折扣率限制方式：gt(大于) / lt(小于) / around(左右)
    discount: Optional[float] = None     # 折扣率限制值（百分比）
    price_min: Optional[float] = None    # 价格下限（兼容）
    price_max: Optional[float] = None    # 价格上限（兼容）


class SolutionAnalyzeRequest(BaseModel):
    requirement: str = ""
    use_ai: bool = False
    max_solutions: int = 50
    # 结构化输入（多块输入）：总价 + 总折扣率 + 商品信息块列表
    total_price: Optional[float] = None
    total_price_op: str = ""                 # 总价限制方式：gt(大于) / lt(小于) / around(左右)
    max_discount_rate: Optional[float] = None   # 总折扣率限制值（可选）
    max_discount_op: str = ""                 # 总折扣率限制方式：gt(大于) / lt(小于) / around(左右)
    slots: List[SolutionSlotInput] = []


class SolutionSlotItem(BaseModel):
    """组合方案中的单个商品"""
    product_id: int
    quick_model: str = ""
    product_model: str = ""
    product_name: str = ""
    brand: str = ""
    category_level1: str = ""
    category_level2: str = ""
    specification: str = ""
    price: float = 0
    retail_price: float = 0
    discount_rate: float = 0
    quantity: int = 1
    subtotal: float = 0


class SolutionCombination(BaseModel):
    """一个完整的组合方案"""
    total_price: float = 0
    total_quantity: int = 0
    total_discount_rate: float = 0
    items: List[SolutionSlotItem] = []


class SolutionAnalyzeResult(BaseModel):
    """组合方案分析结果"""
    parsed_constraints: dict = {}
    ai_interpretation: str = ""
    solutions: List[SolutionCombination] = []
    total_solutions: int = 0
    message: str = ""


class SolutionCandidate(BaseModel):
    """兼容旧版（保留，方案购物车仍使用）"""
    id: int
    quick_model: str = ""
    product_model: str = ""
    product_name: str = ""
    brand: str = ""
    category_level1: str = ""
    category_level2: str = ""
    specification: str = ""
    price: float = 0
    supply_status: str = ""
    is_recommended: bool = False
    source_company_name: str = ""
    source_role: str = ""


class SolutionItemData(BaseModel):
    product_id: int
    quantity: int = 1


class SolutionSaveRequest(BaseModel):
    name: str = ""
    requirement: str = ""
    remark: str = ""
    ai_enabled: bool = False
    items: list = []


class SolutionExportRequest(BaseModel):
    plan_id: int


class SolutionRecommendedRequest(BaseModel):
    """推荐方案请求"""
    requirement: str = Field(..., description="产品组合需求")
    max_solutions: int = Field(default=50, ge=1, le=500)


# ========== 用户认证相关 ==========

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=6, max_length=32)
    email: str = Field(..., max_length=200)
    invite_code: str = Field(...)


class LoginRequest(BaseModel):
    username: str = Field(...)
    password: str = Field(...)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    company_id: Optional[int] = None
    company_name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    company_address: str = ""
    is_active: bool = True
    has_api_key: bool = False
    total_tokens_used: int = 0
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CompanyInfoUpdate(BaseModel):
    """更新公司联系方式（已绑定公司后使用，公司名称不可修改）"""
    contact_person: Optional[str] = ""
    contact_phone: Optional[str] = ""
    company_address: Optional[str] = ""


class CompanyBindRequest(BaseModel):
    """绑定公司（数据隔离：公司名 + 公司数据库密码）

    mode: join=加入已有公司（所有角色）；create=新注册公司（仅管理员/最高级管理员）
    """
    mode: str = Field(..., pattern=r'^(join|create)$', description="join/create")
    company_name: str = Field(..., min_length=1, max_length=200)
    company_password: str = Field(..., min_length=6, max_length=64)
    contact_person: str = ""
    contact_phone: str = ""
    company_address: str = ""


class CompanyPasswordChangeRequest(BaseModel):
    """修改公司数据库密码（需提供该公司当前密码；最高级管理员可指定公司名改任意公司）"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=64)
    company_name: str = ""  # 最高级管理员可指定要修改的公司（留空=自己所在公司）；普通管理员只能改自己所在公司


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(...)
    new_password: str = Field(..., min_length=6, max_length=32)


# ========== 邀请码相关 ==========

class InviteCodeCreateRequest(BaseModel):
    code_type: str = Field(..., pattern=r'^(admin|user)$')
    expires_at: str = Field(..., description="过期时间，格式: YYYY-MM-DD HH:mm")
    company_name: str = Field("", max_length=200, description="（已弃用）邀请码仅决定角色，不再预设公司名，此字段仅作备注")


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    type: str
    created_by: int
    used_by: Optional[int] = None
    used_by_username: str = ""        # 使用者的用户名
    used_by_company: str = ""         # 使用者公司名称
    used_by_last_login: Optional[str] = None  # 使用者最后登录时间
    used_at: Optional[str] = None
    expires_at: str
    is_used: bool
    company_name: str = ""            # 邀请码预设的公司名称
    created_at: str

    class Config:
        from_attributes = True


class InviteCodeVerifyResponse(BaseModel):
    valid: bool
    type: Optional[str] = None
    message: str = ""
    company_name: str = ""


class InviteCodeRenewRequest(BaseModel):
    """续期请求"""
    expires_at: str = Field(..., description="新的过期时间，格式: YYYY-MM-DD HH:mm")


# ========== 推荐产品相关 ==========

class RecommendedProductRequest(BaseModel):
    filters: dict = {}
    page: int = 1
    page_size: int = 20


class RecommendedProduct(BaseModel):
    id: int
    owner_id: Optional[int] = 0
    quick_model: str = ""
    product_model: str = ""
    product_name: str = ""
    brand: str = ""
    category_level1: str = ""
    category_level2: str = ""
    category_level3: str = ""
    price: float = 0
    specification: str = ""
    supply_status: str = ""
    image: str = ""
    # 推荐产品特有字段
    source_company_name: str = ""  # 来源公司名称
    source_role: str = ""          # 来源角色: super_admin/admin


# ========== 列显示配置相关 ==========

class ColumnConfigItem(BaseModel):
    """单列配置"""
    key: str
    label: str = ""
    visible: bool = True
    width: int = 120
    fixed: Optional[str] = None  # 'left' | 'right' | None


class ColumnDisplayConfigResponse(BaseModel):
    """列显示配置响应"""
    page_type: str
    columns: List[ColumnConfigItem] = []


class ColumnDisplayUpdateRequest(BaseModel):
    """更新列显示配置请求"""
    columns: List[ColumnConfigItem]


class AvailableColumn(BaseModel):
    """可用列信息"""
    key: str
    default_label: str
    default_width: int = 120


# ========== 通用响应包装 ==========

class ApiResponse(BaseModel):
    code: int = 200
    data: Any = None
    message: str = "success"
