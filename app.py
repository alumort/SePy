from fastapi import FastAPI
from models import Product, session

app = FastAPI()



for product in session.query(Product).all():
 print(product.name, product)

