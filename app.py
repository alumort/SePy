import datetime
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models import Cart, Cart_Product, Client, Product, Sale
from models import Session as SessionLocal

app = FastAPI(title="API de ventas")

# ---------------------------------------------------------------------------
# Schemas 
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price: float | None = Field(default=None, gt=0)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CartCreate(BaseModel):
    created_at: datetime.date
    status: Literal["open", "closed"] = "open"


class CartUpdate(BaseModel):
    created_at: datetime.date | None = None
    status: Literal["open", "closed"] | None = None


class CartProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    quantity: int = Field(gt=0)


class SaleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    time: datetime.time
    cart_id: int
    client_id: int


class SaleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date | None = None
    time: datetime.time | None = None


class SaleCartAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_id: int | None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sales_query(db):
    """Query de ventas que carga carrito, productos y cliente de una vez
    (evita hacer una consulta extra por cada venta)."""
    return db.query(Sale).options(
        selectinload(Sale.cart)
        .selectinload(Cart.cart_products)
        .selectinload(Cart_Product.product),
        selectinload(Sale.client),
    )


def calculate_cart_total(cart):
    """Total del carrito: precio actual del catálogo x cantidad."""
    if cart is None:
        return 0.0

    total = sum(
        item.product.price * item.quantity
        for item in cart.cart_products
    )
    return round(total, 2)


def calculate_client_total_spent(client):
    total = sum(calculate_cart_total(sale.cart) for sale in client.sales)
    return round(total, 2)


def serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
    }


def serialize_client(client):
    return {
        "id": client.id,
        "name": client.name,
        "total_spent": calculate_client_total_spent(client),
    }


def serialize_cart(cart):
    products = [
        {
            "id": cp.id,
            "product": serialize_product(cp.product),
            "quantity": cp.quantity,
            "subtotal": round(cp.product.price * cp.quantity, 2),
        }
        for cp in cart.cart_products
    ]

    return {
        "id": cart.id,
        "created_at": cart.created_at,
        "status": cart.status,
        "products": products,
        "total_price": calculate_cart_total(cart),
    }


def serialize_sale(sale):
    client = sale.client
    cart = sale.cart

    return {
        "id": sale.id,
        "date": sale.date,
        "time": sale.time,
        "total_price": calculate_cart_total(cart),
        "client": {"id": client.id, "name": client.name} if client else None,
        "cart": serialize_cart(cart) if cart else None,
    }


def get_or_404(db, model, obj_id, label):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def get_assignable_cart(db, cart_id, current_sale_id=None):
    cart = get_or_404(db, Cart, cart_id, "Cart")

    # Un carrito no puede estar asociado a dos ventas.
    if cart.sale is not None and cart.sale.id != current_sale_id:
        raise HTTPException(
            status_code=409,
            detail="Cart already belongs to another sale",
        )

    if cart.status != "closed":
        raise HTTPException(
            status_code=409,
            detail="Only closed carts can be assigned to a sale",
        )

    return cart


def get_editable_cart(db, cart_id):
    """Carrito que todavía se puede modificar (abierto y sin venta)."""
    cart = get_or_404(db, Cart, cart_id, "Cart")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale",
        )
    if cart.status != "open":
        raise HTTPException(status_code=409, detail="Cannot modify a closed cart")

    return cart


def commit_or_raise(db, status_code, detail, *to_refresh):
    """Hace commit; si falla, rollback y devuelve el error HTTP indicado."""
    try:
        db.commit()
        for obj in to_refresh:
            db.refresh(obj)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, db=Depends(get_db)):
    new_product = Product(name=product_data.name, price=product_data.price)
    db.add(new_product)
    commit_or_raise(db, 400, "Error when creating a product", new_product)
    return serialize_product(new_product)


@app.get("/products")
def list_products(db=Depends(get_db)):
    return [serialize_product(p) for p in db.query(Product).all()]


@app.get("/products/{id}")
def get_product(id: int, db=Depends(get_db)):
    return serialize_product(get_or_404(db, Product, id, "Product"))


@app.put("/products/{id}")
def modify_product(id: int, product_data: ProductUpdate, db=Depends(get_db)):
    product = get_or_404(db, Product, id, "Product")

    changes = product_data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(product, field, value)

    commit_or_raise(db, 400, "Error when updating product", product)
    return serialize_product(product)


@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(id: int, db=Depends(get_db)):
    product = get_or_404(db, Product, id, "Product")

    if product.cart_products:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a product registered in a cart",
        )

    db.delete(product)
    commit_or_raise(db, 409, "Could not delete product")


# ---------------------------------------------------------------------------
# Carts
# ---------------------------------------------------------------------------

@app.post("/carts", status_code=status.HTTP_201_CREATED)
def create_cart(cart_data: CartCreate, db=Depends(get_db)):
    new_cart = Cart(created_at=cart_data.created_at, status=cart_data.status)
    db.add(new_cart)
    commit_or_raise(db, 400, "Error when creating a cart", new_cart)
    return serialize_cart(new_cart)


@app.get("/carts")
def list_carts(db=Depends(get_db)):
    carts = db.query(Cart).options(
        selectinload(Cart.cart_products).selectinload(Cart_Product.product)
    ).all()
    return [serialize_cart(cart) for cart in carts]


@app.get("/carts/{id}")
def get_cart(id: int, db=Depends(get_db)):
    return serialize_cart(get_or_404(db, Cart, id, "Cart"))


@app.put("/carts/{id}")
def update_cart(id: int, cart_data: CartUpdate, db=Depends(get_db)):
    cart = get_or_404(db, Cart, id, "Cart")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale",
        )

    changes = cart_data.model_dump(exclude_unset=True, exclude_none=True)

    if cart.status == "closed" and changes.get("status") == "open":
        raise HTTPException(
            status_code=409,
            detail="A closed cart cannot be reopened",
        )

    for field, value in changes.items():
        setattr(cart, field, value)

    commit_or_raise(db, 400, "Error when updating cart", cart)
    return serialize_cart(cart)


@app.delete("/carts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart(id: int, db=Depends(get_db)):
    cart = get_or_404(db, Cart, id, "Cart")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a cart associated with a sale",
        )

    db.delete(cart)
    commit_or_raise(db, 409, "Could not delete cart")


# ---------------------------------------------------------------------------
# Cart products
# ---------------------------------------------------------------------------

@app.post("/carts/{id}/products", status_code=status.HTTP_201_CREATED)
def add_product_to_cart(
    id: int,
    product_data: CartProductCreate,
    db=Depends(get_db),
):
    get_editable_cart(db, id)
    product = get_or_404(db, Product, product_data.product_id, "Product")

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product.id,
    ).first()

    if cart_product is not None:
        cart_product.quantity += product_data.quantity
    else:
        cart_product = Cart_Product(
            id_cart=id,
            id_product=product.id,
            quantity=product_data.quantity,
        )
        db.add(cart_product)

    commit_or_raise(db, 400, "Error when adding product to cart", cart_product)

    return {
        "id": cart_product.id,
        "product_id": cart_product.id_product,
        "quantity": cart_product.quantity,
        "unit_price": product.price,
        "subtotal": round(product.price * cart_product.quantity, 2),
    }


@app.delete(
    "/carts/{id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_product_from_cart(id: int, product_id: int, db=Depends(get_db)):
    get_editable_cart(db, id)

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product_id,
    ).first()

    if cart_product is None:
        raise HTTPException(status_code=404, detail="Product not found in this cart")

    db.delete(cart_product)
    commit_or_raise(db, 400, "Error when removing product from cart")


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

@app.post("/sales", status_code=status.HTTP_201_CREATED)
def create_sale(sale_data: SaleCreate, db=Depends(get_db)):
    cart = get_assignable_cart(db, sale_data.cart_id)
    client = get_or_404(db, Client, sale_data.client_id, "Client")

    new_sale = Sale(
        date=sale_data.date,
        time=sale_data.time,
        id_cart=cart.id,
        id_client=client.id,
    )
    db.add(new_sale)
    commit_or_raise(
        db, 409, "Could not create sale. Check cart assignment.", new_sale
    )
    return serialize_sale(new_sale)


@app.get("/sales")
def list_sales(db=Depends(get_db)):
    return [serialize_sale(sale) for sale in sales_query(db).all()]


@app.get("/sales/recent")
def get_recent_sales(
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    sales = (
        sales_query(db)
        .order_by(Sale.date.desc(), Sale.time.desc(), Sale.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_sale(sale) for sale in sales]


@app.get("/sales/{id}")
def get_sale(id: int, db=Depends(get_db)):
    return serialize_sale(get_or_404(db, Sale, id, "Sale"))


@app.put("/sales/{id}")
def update_sale(id: int, sale_data: SaleUpdate, db=Depends(get_db)):
    sale = get_or_404(db, Sale, id, "Sale")

    changes = sale_data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(sale, field, value)

    commit_or_raise(db, 400, "Error when updating sale", sale)
    return serialize_sale(sale)


@app.post("/sales/{id}/cart")
def assign_cart_to_sale(id: int, data: SaleCartAssign, db=Depends(get_db)):
    sale = get_or_404(db, Sale, id, "Sale")

    if data.cart_id is None:
        sale.id_cart = None
    else:
        cart = get_assignable_cart(db, data.cart_id, current_sale_id=id)
        sale.id_cart = cart.id

    commit_or_raise(db, 409, "Could not assign or unlink cart", sale)
    return serialize_sale(sale)


@app.delete("/sales/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(id: int, db=Depends(get_db)):
    sale = get_or_404(db, Sale, id, "Sale")
    db.delete(sale)
    commit_or_raise(db, 400, "Error when deleting sale")



@app.post("/clients", status_code=status.HTTP_201_CREATED)
def create_client(client_data: ClientCreate, db=Depends(get_db)):
    new_client = Client(name=client_data.name)
    db.add(new_client)
    commit_or_raise(db, 400, "Error when creating client", new_client)
    return serialize_client(new_client)


@app.get("/clients")
def list_clients(db=Depends(get_db)):
    clients = db.query(Client).options(
        selectinload(Client.sales)
        .selectinload(Sale.cart)
        .selectinload(Cart.cart_products)
        .selectinload(Cart_Product.product)
    ).all()
    return [serialize_client(client) for client in clients]


@app.get("/clients/{id}")
def get_client(id: int, db=Depends(get_db)):
    return serialize_client(get_or_404(db, Client, id, "Client"))


@app.put("/clients/{id}")
def update_client(id: int, client_data: ClientUpdate, db=Depends(get_db)):
    client = get_or_404(db, Client, id, "Client")

    changes = client_data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(client, field, value)

    commit_or_raise(db, 400, "Error when updating client", client)
    return serialize_client(client)


@app.get("/clients/{id}/sales")
def get_client_sales(id: int, db=Depends(get_db)):
    client = get_or_404(db, Client, id, "Client")

    sales = (
        sales_query(db)
        .filter(Sale.id_client == client.id)
        .order_by(Sale.date.desc(), Sale.time.desc(), Sale.id.desc())
        .all()
    )
    return [serialize_sale(sale) for sale in sales]

@app.delete("/clients/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(id: int, db=Depends(get_db)):
    client = get_or_404(db, Client, id, "Client")

    if client.sales:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a client with registered sales",
        )

    db.delete(client)
    commit_or_raise(db, 400, "Error when deleting client")