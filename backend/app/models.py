"""SQLAlchemy 数据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.database import Base


class Product(Base):
    """商品主表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID(自增)")
    brand = Column(String(200), default="", index=True, comment="品牌")
    product_image = Column(String(500), default="", comment="商品图片URL")
    category = Column(String(200), default="", index=True, comment="类别")
    product_model = Column(String(500), default="", index=True, comment="商品型号")
    specification = Column(String(500), default="", index=True, comment="规格")
    jd_price = Column(Float, nullable=True, default=0, comment="京东划线价(元)")
    cost_price = Column(Float, nullable=True, default=0, comment="成本价(元)")
    price = Column(Float, nullable=False, default=0, index=True, comment="代发价/报价(元)")
    barcode_69 = Column(String(20), default="", index=True, comment="69码")
    supplier = Column(String(200), default="", comment="供应商")
    shop_url = Column(String(500), default="", comment="店铺链接")
    stock = Column(Integer, default=0, comment="库存")
    remark = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    @property
    def discount_rate(self) -> float:
        """折扣率 = 代发价 / 京东划线价 (自动计算)"""
        if self.jd_price and self.jd_price > 0:
            return round(self.price / self.jd_price * 100, 2)
        return 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "product_image": self.product_image,
            "category": self.category,
            "product_model": self.product_model,
            "specification": self.specification,
            "jd_price": self.jd_price,
            "cost_price": self.cost_price,
            "price": self.price,
            "barcode_69": self.barcode_69,
            "supplier": self.supplier,
            "shop_url": self.shop_url,
            "discount_rate": self.discount_rate,
            "stock": self.stock,
            "remark": self.remark,
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
