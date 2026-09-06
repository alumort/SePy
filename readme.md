# Products & Sales API

Individual project for the *Seminario de lenguajes Python* course — Licenciatura en Sistemas, Universidad Nacional de Lanús (UNLa), 2026.

## Description

REST API built with **FastAPI** and **SQLAlchemy** (SQLite) to manage products and sales. Implements full CRUD (Create, Read, Update, Delete) operations following the course's lab assignment.

## Status

🚧 Work in progress — currently implementing the Product ABM (CRUD). Sales ABM to follow.

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

## Endpoints (planned)

### Products
- `POST /productos` — create a new product
- `GET /productos` — list all products
- `GET /productos/{id}` — get a product by id
- `PUT /productos/{id}` — update a product
- `DELETE /productos/{id}` — delete a product

### Sales
- `POST /ventas` — create a new sale
- `GET /ventas` — list all sales
- `GET /ventas/{id}` — get a sale by id
- `PUT /ventas/{id}` — update a sale
- `DELETE /ventas/{id}` — delete a sale

## Setup

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Notes

This is a coursework project — some naming conventions were kept in Spanish where required by the assignment spec (e.g. endpoint paths), while internal code follows English naming conventions where possible.
