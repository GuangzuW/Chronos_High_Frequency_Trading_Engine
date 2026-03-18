import asyncio
import threading
import zmq
import json
import time
import os
import subprocess
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from bridge.schemas import Order, Trade, OrderRequest, OrderStatus
from bridge.decoder import decode_order, decode_trade, encode_order

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI(title="Chronos API Bridge")

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global ZMQ context and sockets
zmq_context = zmq.Context()
ingress_socket = zmq_context.socket(zmq.DEALER)
ingress_socket.setsockopt(zmq.IDENTITY, b"bridge_proxy")
ingress_socket.connect("tcp://localhost:5555")

# Simple order ID generator
order_id_counter = 1000

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

def zmq_listener():
    """Background thread to poll ZMQ PUB/SUB from the engine"""
    sub_socket = zmq_context.socket(zmq.SUB)
    sub_socket.connect("tcp://localhost:5556")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "TRADE")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ORDER")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            topic = sub_socket.recv_string()
            payload = sub_socket.recv()
            
            event_data = {}
            if topic == "TRADE":
                trade = decode_trade(payload)
                event_data = {"type": "TRADE", "data": trade.model_dump()}
            elif topic == "ORDER":
                order = decode_order(payload)
                event_data = {"type": "ORDER", "data": order.model_dump()}
            
            if event_data:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(event_data)), 
                    loop
                )
        except Exception as e:
            print(f"ZMQ Listener Error: {e}")

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=zmq_listener, daemon=True)
    thread.start()
    
    if os.environ.get("START_FEEDER") == "1":
        print("[Bridge] Starting Market Data Feeder subprocess...")
        subprocess.Popen(["python", "bridge/feeder.py"])

@app.get("/health")
async def health_check():
    return {"status": "online", "service": "Chronos API Bridge"}

@app.post("/order")
async def place_order(request: OrderRequest):
    global order_id_counter
    order_id_counter += 1
    
    # Scale to engine fixed-point
    price = int(request.price * 100)
    quantity = int(request.quantity * 1000)

    order = Order(
        id=order_id_counter,
        symbol=request.symbol,
        price=price,
        quantity=quantity,
        side=request.side,
        status=OrderStatus.NEW,
        timestamp=int(time.time_ns())
    )
    
    # Send binary to C++ engine
    binary_data = encode_order(order)
    ingress_socket.send(binary_data)
    
    return {"status": "submitted", "order_id": order.id}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
