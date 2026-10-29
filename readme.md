# SePy — Products and Sales API

REST API developed as an individual project for **Seminario de Python**, part of the Licenciatura en Sistemas at Universidad Nacional de Lanús (UNLa), Argentina (2026).

## Overview

SePy is a backend project for managing products, shopping carts, sales, and clients. It provides REST endpoints for creating, retrieving, updating, and deleting records, as well as managing cart contents and retrieving sales information.

## Tech Stack

- **Python 3.12**
- **FastAPI** — REST API development
- **SQLAlchemy** — ORM and database operations
- **SQLite** — relational database
- **Pydantic** — request data validation
- **Uvicorn** — ASGI server

## Features

### Products
- Create, list, retrieve, update, and delete products.
- Validate product names and require prices greater than zero.
- Prevent deletion of products registered in shopping carts.

### Shopping Carts
- Create, list, retrieve, update, and delete shopping carts.
- Manage cart status (`open` or `closed`).
- Add products to a cart and increase the quantity of products already present.
- Remove products from a cart.
- Calculate product subtotals and cart totals.
- Prevent modifications to carts that are associated with sales or are closed.
- Require carts to be closed before associating them with sales.

### Clients
- Create, list, retrieve, update, and delete clients.
- Associate clients with their sales using a one-to-many relationship.
- Retrieve all sales associated with a specific client.
- Calculate the total amount spent by each client.
- Prevent deletion of clients who have registered sales.

### Sales
- Create, list, retrieve, update, and delete sales.
- Associate sales with clients and shopping carts.
- Retrieve the most recent sales, ordered by date and time.
- Filter a client's sales and order them from newest to oldest.
- Calculate sale totals using the products and quantities in the associated cart.
- Prevent a cart from being assigned to more than one sale.

### Data validation and error handling
- Validate request bodies using Pydantic schemas.
- Use HTTP status codes to report errors, including `404 Not Found`, `409 Conflict`, and `400 Bad Request`.
- Handle database transaction errors with rollback where applicable.
- Enforce database constraints, including unique product entries per cart and positive product quantities.

## Data Model

The application uses four main entities and a cart-product association table:

- **Product:** stores product names and prices.
- **Client:** stores client names.
- **Cart:** stores creation dates and status.
- **Sale:** stores sale dates, times, client references, and cart references.
- **Cart_Product:** associates products with carts and stores quantities.

A client can have multiple sales. Each sale can be associated with a client and a cart, while each cart can contain multiple products.

## API Endpoints

All endpoints use the `/` root path and exchange JSON unless otherwise indicated.

### Products

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/products` | Create a product |
| `GET` | `/products` | List all products |
| `GET` | `/products/{id}` | Retrieve a product |
| `PUT` | `/products/{id}` | Update a product |
| `DELETE` | `/products/{id}` | Delete a product |

### Shopping Carts

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/carts` | Create a cart |
| `GET` | `/carts` | List all carts |
| `GET` | `/carts/{id}` | Retrieve a cart and its products |
| `PUT` | `/carts/{id}` | Update a cart |
| `DELETE` | `/carts/{id}` | Delete a cart |
| `POST` | `/carts/{id}/products` | Add a product to a cart |
| `DELETE` | `/carts/{id}/products/{product_id}` | Remove a product from a cart |

### Sales

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sales` | Create a sale |
| `GET` | `/sales` | List all sales |
| `GET` | `/sales/recent` | Retrieve the most recent sales |
| `GET` | `/sales/{id}` | Retrieve a sale |
| `PUT` | `/sales/{id}` | Update a sale's date or time |
| `POST` | `/sales/{id}/cart` | Assign or unlink a cart |
| `DELETE` | `/sales/{id}` | Delete a sale |

The recent sales endpoint accepts an optional `limit` query parameter, defaulting to 10 and allowing values between 1 and 100.

Example: `GET /sales/recent?limit=5`

### Clients

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/clients` | Create a client |
| `GET` | `/clients` | List clients and their total spending |
| `GET` | `/clients/{id}` | Retrieve a client and their total spending |
| `PUT` | `/clients/{id}` | Update a client's name |
| `DELETE` | `/clients/{id}` | Delete a client without registered sales |
| `GET` | `/clients/{id}/sales` | Retrieve a client's sales |

## Getting Started

### Requirements

- Python 3.12
- pip

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/alumort/SePy.git
   cd SePy
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the development server:

   ```bash
   uvicorn app:app --reload
   ```

4. Open the interactive API documentation:

   [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The application uses a local SQLite database named `products.db`.

## Implementation Notes

- Database models and relationships are defined in `models.py`.
- API routes, Pydantic schemas, serialization, and business logic are defined in `app.py`.
- Database tables are initialized through SQLAlchemy's `Base.metadata.create_all()`.
- The total spent by a client is calculated from the totals of their associated sales. Sale totals use the current catalog prices multiplied by the quantities in the associated cart, so changing a product's price can affect previously calculated sale totals.
- `create_all()` creates missing tables but does not automatically migrate existing tables when their schema changes.

## Project Context

SePy is an academic project developed to practice Python backend development, REST API design, relational data modeling, database operations, request validation, and business logic using FastAPI and SQLAlchemy.
