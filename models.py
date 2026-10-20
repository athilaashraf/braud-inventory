from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

SIZES = ["S", "M", "L", "XL"]


class Product(db.Model):
    """One shirt model, e.g. White, Black, Checks, Denim"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    low_stock_limit = db.Column(db.Integer, default=10)  # warn below this
    variants = db.relationship("Variant", backref="product", cascade="all, delete")


class Variant(db.Model):
    """Stock count for one size of one product"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    size = db.Column(db.String(3), nullable=False)
    quantity = db.Column(db.Integer, default=0)


class StockEntry(db.Model):
    """History of every delivery"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    pieces = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    product = db.relationship("Product")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(20), unique=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.now)
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(10), default="Active")
    cancel_reason = db.Column(db.String(200))
    discount = db.Column(db.Float, default=0)
    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete")


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    size = db.Column(db.String(3), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    product = db.relationship("Product")

class StockAdjustment(db.Model):
    """History of manual stock corrections"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    size = db.Column(db.String(3), nullable=False)
    old_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    product = db.relationship("Product")