from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel

from models import Product, Session


app = FastAPI()


class ProductCreate(BaseModel):
    name: str
    price: float


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None



def get_db():
    db = Session()

    try:
        yield db
    finally:
        db.close()



@app.post("/productos", status_code=status.HTTP_201_CREATED)
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


@app.get("/productos")
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



@app.get("/productos/{id}")
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



@app.put("/productos/{id}")
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
    "/productos/{id}",
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

    db.delete(product)
    db.commit()

    return None