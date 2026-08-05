"""SQLAlchemy 数据模型"""
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.database import Base


# 北京时间 (UTC+8)
def beijing_now():
    return datetime.now(timezone(timedelta(hours=8)))


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(512), nullable=False, comment="用户名(加密存储)")
    username_hash = Column(String(64), unique=True, index=True, nullable=False, default="", comment="用户名HMAC(用于唯一校验与查询)")
    password_hash = Column(String(256), nullable=False, comment="密码哈希(bcrypt)")
    email = Column(String(200), nullable=False, comment="邮箱")
    role = Column(String(20), nullable=False, default="user", comment="角色: super_admin/admin/user")
    company_name = Column(String(200), default="", comment="公司名称")
    company_id = Column(Integer, nullable=True, default=None, index=True, comment="所属公司ID(数据隔离)")
    contact_person = Column(String(100), default="", comment="联系人")
    contact_phone = Column(String(50), default="", comment="联系电话")
    company_address = Column(String(500), default="", comment="公司地址")
    is_active = Column(Integer, default=1, comment="是否启用(1是/0否)")
    api_key = Column(String(500), default="", comment="DeepSeek API Key（加密存储）")
    total_tokens_used = Column(Integer, default=0, comment="累计消耗的 token 总数")
    expires_at = Column(DateTime, nullable=True, default=None, comment="账号过期时间(过期后禁止操作，仅可删除)")
    last_login_at = Column(DateTime, nullable=True, default=None, comment="最后登录时间")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now, comment="更新时间(北京时间)")

    def get_plain_username(self) -> str:
        """解密返回明文用户名（数据库中以密文存储）"""
        from app.utils.crypto_utils import decrypt_username
        username_value: str = self.username  # type: ignore[assignment]
        return decrypt_username(username_value)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.get_plain_username(),
            "email": self.email,
            "role": self.role,
            "company_id": self.company_id,
            "company_name": self.company_name or "",
            "contact_person": self.contact_person or "",
            "contact_phone": self.contact_phone or "",
            "company_address": self.company_address or "",
            "is_active": bool(self.is_active),
            "has_api_key": bool(self.api_key),
            "total_tokens_used": self.total_tokens_used or 0,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Company(Base):
    """公司表：公司名(唯一) + 公司数据库密码"""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="公司ID")
    company_name = Column(String(200), unique=True, nullable=False, index=True, comment="公司名称(唯一，创建后不可修改)")
    password_hash = Column(String(256), nullable=False, comment="公司数据库密码哈希(bcrypt)")
    created_by = Column(Integer, nullable=True, default=0, comment="创建者用户ID(管理员)")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now, comment="更新时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InviteCode(Base):
    """邀请码表"""
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="邀请码")
    type = Column(String(20), nullable=False, comment="类型: admin/user")
    created_by = Column(Integer, nullable=False, comment="创建者用户ID")
    used_by = Column(Integer, nullable=True, default=None, comment="使用者用户ID")
    used_at = Column(DateTime, nullable=True, default=None, comment="使用时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    is_used = Column(Integer, default=0, comment="是否已使用(0否/1是)")
    company_name = Column(String(200), default="", comment="备注（邀请码仅决定角色，不再预设公司名）")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "type": self.type,
            "created_by": self.created_by,
            "used_by": self.used_by,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_used": bool(self.is_used),
            "company_name": self.company_name or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Product(Base):
    """商品主表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    company_name = Column(String(200), nullable=False, default="", index=True, comment="所属公司名称(数据隔离)")
    company_id = Column(Integer, nullable=True, default=0, index=True, comment="所属公司ID(数据隔离)")
    owner_id = Column(Integer, nullable=True, default=0, index=True, comment="所属用户ID(兼容保留)")
    quick_model = Column(String(500), nullable=False, default="", index=True, comment="快查型号(必填)")
    product_model = Column(String(500), nullable=True, default="", index=True, comment="型号")
    product_name = Column(String(500), default="", comment="产品名称")
    brand = Column(String(200), default="", index=True, comment="品牌")
    category_level1 = Column(String(200), default="", index=True, comment="一级品类")
    category_level2 = Column(String(200), default="", index=True, comment="二级品类")
    category_level3 = Column(String(200), default="", index=True, comment="三级品类")
    negotiation_price = Column(Float, nullable=True, default=0, comment="备货商谈价(元)")
    price_update = Column(String(200), default="", comment="报价更新")
    last_purchase_price = Column(Float, nullable=True, default=0, comment="上次进货价(元)")
    purchase_price = Column(Float, nullable=True, default=0, comment="进货价(元)")
    retail_price = Column(Float, nullable=True, default=0, comment="零售价(元)")
    @property
    def discount_rate(self) -> float:
        """折扣率 = 集采价 / 新活动价 × 100% (自动计算)"""
        if self.new_event_price and self.new_event_price > 0:
            return round(self.group_purchase_price / self.new_event_price * 100, 2) if self.group_purchase_price else 0.0
        return 0.0
    new_event_price = Column(Float, nullable=True, default=0, comment="新活动价(元)")
    shop_url = Column(String(500), default="", comment="链接")
    bid_price = Column(Float, nullable=True, default=0, comment="投标价(元)")
    group_purchase_price = Column(Float, nullable=True, default=0, comment="集采价/项目(元)")
    price = Column(Float, nullable=False, default=0, index=True, comment="代发价(元)")
    gross_weight = Column(Float, nullable=True, default=0, comment="毛重(kg)")
    box_spec = Column(String(200), default="", comment="箱规")
    cooperation_level = Column(String(100), default="", comment="合作等级")
    supply_status = Column(String(100), default="", comment="供货状态")
    specification = Column(String(500), default="", index=True, comment="规格")
    remark = Column(Text, default="", comment="备注")
    shipping_fee = Column(Float, nullable=True, default=0, comment="代发运费(元)")
    barcode_69 = Column(String(20), nullable=True, default="", index=True, comment="69码")
    sales_volume = Column(Integer, default=0, comment="销量")
    recommendation = Column(Text, default="", comment="推荐理由")
    parameters = Column(Text, default="", comment="参数")
    cert_3c = Column(String(200), default="", comment="3C")
    image = Column(Text, default="", comment="产品图片(Base64编码)")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now, comment="更新时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name or "",
            "owner_id": self.owner_id,
            "quick_model": self.quick_model,
            "product_model": self.product_model,
            "product_name": self.product_name,
            "brand": self.brand,
            "category_level1": self.category_level1,
            "category_level2": self.category_level2,
            "category_level3": self.category_level3,
            "negotiation_price": self.negotiation_price,
            "price_update": self.price_update,
            "last_purchase_price": self.last_purchase_price,
            "purchase_price": self.purchase_price,
            "retail_price": self.retail_price,
            "discount_rate": self.discount_rate,
            "new_event_price": self.new_event_price,
            "shop_url": self.shop_url,
            "bid_price": self.bid_price,
            "group_purchase_price": self.group_purchase_price,
            "price": self.price,
            "gross_weight": self.gross_weight,
            "box_spec": self.box_spec,
            "cooperation_level": self.cooperation_level,
            "supply_status": self.supply_status,
            "specification": self.specification,
            "remark": self.remark,
            "shipping_fee": self.shipping_fee,
            "barcode_69": self.barcode_69,
            "sales_volume": self.sales_volume,
            "recommendation": self.recommendation,
            "parameters": self.parameters,
            "cert_3c": self.cert_3c,
            "image": self.image or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ColumnDisplayConfig(Base):
    """列显示配置表（v2.0 新增）"""
    __tablename__ = "column_display_configs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    user_id = Column(Integer, nullable=False, comment="用户ID")
    page_type = Column(String(50), nullable=False, comment="页面类型: product_db / query_result / batch_query")
    config_json = Column(Text, nullable=False, default="[]", comment="列配置JSON")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now, comment="更新时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "page_type": self.page_type,
            "columns": json.loads(self.config_json) if self.config_json else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ImportTemplate(Base):
    """导入列映射模板"""
    __tablename__ = "import_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="模板名称")
    mapping_json = Column(Text, nullable=False, comment="列映射JSON")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class ImportLog(Base):
    """导入日志"""
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(500), nullable=False, comment="导入文件名")
    total_rows = Column(Integer, default=0, comment="总行数")
    success_rows = Column(Integer, default=0, comment="成功行数")
    skip_rows = Column(Integer, default=0, comment="跳过行数")
    error_rows = Column(Integer, default=0, comment="失败行数")
    error_detail = Column(Text, default="", comment="错误详情JSON")
    owner_id = Column(Integer, nullable=True, default=0, comment="所属用户ID")
    company_id = Column(Integer, nullable=True, default=0, index=True, comment="所属公司ID(数据隔离)")
    company_name = Column(String(200), default="", comment="所属公司名称")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")





class SolutionPlan(Base):
    """智能方案主表"""
    __tablename__ = "solution_plans"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    company_name = Column(String(200), nullable=False, default="", index=True, comment="所属公司名称(数据隔离)")
    company_id = Column(Integer, nullable=True, default=0, index=True, comment="所属公司ID(数据隔离)")
    owner_id = Column(Integer, nullable=False, default=0, index=True, comment="所属用户ID")
    name = Column(String(200), default="", comment="方案名称")
    requirement = Column(Text, default="", comment="客户原始需求文本")
    ai_enabled = Column(Integer, default=0, comment="是否使用 AI 分析(1是/0否)")
    total_amount = Column(Float, nullable=True, default=0, comment="方案总金额(元)")
    status = Column(String(20), default="draft", comment="状态: draft/finalized")
    remark = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now, comment="更新时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "requirement": self.requirement,
            "ai_enabled": bool(self.ai_enabled),
            "total_amount": self.total_amount,
            "status": self.status,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SolutionItem(Base):
    """方案明细表"""
    __tablename__ = "solution_items"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    plan_id = Column(Integer, nullable=False, index=True, comment="方案ID")
    product_id = Column(Integer, nullable=False, comment="商品ID")
    quick_model = Column(String(500), default="", comment="快查型号(冗余)")
    product_model = Column(String(500), default="", comment="商品型号(冗余)")
    product_name = Column(String(500), default="", comment="商品名称(冗余)")
    brand = Column(String(200), default="", comment="品牌(冗余)")
    category_level1 = Column(String(200), default="", comment="一级品类(冗余)")
    category_level2 = Column(String(200), default="", comment="二级品类(冗余)")
    specification = Column(String(500), default="", comment="规格(冗余)")
    price = Column(Float, default=0, comment="代发价(冗余)")
    retail_price = Column(Float, nullable=True, default=0, comment="零售价(冗余)")
    image = Column(Text, default="", comment="产品图片Base64(冗余)")
    quantity = Column(Integer, default=1, comment="数量")
    subtotal = Column(Float, nullable=True, default=0, comment="小计 = price × quantity")
    remark = Column(Text, default="", comment="行备注")
    created_at = Column(DateTime, default=beijing_now, comment="创建时间(北京时间)")

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "product_id": self.product_id,
            "quick_model": self.quick_model,
            "product_model": self.product_model,
            "product_name": self.product_name,
            "brand": self.brand,
            "category_level1": self.category_level1,
            "category_level2": self.category_level2,
            "specification": self.specification,
            "price": self.price,
            "retail_price": self.retail_price,
            "image": self.image,
            "quantity": self.quantity,
            "subtotal": self.subtotal,
            "remark": self.remark,
        }
