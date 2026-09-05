from fastapi import FastAPI, HTTPException, status, Depends
from models import Product, session


app = FastAPI()

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()
#POST

@app.post("/productos", status_code=status.HTTP_201_CREATED)
def create_product(product_data, db  session = Depends(get_db)):
    new_product = Product(
    name = product_data.name,
    price = product_data.price)
    db.add(new_product)
    try:
        db.commit()
        db.refresh(new_product)
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error when creating a product")
    return vars(new_product)


#GET
@app.get("/productos")
def list_products(db  session = Depends(get_db)):
    products = session.query(Product).all()
    return [vars(p) for p in products]

@app.get("/productos/{id}")
def get_product(id: int, db  session = Depends(get_db)):
    product = session.query(Product).get(id)
    if product is None:
            raise HTTPException(status_code=404, detail="Product not found :(")
    return vars(product)

