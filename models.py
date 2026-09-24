from sqlalchemy import create_engine, Column, Float, String, Integer, Date, ForeignKey, Time
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

engine = create_engine("sqlite:///products.db", echo=True)

Base = declarative_base()


class Product(Base):
    __tablename__ = "productos"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    cart_products = relationship("Cart_Product", back_populates = "product")

class Sale(Base):
    __tablename__ = "ventas"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    date = Column(Date, default=datetime.now, nullable=False)
    time = Column(Time, default=datetime.now, nullable=False)
    id_cart = Column(Integer, ForeignKey("carritos.id"), nullable=False, unique=True)
    cart = relationship("Cart", back_populates = "sale", uselist=False)

class Cart(Base):
    __tablename__ = "carritos"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    created_at = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    sale = relationship("Sale", back_populates = "cart", uselist=False)
    cart_products = relationship("Cart_Product", back_populates = "cart")


class Cart_Product(Base):
    __tablename__ = "carrito_producto"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    id_cart = Column(Integer, ForeignKey("carritos.id"), nullable=False)
    id_product = Column(Integer, ForeignKey("productos.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    product = relationship("Product", back_populates = "cart_products")
    cart = relationship("Cart", back_populates = "cart_products")



Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)