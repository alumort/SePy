from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Float,
    String,
    Integer,
    Date,
    ForeignKey,
    Time,
    UniqueConstraint,
    CheckConstraint,
    event,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


engine = create_engine(
    "sqlite:///products.db",
    echo=False,
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    cart_products = relationship(
        "Cart_Product",
        back_populates="product",
    )


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    sales = relationship(
        "Sale",
        back_populates="client",
    )


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(Date, nullable=False)
    status = Column(String, nullable=False)

    sale = relationship(
        "Sale",
        back_populates="cart",
        uselist=False,
    )

    cart_products = relationship(
        "Cart_Product",
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(
        Date,
        default=lambda: datetime.now().date(),
        nullable=False,
    )
    time = Column(
        Time,
        default=lambda: datetime.now().time().replace(microsecond=0),
        nullable=False,
    )
    id_cart = Column(
        Integer,
        ForeignKey("carts.id"),
        nullable=True,
        unique=True,
    )

    cart = relationship(
        "Cart",
        back_populates="sale",
        uselist=False,
    )
    
    id_client = Column(
    Integer,
    ForeignKey("clients.id"),
    nullable=True,
    )

    client = relationship(
    "Client",
    back_populates="sales",
    )



class Cart_Product(Base):
    __tablename__ = "cart_product"
    __table_args__ = (
        UniqueConstraint(
            "id_cart",
            "id_product",
            name="uq_cart_product",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_cart_product_quantity_positive",
        ),
        {"sqlite_autoincrement": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cart = Column(
        Integer,
        ForeignKey("carts.id"),
        nullable=False,
    )
    id_product = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )
    quantity = Column(Integer, nullable=False)

    product = relationship(
        "Product",
        back_populates="cart_products",
    )

    cart = relationship(
        "Cart",
        back_populates="cart_products",
    )


Base.metadata.create_all(engine)

Session = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
