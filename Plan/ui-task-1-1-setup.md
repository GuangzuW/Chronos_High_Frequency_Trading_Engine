# Implementation Plan: Task 1.1 - API Bridge Environment & Schemas

Initialize the Python-based API Bridge that will serve as the middleware between the C++ engine and the web frontend.

## Objective
Setup the project structure for the FastAPI bridge and define Pydantic models that mirror the C++ `Order` and `Trade` data structures.

## Key Files
- `bridge/requirements.txt`: Python dependencies.
- `bridge/schemas.py`: Pydantic models for JSON validation and serialization.
- `bridge/main.py`: Entry point for the FastAPI application.

## Implementation Steps

### 1. Project Initialization
- Create the `bridge/` directory.
- Create `bridge/requirements.txt` with:
    - `fastapi`
    - `uvicorn`
    - `pyzmq`
    - `pydantic`

### 2. Define Data Models (`bridge/schemas.py`)
- Create `OrderSide` and `OrderStatus` Enums (matching C++ values).
- Define `Order` Pydantic model:
    - `id: int`
    - `symbol: str`
    - `price: int`
    - `quantity: int`
    - `side: OrderSide`
    - `status: OrderStatus`
    - `timestamp: int`
- Define `Trade` Pydantic model:
    - `buy_order_id: int`
    - `sell_order_id: int`
    - `price: int`
    - `quantity: int`
    - `timestamp: int`

### 3. Basic FastAPI App (`bridge/main.py`)
- Initialize FastAPI instance.
- Add a simple `/health` endpoint to verify the bridge is running.

## Verification
- Run `pip install -r bridge/requirements.txt` (locally, or I'll just assume dependencies for now).
- Start the server using `uvicorn main:app --reload` and check the health endpoint.
