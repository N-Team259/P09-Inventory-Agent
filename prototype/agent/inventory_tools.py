from typing import Optional
from database.db_manager import get_connection

def add_warehouse(name: str, location: str = "") -> dict:
    """إضافة مخزن أو قسم جديد إلى قاعدة البيانات."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO warehouses (name, location) VALUES (?, ?)",
                (name.strip(), location.strip())
            )
            return {"status": "success", "warehouse_id": cursor.lastrowid, "name": name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def add_item(name: str, sku: str = "", category: str = "General", quantity: int = 0, min_threshold: int = 5, warehouse_id: Optional[int] = None) -> dict:
    """إضافة صنف أو مادة جديدة إلى المخزن."""
    try:
        sku_val = sku.strip() if sku and sku.strip() else None
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO items (sku, name, category, quantity, min_threshold, warehouse_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sku_val, name.strip(), category.strip(), quantity, min_threshold, warehouse_id)
            )
            item_id = cursor.lastrowid
            if quantity > 0:
                conn.execute(
                    "INSERT INTO transactions (item_id, type, quantity, notes) VALUES (?, 'IN', ?, 'Initial stock')",
                    (item_id, quantity)
                )
            return {"status": "success", "item_id": item_id, "name": name, "quantity": quantity}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def record_transaction(item_id: int, trans_type: str, quantity: int, notes: str = "") -> dict:
    """تسجيل حركة مخزنية: 'IN' للإدخال، 'OUT' للصرف/الإخراج، 'ADJUST' للتسوية."""
    trans_type = trans_type.upper().strip()
    if trans_type not in ("IN", "OUT", "ADJUST"):
        return {"status": "error", "message": "نوع الحركة يجب أن يكون IN أو OUT أو ADJUST"}
    if quantity <= 0 and trans_type != "ADJUST":
        return {"status": "error", "message": "الكمية يجب أن تكون أكبر من صفر"}

    try:
        with get_connection() as conn:
            item = conn.execute("SELECT id, name, quantity FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return {"status": "error", "message": f"الصنف برقم {item_id} غير موجود"}

            current_qty = item["quantity"]
            if trans_type == "IN":
                new_qty = current_qty + quantity
            elif trans_type == "OUT":
                if current_qty < quantity:
                    return {"status": "error", "message": f"الرصيد غير كافٍ. المتوفر حالياً: {current_qty}"}
                new_qty = current_qty - quantity
            else:
                new_qty = quantity

            conn.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_qty, item_id))
            conn.execute(
                "INSERT INTO transactions (item_id, type, quantity, notes) VALUES (?, ?, ?, ?)",
                (item_id, trans_type, quantity if quantity > 0 else 1, notes)
            )
            return {
                "status": "success",
                "item": item["name"],
                "previous_quantity": current_qty,
                "new_quantity": new_qty
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_inventory(search: str = "") -> list[dict]:
    """جلب قائمة الأصناف الموجودة في المخازن مع إمكانية البحث بالاسم أو الرمز."""
    with get_connection() as conn:
        query = """
            SELECT i.id, i.sku, i.name, i.category, i.quantity, i.min_threshold,
                   COALESCE(w.name, 'غير محدد') AS warehouse
            FROM items i
            LEFT JOIN warehouses w ON i.warehouse_id = w.id
        """
        if search.strip():
            query += " WHERE i.name LIKE ? OR i.sku LIKE ? OR i.category LIKE ?"
            term = f"%{search.strip()}%"
            rows = conn.execute(query, (term, term, term)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

def get_low_stock_items() -> list[dict]:
    """جلب قائمة الأصناف التي وصلت كميتها إلى حد إعادة الطلب أو أقل."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT i.id, i.sku, i.name, i.quantity, i.min_threshold,
                      COALESCE(w.name, 'غير محدد') AS warehouse
               FROM items i
               LEFT JOIN warehouses w ON i.warehouse_id = w.id
               WHERE i.quantity <= i.min_threshold"""
        ).fetchall()
        return [dict(row) for row in rows]

def get_warehouses() -> list[dict]:
    """جلب جميع المخازن والأقسام المسجلة."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, location FROM warehouses").fetchall()
        return [dict(row) for row in rows]
