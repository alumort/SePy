from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import date
from models import Product, Cart, Sale, Cart_Product, Session
from pydantic import BaseModel, Field
from typing import Literal

app = FastAPI()

class CartProductCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class ProductCreate(BaseModel):
    name: str
    price: float

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

class CartCreate(BaseModel):
    created_at: date
    status: str

class CartUpdate(BaseModel):
    created_at: date | None = None
    status: Literal["open", "closed"] | None = None


class SaleCreate(BaseModel):
    cart_id: int


def get_db():
    db = Session()

    try:
        yield db
    finally:
        db.close()


# product

@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db = Depends(get_db)
):
    new_product = Product(
        name=product_data.name,
        price=product_data.price
    )

    db.add(new_product)

    try:
        db.commit()
        db.refresh(new_product)
    except:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when creating a product"
        )

    return {
        "id": new_product.id,
        "name": new_product.name,
        "price": new_product.price
    }


@app.get("/products")
def list_products(db = Depends(get_db)):
    products = db.query(Product).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price
        }
        for p in products
    ]



@app.get("/products/{id}")
def get_product(
    id: int,
    db = Depends(get_db)
):
    product = db.get(Product, id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found :("
        )

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price
    }



@app.put("/products/{id}")
def modify_product(
    id: int,
    product_data: ProductUpdate,
    db = Depends(get_db)
):
    product = db.get(Product, id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product_data.name is not None:
        product.name = product_data.name

    if product_data.price is not None:
        product.price = product_data.price

    db.commit()
    db.refresh(product)

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price
    }


@app.delete(
    "/products/{id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_product(
    id: int,
    db = Depends(get_db)
):
    product = db.get(Product, id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    elif product.cart_products:        
            raise HTTPException(
            status_code=409,
            detail="Can't delete products inside of a cart"
        )
    else:
            db.delete(product)
            db.commit()

    return None

# sale

@app.post("/sales", status_code=status.HTTP_201_CREATED)
def create_sale(
    sale_data: SaleCreate,
    db = Depends(get_db)
):
    cart = db.get(Cart, sale_data.cart_id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    if cart.sale:
        raise HTTPException(
            status_code=409,
            detail="This cart already has a sale"
        )

    if cart.status != "closed":
        raise HTTPException(
            status_code=409,
            detail="Cannot create a sale for an open cart"
        )

    if not cart.cart_products:
        raise HTTPException(
            status_code=409,
            detail="Cannot create a sale for an empty cart"
        )

    new_sale = Sale(
        id_cart=cart.id
    )

    db.add(new_sale)

    try:
        db.commit()
        db.refresh(new_sale)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when creating a sale"
        )

    return {
        "id": new_sale.id,
        "cart_id": new_sale.id_cart,
        "date": new_sale.date,
        "time": new_sale.time
    }


@app.get("/sales")
def list_sales(db = Depends(get_db)):
    sales = db.query(Sale).all()

    return [
        {
            "id": sale.id,
            "cart_id": sale.id_cart,
            "date": sale.date,
            "time": sale.time
        }
        for sale in sales
    ]


@app.get("/sales/{id}")
def get_sale(
    id: int,
    db = Depends(get_db)
):
    sale = db.get(Sale, id)

    if sale is None:
        raise HTTPException(
            status_code=404,
            detail="Sale not found"
        )

    return {
        "id": sale.id,
        "cart_id": sale.id_cart,
        "date": sale.date,
        "time": sale.time
    }

# cart


@app.post("/carts", status_code=status.HTTP_201_CREATED)
def create_cart(
    cart_data: CartCreate,
    db = Depends(get_db)
):
    new_cart = Cart(
        created_at=cart_data.created_at,
        status = cart_data.status
    )

    db.add(new_cart)

    try:
        db.commit()
        db.refresh(new_cart)
    except:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when creating a cart"
        )

    return {
        "id": new_cart.id,
        "created_at": new_cart.created_at,
        "status": new_cart.status
    }


@app.get("/carts")
def list_carts(db = Depends(get_db)):
    carts = db.query(Cart).all()

    return [
        {
            "id": c.id,
            "created_at": c.created_at,
            "status": c.status
        }
        for c in carts
    ]




@app.get("/carts/{id}")
def get_cart(
    id: int,
    db = Depends(get_db)
):
    cart = db.get(Cart, id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    return {
        "id": cart.id,
        "created_at": cart.created_at,
        "status": cart.status,
        "products": [
            {
                "product_id": cp.id_product,
                "name": cp.product.name,
                "price": cp.product.price,
                "quantity": cp.quantity
            }
            for cp in cart.cart_products
        ]
    }


@app.put("/carts/{id}")
def update_cart(
    id: int,
    cart_data: CartUpdate,
    db=Depends(get_db)
):
    cart = db.get(Cart, id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    if cart.sale:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale"
        )

    if cart_data.created_at is not None:
        cart.created_at = cart_data.created_at

    if cart_data.status is not None:
        cart.status = cart_data.status

    try:
        db.commit()
        db.refresh(cart)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when updating cart"
        )

    return {
        "id": cart.id,
        "created_at": cart.created_at,
        "status": cart.status
    }


@app.delete(
    "/carts/{id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_cart(
    id: int,
    db = Depends(get_db)
):
    cart = db.get(Cart, id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    if cart.sale:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a cart associated with a sale"
        )

    try:
        db.query(Cart_Product).filter_by(
            id_cart=id
        ).delete(synchronize_session=False)

        db.delete(cart)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when deleting cart"
        )

    return None


# cart product

@app.post("/carts/{id}/products", status_code=status.HTTP_201_CREATED)
def add_product_to_cart(
    id: int,
    product_data: CartProductCreate,
    db=Depends(get_db)
):
    cart = db.get(Cart, id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    if cart.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a closed cart"
        )

    product = db.get(Product, product_data.product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product_data.product_id
    ).first()

    if cart_product:
        cart_product.quantity += product_data.quantity
    else:
        cart_product = Cart_Product(
            id_cart=id,
            id_product=product_data.product_id,
            quantity=product_data.quantity
        )
        db.add(cart_product)

    try:
        db.commit()
        db.refresh(cart_product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when adding product to cart"
        )

    return {
        "id": cart_product.id,
        "product_id": cart_product.id_product,
        "quantity": cart_product.quantity
    }


@app.delete(
    "/carts/{id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remove_product_from_cart(
    id: int,
    product_id: int,
    db=Depends(get_db)
):
    cart = db.get(Cart, id)

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    if cart.sale:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify a cart associated with a sale"
        )

    if cart.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Cannot remove products from a closed cart"
        )

    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    cart_product = db.query(Cart_Product).filter_by(
        id_cart=id,
        id_product=product_id
    ).first()

    if cart_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found in this cart"
        )

    try:
        db.delete(cart_product)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error when removing product from cart"
        )

    return None
