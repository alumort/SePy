from sqlalchemy import create_engine, Column, Float, String, Integer, Date
from sqlalchemy.orm import declarative_base, sessionmaker


engine = create_engine("sqlite:///products.db", echo=True)

Base = declarative_base()


class Product(Base):
    __tablename__ = "productos"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)

class Cart(Base):
    __tablename__ = "carritos"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    created_at = Column(Date, default=Date.now)
    status = Column(String, nullable=False)

class Cart_Product(Base):
    __tablename__ = "carrito_producto"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    id_cart = Column(Integer, foreign_key = Cart, nullable=False)
    id_product = Column(Integer, foreign_key = Product, nullable=False)
    quantity = Column(Integer, nullable=False)



Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)