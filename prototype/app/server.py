import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from database.db_manager import get_connection, init_and_seed_db
from agent.agent_core import run_inventory_agent, OLLAMA_MODEL

app = FastAPI(title="P09 Autonomous Inventory Agent (N-Team)")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    user_role: str = "OPERATOR"
    user_dept: str = "ALL"

class DecisionActionRequest(BaseModel):
    reviewer_name: str
    reviewer_role: str
    action: str  # "APPROVED" or "REJECTED"
    notes: str = ""

def _seed_users(conn):
    def h(pw): return hashlib.sha256(pw.encode()).hexdigest()
    users = [
        ("manager", h("1234"), "د. منى داود - مدير المخازن العام", "MANAGER", "ALL", "المسؤول المعتمد (صلاحية اعتماد ورفض كاملة)"),
        ("lab_user", h("1234"), "سجاد عايد - مسؤول مختبرات الحاسبات", "OPERATOR", "COMP_LABS", "أمين مختبر الحاسبات (استعلام واقتراح فقط)"),
        ("cold_user", h("1234"), "مريم أمجد - مسؤولة مخزن التبريد", "OPERATOR", "REFRIGERATION", "مسؤولة سلسلة التبريد (صلاحية استعلام واقتراح فقط)"),
        ("ecom_user", h("1234"), "آية أمجد - مسؤولة التجارة الإلكترونية", "OPERATOR", "ECOMMERCE", "مسؤولة مخزن التجارة الإلكترونية (استعلام واقتراح فقط)"),
        ("trade_user", h("1234"), "محمد جابر - أمين التجارة العامة", "OPERATOR", "GEN_TRADE", "أمين مخزن التجارة العامة (استعلام واقتراح فقط)")
    ]
    conn.executemany("""
        INSERT OR REPLACE INTO users (username, password_hash, full_name, role, department_scope, title)
        VALUES (?, ?, ?, ?, ?, ?)
    """, users)
    conn.commit()

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_connection()
    _seed_users(conn)
    pw_hash = hashlib.sha256(req.password.strip().encode()).hexdigest()
    user = conn.execute(
        "SELECT username, full_name, role, department_scope, title FROM users WHERE username = ? AND password_hash = ?",
        (req.username.strip().lower(), pw_hash)
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="02-NFR: اسم المستخدم أو كلمة المرور غير صحيحة.")
    return {"user": dict(user)}

@app.get("/api/state")
def get_system_state():
    conn = get_connection()
    departments = [dict(r) for r in conn.execute("SELECT * FROM departments").fetchall()]
    items = [dict(r) for r in conn.execute("SELECT * FROM items ORDER BY department_code, sku").fetchall()]
    batches = [dict(r) for r in conn.execute("SELECT * FROM batches ORDER BY expiry_date ASC").fetchall()]
    decisions = [dict(r) for r in conn.execute("SELECT * FROM pending_decisions ORDER BY id DESC").fetchall()]
    logs = [dict(r) for r in conn.execute("SELECT * FROM agent_execution_log ORDER BY id DESC LIMIT 100").fetchall()]
    conn.close()

    pending_count = sum(1 for d in decisions if d["status"] == "PENDING")
    low_stock_count = sum(1 for i in items if i["actual_quantity"] <= i["min_threshold"])
    discrepancy_count = sum(1 for i in items if i["book_quantity"] != i["actual_quantity"])

    return {
        "model": OLLAMA_MODEL,
        "kpis": {
            "departments": len(departments),
            "total_items": len(items),
            "low_stock": low_stock_count,
            "discrepancies": discrepancy_count,
            "pending_approvals": pending_count
        },
        "departments": departments,
        "items": items,
        "batches": batches,
        "decisions": decisions,
        "logs": logs
    }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="01-NFR: Message cannot be empty.")
    context_prefix = ""
    if req.user_dept != "ALL":
        context_prefix = f"[User Context: Role={req.user_role}, Assigned Department={req.user_dept}] "
    return run_inventory_agent(context_prefix + req.message.strip())

@app.post("/api/decisions/{decision_id}/review")
def review_decision(decision_id: int, req: DecisionActionRequest):
    # 02-NFR: منع المستخدم التشغيلي من الاعتماد برمجياً من الخادم أيضاً
    if req.reviewer_role != "MANAGER":
        raise HTTPException(status_code=403, detail="02-NFR Access Denied: فقط المسؤول المعتمد (MANAGER) يملك صلاحية الاعتماد أو الرفض.")
    reviewer = req.reviewer_name.strip()
    if not reviewer:
        raise HTTPException(status_code=400, detail="02-NFR: هوية المسؤول مطلوبة.")
    if req.action not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Invalid action.")

    conn = get_connection()
    row = conn.execute("SELECT * FROM pending_decisions WHERE id = ?", (decision_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Decision draft not found.")
    if row["status"] != "PENDING":
        conn.close()
        raise HTTPException(status_code=400, detail=f"Decision already reviewed ({row['status']}).")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = json.loads(row["details_json"])

    if req.action == "APPROVED":
        dtype = row["decision_type"]
        if dtype == "TRANSFER_ORDER":
            qty = float(details["transfer_quantity"])
            conn.execute("UPDATE items SET book_quantity = book_quantity - ?, actual_quantity = actual_quantity - ? WHERE sku = ?",
                         (qty, qty, details["from_sku"]))
            conn.execute("UPDATE items SET book_quantity = book_quantity + ?, actual_quantity = actual_quantity + ? WHERE sku = ?",
                         (qty, qty, details["to_sku"]))
            conn.execute("INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp) VALUES (?, ?, 'OUT', ?, ?, ?, ?)",
                         (details["from_sku"], details["from_department"], qty, f"Approved by {reviewer}", f"Transfer #{decision_id}", now))
            conn.execute("INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp) VALUES (?, ?, 'IN', ?, ?, ?, ?)",
                         (details["to_sku"], details["to_department"], qty, f"Approved by {reviewer}", f"Transfer #{decision_id}", now))

        elif dtype == "PURCHASE_REQUEST":
            qty = float(details["recommended_purchase_qty"])
            conn.execute("UPDATE items SET book_quantity = book_quantity + ?, actual_quantity = actual_quantity + ? WHERE sku = ?",
                         (qty, qty, details["sku"]))
            conn.execute("INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp) VALUES (?, ?, 'IN', ?, ?, ?, ?)",
                         (details["sku"], details["department"], qty, f"Approved by {reviewer}", f"Purchase Request #{decision_id}", now))

        elif dtype == "DISPOSAL_REPORT":
            qty = float(details["expired_quantity"])
            conn.execute("DELETE FROM batches WHERE batch_code = ?", (details["batch_code"],))
            conn.execute("UPDATE items SET book_quantity = MAX(0, book_quantity - ?), actual_quantity = MAX(0, actual_quantity - ?) WHERE sku = ?",
                         (qty, qty, details["sku"]))
            conn.execute("INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp) VALUES (?, ?, 'OUT', ?, ?, ?, ?)",
                         (details["sku"], details["department"], qty, f"Approved by {reviewer}", f"Disposal #{decision_id}", now))

        elif dtype == "AUDIT_ALERT" and details.get("audit_type") == "INVENTORY_COUNT_DISCREPANCY":
            actual = float(details["actual_quantity"])
            conn.execute("UPDATE items SET book_quantity = ? WHERE sku = ?", (actual, details["sku"]))
            conn.execute("INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp) VALUES (?, ?, 'ADJUST', ?, ?, ?, ?)",
                         (details["sku"], details["department"], actual, f"Approved by {reviewer}", f"Audit Fix #{decision_id}", now))

    conn.execute("""
        UPDATE pending_decisions
        SET status = ?, reviewed_by = ?, reviewed_at = ?, reviewer_notes = ?
        WHERE id = ?
    """, (req.action, reviewer, now, req.notes.strip(), decision_id))
    conn.commit()
    conn.close()
    return {"status": req.action, "decision_id": decision_id, "reviewed_by": reviewer, "reviewed_at": now}

@app.post("/api/reset-demo")
def reset_demo_data():
    init_and_seed_db()
    conn = get_connection()
    _seed_users(conn)
    conn.close()
    return {"status": "reset_complete"}

@app.get("/api/export-report", response_class=PlainTextResponse)
def export_report():
    conn = get_connection()
    items = conn.execute("SELECT * FROM items ORDER BY department_code, sku").fetchall()
    if dept_scope == "ALL":
        decisions = conn.execute("SELECT * FROM pending_decisions ORDER BY id DESC").fetchall()
    else:
        decisions = conn.execute(
            "SELECT * FROM pending_decisions WHERE details_json LIKE ? OR title LIKE ? ORDER BY id DESC",
            (f"%{dept_scope}%", f"%{dept_scope}%")
        ).fetchall()
    logs = conn.execute("SELECT * FROM agent_execution_log ORDER BY id DESC").fetchall()
    conn.close()

    lines = [
        "====================================================================",
        "P09 - AUTONOMOUS INVENTORY TRACKING AGENT (N-TEAM) - AUDIT REPORT",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Local Model: {OLLAMA_MODEL}",
        "====================================================================\n",
        "1. INVENTORY SUMMARY (44 ITEMS ACROSS 4 DEPARTMENTS):",
    ]
    for i in items:
        lines.append(f"  [{i['department_code']}] {i['sku']} | {i['name']} | Book={i['book_quantity']} | Actual={i['actual_quantity']} {i['unit']} | Min={i['min_threshold']} | Shelf={i['shelf_location']}")

    lines.append("\n2. GOVERNANCE & HUMAN APPROVAL DECISIONS (02-NFR):")
    for d in decisions:
        lines.append(f"  #{d['id']} [{d['status']}] ({d['decision_type']}) {d['title']} | Reviewed By: {d['reviewed_by'] or 'PENDING'} at {d['reviewed_at'] or '-'}")

    lines.append("\n3. AGENT EXECUTION LOG (05-NFR):")
    for l in logs:
        lines.append(f"  [{l['timestamp']}] Session={l['session_id']} Step={l['step_number']} Tool={l['tool_name']} Status={l['status']} ({l['duration_ms']} ms)")

    return "\n".join(lines)
