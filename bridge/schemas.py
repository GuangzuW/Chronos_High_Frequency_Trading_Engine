from pydantic import BaseModel, Field
from enum import IntEnum
from typing import Optional

class OrderSide(IntEnum):
    BUY = 0
    SELL = 1

class OrderStatus(IntEnum):
    NEW = 0
    PARTIAL = 1
    FILLED = 2
    CANCELED = 3
    REJECTED = 4

class Order(BaseModel):
    id: int
    symbol: str = Field(..., max_length=8)
    price: int
    quantity: int
    side: OrderSide
    status: OrderStatus = OrderStatus.NEW
    timestamp: int = 0

class Trade(BaseModel):
    buy_order_id: int
    sell_order_id: int
    price: int
    quantity: int
    timestamp: int

class OrderRequest(BaseModel):
    """Simplified model for incoming REST API requests"""
    symbol: str
    price: int
    quantity: int
    side: OrderSide
