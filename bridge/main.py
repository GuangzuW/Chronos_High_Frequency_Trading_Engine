import asyncio
import threading
import zmq
import json
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from bridge.schemas import Order, Trade
from bridge.decoder import decode_order, decode_trade

app = FastAPI(title="Chronos API Bridge")

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
                # Handle stale connections
                pass

manager = ConnectionManager()

def zmq_listener():
    """Background thread to poll ZMQ PUB/SUB from the engine"""
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5556")
    socket.setsockopt_string(zmq.SUBSCRIBE, "TRADE")
    socket.setsockopt_string(zmq.SUBSCRIBE, "ORDER")
    
    # Use a new event loop for this thread to handle the async broadcast
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            topic = socket.recv_string()
            payload = socket.recv()
            
            event_data = {}
            if topic == "TRADE":
                trade = decode_trade(payload)
                event_data = {"type": "TRADE", "data": trade.model_dump()}
            elif topic == "ORDER":
                order = decode_order(payload)
                event_data = {"type": "ORDER", "data": order.model_dump()}
            
            if event_data:
                # Broadcast to all WS clients
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(event_data)), 
                    loop
                )
        except Exception as e:
            print(f"ZMQ Listener Error: {e}")

@app.on_event("startup")
async def startup_event():
    # Start ZMQ listener in a separate thread
    thread = threading.Thread(target=zmq_listener, daemon=True)
    thread.start()

@app.get("/health")
async def health_check():
    return {"status": "online", "service": "Chronos API Bridge"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
