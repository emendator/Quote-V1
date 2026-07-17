"""SQLAlchemy 数据模型"""
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.database import Base


# 北京时间 (UTC+8)
def beijing_now():
    return datetime.now(timezone(timedelta(hours=8)))


class Product(Base):
    """商品主表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    quick_model = Column(String(500), nullable=False, default="", index=True, comment="快查型号(必填)")
    product_model = Column(String(500), nullable=False, default="", index=True, comment="型号(必填)")
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
        """折扣率 = 代发价 / 零售价 × 100% (自动计算)"""
        if self.retail_price and self.retail_price > 0:
            return round(self.price / self.retail_price * 100, 2)
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
    barcode_69 = Column(String(20), nullable=False, default="", index=True, comment="69码")
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
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class PlatformConfig(Base):
    """平台配置"""
    __tablename__ = "platform_configs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    name = Column(String(200), nullable=False, comment="平台名称")
    platform_type = Column(String(50), nullable=False, comment="平台类型(taobao/jd/pdd/...)")
    api_base_url = Column(String(500), nullable=False, default="", comment="API基础地址")
    api_key = Column(String(500), default="", comment="API密钥")
    api_secret = Column(String(500), default="", comment="API密钥Secret")
    shop_id = Column(String(200), default="", comment="店铺ID")
    extra_config = Column(Text, default="{}", comment="额外配置JSON")
    is_active = Column(Integer, default=1, comment="是否启用(1是/0否)")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "platform_type": self.platform_type,
            "api_base_url": self.api_base_url,
            "api_key": "******" if self.api_key else "",
            "api_secret": "******" if self.api_secret else "",
            "shop_id": self.shop_id,
            "extra_config": json.loads(self.extra_config) if self.extra_config else {},
            "is_active": bool(self.is_active),
            "created_at": (self.created_at.isoformat() + 'Z') if self.created_at else None,
            "updated_at": (self.updated_at.isoformat() + 'Z') if self.updated_at else None,
        }


class ListingLog(Base):
    """上架日志"""
    __tablename__ = "listing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号(自增)")
    product_id = Column(Integer, nullable=False, comment="商品ID")
    product_model = Column(String(500), default="", comment="商品型号(冗余)")
    product_name = Column(String(500), default="", comment="商品名称(冗余)")
    platform_id = Column(Integer, nullable=False, comment="平台配置ID")
    platform_name = Column(String(200), default="", comment="平台名称(冗余)")
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/success/failed")
    platform_product_id = Column(String(200), default="", comment="平台商品ID")
    request_data = Column(Text, default="{}", comment="请求数据JSON")
    response_data = Column(Text, default="{}", comment="响应数据JSON")
    error_message = Column(Text, default="", comment="错误信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_model": self.product_model,
            "product_name": self.product_name,
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "status": self.status,
            "platform_product_id": self.platform_product_id,
            "error_message": self.error_message,
            "created_at": (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }
