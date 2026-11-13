import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db_manager import init_db, get_connection
from agent.agent_core import InventoryAgent
from agent.inventory_tools import get_inventory, get_low_stock_items, get_warehouses

load_dotenv(ROOT_DIR / ".env")
init_db()

app = FastAPI(title="P09 Inventory Agent API")
app.mount("/static", StaticFiles(directory=ROOT_DIR / "app" / "static"), name="static")

agent_instance: InventoryAgent | None = None
current_api_key: str = ""

class ChatRequest(BaseModel):
    message: str
    api_key: str | None = None

@app.get("/")
def serve_index():
    return FileResponse(ROOT_DIR / "app" / "static" / "index.html")

@app.get("/api/dashboard")
def get_dashboard_data():
    items = get_inventory()
    low_stock = get_low_stock_items()
    warehouses = get_warehouses()
    
    with get_connection() as conn:
        txs = conn.execute(
            """SELECT t.id, i.name AS item, t.type, t.quantity, t.notes, t.timestamp
               FROM transactions t
               JOIN items i ON t.item_id = i.id
               ORDER BY t.id DESC LIMIT 50"""
        ).fetchall()

    total_qty = sum(item["quantity"] for item in items)
    env_key = os.getenv("GEMINI_API_KEY", "")
    has_env_key = bool(env_key and env_key != "YOUR_API_KEY_HERE")

    return {
        "stats": {
            "warehouses_count": len(warehouses),
            "items_count": len(items),
            "total_quantity": total_qty,
            "low_stock_count": len(low_stock),
        },
        "items": items,
        "low_stock": low_stock,
        "warehouses": warehouses,
        "transactions": [dict(r) for r in txs],
        "has_env_key": has_env_key,
    }

@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    global agent_instance, current_api_key
    key = (req.api_key or "").strip() or os.getenv("GEMINI_API_KEY", "")
    
    if not key or key == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=400, detail="Please enter a valid Gemini API Key in the top bar.")

    try:
        if agent_instance is None or current_api_key != key:
            agent_instance = InventoryAgent(api_key=key)
            current_api_key = key
        
        reply = agent_instance.ask(req.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
