from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
import datetime

from models import Product, Cart, Sale, Cart_Product, Session


app = FastAPI()


class CartProductCreate(BaseModel):
    # El cliente solo puede indicar producto y cantidad, nunca el precio.
    model_config = ConfigDict(extra="forbid")

    product_id: int
    quantity: int = Field(gt=0)


class ProductCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)


class CartCreate(BaseModel):
    created_at: datetime.date
    status: Literal["open", "closed"] = "open"


class CartUpdate(BaseModel):
    created_at: datetime.date | None = None
    status: Literal["open", "closed"] | None = None


class SaleCreate(BaseModel):
    # No se acepta total_price: la API siempre lo calcula.
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    time: datetime.time
    cart_id: int


class SaleUpdate(BaseModel):
    # Solo se pueden modificar fecha y hora de la venta.
    model_config = ConfigDict(extra="forbid")

    date: datetime.date | None = None
    time: datetime.time | None = None


class SaleCartAssign(BaseModel):
    # Enviar {"cart_id": null} desvincula el carrito de la venta.
    model_config = ConfigDict(extra="forbid")

    cart_id: int | None


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def calculate_cart_total(cart):
    """Calcula el total con el precio del catálogo por la cantidad."""
    if cart is None:
        return 0.0

    total = sum(
        item.product.price * item.quantity
        for item in cart.cart_products
    )
    return round(total, 2)


def serialize_cart(cart):
    products = []

    for cp in cart.cart_products:
        unit_price = cp.product.price
        products.append({
            "id": cp.id,
            "product": {
                "id": cp.product.id,
                "name": cp.product.name,
                "price": unit_price,
            },
            "quantity": cp.quantity,
            "subtotal": round(unit_price * cp.quantity, 2),
        })

    return {
        "id": cart.id,
        "created_at": cart.created_at,
        "status": cart.status,
        "products": products,
        "total_price": calculate_cart_total(cart),
    }


def serialize_sale(sale):
    cart = sale.cart

    return {
        "id": sale.id,
        "date": sale.date,
        "time": sale.time,
        "total_price": calculate_cart_total(cart),
        "cart": serialize_cart(cart) if cart is not None else None,
    }


def get_assignable_cart(db, cart_id, current_sale_id=None):
    cart = db.get(Cart, cart_id)

    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

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

@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, db=Depends(get_db)):
    new_product = Product(
        name=product_data.name,
        price=product_data.price,
    )
    db.add(new_product)

    try:
        db.commit()
        db.refresh(new_product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when creating a product",
        )

    return {
        "id": new_product.id,
        "name": new_product.name,
        "price": new_product.price,
    }


@app.get("/products")
def list_products(db=Depends(get_db)):
    products = db.query(Product).all()
    return [
        {"id": p.id, "name": p.name, "price": p.price}
        for p in products
    ]


@app.get("/products/{id}")
def get_product(id: int, db=Depends(get_db)):
    product = db.get(Product, id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
    }


@app.put("/products/{id}")
def modify_product(id: int, product_data: ProductUpdate, db=Depends(get_db)):
    product = db.get(Product, id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    changes = product_data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        product.name = changes["name"]
    if "price" in changes and changes["price"] is not None:
        product.price = changes["price"]

    try:
        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when updating product")

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
    }


@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(id: int, db=Depends(get_db)):
    product = db.get(Product, id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.cart_products:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a product registered in a cart",
        )

    try:
        db.delete(product)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not delete product")

    return None


@app.post("/carts", status_code=status.HTTP_201_CREATED)
def create_cart(cart_data: CartCreate, db=Depends(get_db)):
    new_cart = Cart(
        created_at=cart_data.created_at,
        status=cart_data.status,
    )
    db.add(new_cart)

    try:
        db.commit()
        db.refresh(new_cart)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when creating a cart")

    return {
        "id": new_cart.id,
        "created_at": new_cart.created_at,
        "status": new_cart.status,
    }


@app.get("/carts")
def list_carts(db=Depends(get_db)):
    carts = db.query(Cart).all()
    return [
        {
            "id": cart.id,
            "created_at": cart.created_at,
            "status": cart.status,
        }
        for cart in carts
    ]


@app.get("/carts/{id}")
def get_cart(id: int, db=Depends(get_db)):
    cart = db.get(Cart, id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return serialize_cart(cart)


@app.put("/carts/{id}")
def update_cart(id: int, cart_data: CartUpdate, db=Depends(get_db)):
    cart = db.get(Cart, id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale",
        )

    changes = cart_data.model_dump(exclude_unset=True)

    # Los carritos cerrados no se reabren.
    if cart.status == "closed" and changes.get("status") == "open":
        raise HTTPException(
            status_code=409,
            detail="A closed cart cannot be reopened",
        )

    if "created_at" in changes and changes["created_at"] is not None:
        cart.created_at = changes["created_at"]
    if "status" in changes and changes["status"] is not None:
        cart.status = changes["status"]

    try:
        db.commit()
        db.refresh(cart)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when updating cart")

    return serialize_cart(cart)


@app.delete("/carts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart(id: int, db=Depends(get_db)):
    cart = db.get(Cart, id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a cart associated with a sale",
        )

    try:
        # Borramos las líneas antes del carrito para no depender de cascadas.
        db.query(Cart_Product).filter_by(id_cart=id).delete()
        db.delete(cart)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not delete cart")

    return None


@app.post("/carts/{id}/products", status_code=status.HTTP_201_CREATED)
def add_product_to_cart(
    id: int,
    product_data: CartProductCreate,
    db=Depends(get_db),
):
    cart = db.get(Cart, id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale",
        )

    if cart.status != "open":
        raise HTTPException(status_code=409, detail="Cannot modify a closed cart")

    product = db.get(Product, product_data.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product_data.product_id,
    ).first()

    if cart_product is not None:
        cart_product.quantity += product_data.quantity
    else:
        cart_product = Cart_Product(
            id_cart=id,
            id_product=product_data.product_id,
            quantity=product_data.quantity,
        )
        db.add(cart_product)

    try:
        db.commit()
        db.refresh(cart_product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when adding product to cart",
        )

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
    cart = db.get(Cart, id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    if cart.sale is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale",
        )

    if cart.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Cannot remove products from a closed cart",
        )

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product_id,
    ).first()

    if cart_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found in this cart",
        )

    try:
        db.delete(cart_product)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when removing product from cart",
        )

    return None



@app.post("/sales", status_code=status.HTTP_201_CREATED)
def create_sale(sale_data: SaleCreate, db=Depends(get_db)):
    cart = get_assignable_cart(db, sale_data.cart_id)

    new_sale = Sale(
        date=sale_data.date,
        time=sale_data.time,
        id_cart=cart.id,
    )
    db.add(new_sale)

    try:
        db.commit()
        db.refresh(new_sale)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create sale. Check cart assignment.",
        )

    return serialize_sale(new_sale)


@app.get("/sales")
def list_sales(db=Depends(get_db)):
    return [serialize_sale(sale) for sale in db.query(Sale).all()]


@app.get("/sales/{id}")
def get_sale(id: int, db=Depends(get_db)):
    sale = db.get(Sale, id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    return serialize_sale(sale)


@app.put("/sales/{id}")
def update_sale(id: int, sale_data: SaleUpdate, db=Depends(get_db)):
    sale = db.get(Sale, id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    changes = sale_data.model_dump(exclude_unset=True)
    if "date" in changes and changes["date"] is not None:
        sale.date = changes["date"]
    if "time" in changes and changes["time"] is not None:
        sale.time = changes["time"]

    try:
        db.commit()
        db.refresh(sale)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when updating sale")

    return serialize_sale(sale)


@app.post("/sales/{id}/cart")
def assign_cart_to_sale(
    id: int,
    data: SaleCartAssign,
    db=Depends(get_db),
):
    sale = db.get(Sale, id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    if data.cart_id is None:
        # Desvincular no abre ni modifica el carrito: permanece cerrado.
        sale.id_cart = None
    else:
        cart = get_assignable_cart(db, data.cart_id, current_sale_id=id)
        sale.id_cart = cart.id

    try:
        db.commit()
        db.refresh(sale)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not assign or unlink cart",
        )

    return serialize_sale(sale)


@app.delete("/sales/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(id: int, db=Depends(get_db)):
    sale = db.get(Sale, id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    try:
        db.delete(sale)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when deleting sale")

    return None
