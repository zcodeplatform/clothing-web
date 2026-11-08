from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price_nonnegative"),
        CheckConstraint(
            "compare_at IS NULL OR compare_at > price",
            name="ck_product_compare_at_greater_than_price",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_at = db.Column(db.Numeric(10, 2))
    description = db.Column(db.Text, nullable=False, default="")
    details = db.Column(db.JSON, nullable=False, default=list)
    is_new = db.Column(db.Boolean, nullable=False, default=False)

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
        lazy="selectin",
    )
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.id",
        lazy="selectin",
    )

    @property
    def image(self):
        return self.images[0].path if self.images else ""

    @property
    def colors(self):
        return list(dict.fromkeys(variant.color for variant in self.variants))

    @property
    def sizes(self):
        return list(dict.fromkeys(variant.size for variant in self.variants))

    @property
    def default_variant(self):
        return next((variant for variant in self.variants if variant.stock > 0),
                    self.variants[0] if self.variants else None)

    def variant_for(self, color, size):
        return next(
            (variant for variant in self.variants
             if variant.color == color and variant.size == size),
            None,
        )

    def stock_for(self, color, size):
        variant = self.variant_for(color, size)
        return variant.stock if variant else 0

    def stocks_for(self, color):
        return {size: self.stock_for(color, size) for size in self.sizes}


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    path = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255), nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="images")


class ProductVariant(db.Model):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "color", "size", name="uq_product_variant"),
        CheckConstraint("stock >= 0", name="ck_product_variant_stock_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    color = db.Column(db.String(80), nullable=False)
    size = db.Column(db.String(40), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="variants")
