import asyncio
import websockets
import json
import os
import zmq
import time
from dotenv import load_dotenv
from bridge.schemas import Order, OrderSide, OrderStatus
from bridge.decoder import encode_order

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")

# Mapping Finnhub symbols to Chronos engine symbols (max 8 chars)
SYMBOL_MAP = {
    "BINANCE:BTCUSDT": "BTC",
    "BINANCE:ETHUSDT": "ETH",
    "AAPL": "AAPL"
}

# Initialize ZMQ context and DEALER socket
zmq_context = zmq.Context()
ingress_socket = zmq_context.socket(zmq.DEALER)
ingress_socket.setsockopt(zmq.IDENTITY, b"market_feeder")
ingress_socket.connect("tcp://localhost:5555")

# Global Order ID counter for the feeder
order_id_counter = 500000

def synthesize_and_send_orders(trade_data):
    """
    Takes a single Finnhub trade event and generates a matching Buy/Sell 
    Limit Order pair to force an execution in the Chronos Engine.
    """
    global order_id_counter
    
    finnhub_sym = trade_data.get('s')
    chronos_sym = SYMBOL_MAP.get(finnhub_sym)
    
    if not chronos_sym:
        return
        
    raw_price = trade_data.get('p', 0.0)
    raw_qty = trade_data.get('v', 0.0)
    
    # Chronos uses fixed-point integers. 
    # Price scale: x100 (e.g. 150.25 -> 15025)
    # Qty scale: We ensure at least 1, scaling up fractional crypto volumes.
    price = int(raw_price * 100)
    qty = max(1, int(raw_qty * 1000)) 
    timestamp = int(time.time_ns())

    # Create Buy Order
    order_id_counter += 1
    buy_order = Order(
        id=order_id_counter,
        symbol=chronos_sym,
        price=price,
        quantity=qty,
        side=OrderSide.BUY,
        status=OrderStatus.NEW,
        timestamp=timestamp
    )
    
    # Create Sell Order
    order_id_counter += 1
    sell_order = Order(
        id=order_id_counter,
        symbol=chronos_sym,
        price=price,
        quantity=qty,
        side=OrderSide.SELL,
        status=OrderStatus.NEW,
        timestamp=timestamp
    )
    
    # Send binary to C++ Engine
    ingress_socket.send(encode_order(buy_order))
    ingress_socket.send(encode_order(sell_order))

async def connect_to_finnhub():
    if not FINNHUB_API_KEY or FINNHUB_API_KEY == "your_api_key_here":
        print("[Feeder] Error: FINNHUB_API_KEY is not set or is invalid in bridge/.env")
        return

    url = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
    
    async for websocket in websockets.connect(url):
        try:
            print("[Feeder] Connected to Finnhub WebSocket.")
            
            # Subscribe to symbols
            for symbol in SYMBOL_MAP.keys():
                await websocket.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                print(f"[Feeder] Subscribed to {symbol}")

            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'trade':
                    # data['data'] contains a list of trade objects
                    for trade in data.get('data', []):
                        synthesize_and_send_orders(trade)

        except websockets.ConnectionClosed:
            print("[Feeder] Connection closed, reconnecting...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[Feeder] Error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    print("[Feeder] Starting Market Data Feeder...")
    asyncio.run(connect_to_finnhub())
