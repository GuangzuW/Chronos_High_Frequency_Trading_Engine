from fastapi import FastAPI
from bridge.schemas import Order, Trade

app = FastAPI(title="Chronos API Bridge")

@app.get("/health")
async def health_check():
    return {"status": "online", "service": "Chronos API Bridge"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
