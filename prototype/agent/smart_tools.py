import json
from datetime import datetime
from database.db_manager import get_connection

VALID_DEPARTMENTS = {"GEN_TRADE", "ECOMMERCE", "REFRIGERATION", "COMP_LABS"}
DEPT_ALIASES = {
    "general trade": "GEN_TRADE", "التجارة العامة": "GEN_TRADE", "gen_trade": "GEN_TRADE",
    "e-commerce": "ECOMMERCE", "ecommerce": "ECOMMERCE", "التجارة الإلكترونية": "ECOMMERCE", "التجارة الالكترونية": "ECOMMERCE",
    "refrigeration": "REFRIGERATION", "التبريد": "REFRIGERATION", "cold": "REFRIGERATION",
    "computer labs": "COMP_LABS", "comp_labs": "COMP_LABS", "مختبرات الحاسبات": "COMP_LABS", "المختبر": "COMP_LABS"
}

def _normalize_dept(dept: str) -> str | None:
    if not dept:
        return None
    key = dept.strip().lower()
    if dept.strip().upper() in VALID_DEPARTMENTS:
        return dept.strip().upper()
    return DEPT_ALIASES.get(key)

def _save_pending_decision(conn, decision_type: str, source_tool: str, title: str, details: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute("""
        INSERT INTO pending_decisions (decision_type, source_tool, title, details_json, status, created_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?)
    """, (decision_type, source_tool, title, json.dumps(details, ensure_ascii=False), now))
    conn.commit()
    return cur.lastrowid

# ==============================================================================
# 1. أداة الموازنة الذكية والمناقلة البينية
# ==============================================================================
def smart_cross_inventory_balancer(target_department: str, item_keyword: str = "") -> str:
    """
    Checks inventory across all 4 departments to detect shortages in target_department
    and surplus in other departments, creating a draft TRANSFER_ORDER for human approval.
    """
    dept_code = _normalize_dept(target_department)
    if not dept_code:
        return json.dumps({
            "error": "01-NFR Validation Error: Invalid or missing 'target_department'.",
            "how_to_fix": "Specify one of: GEN_TRADE (General Trade), ECOMMERCE (E-commerce), REFRIGERATION (Refrigeration), or COMP_LABS (Computer Labs)."
        }, ensure_ascii=False)

    conn = get_connection()
    query = "SELECT * FROM items WHERE department_code = ?"
    params = [dept_code]
    if item_keyword.strip():
        query += " AND (name LIKE ? OR sku LIKE ?)"
        params.extend([f"%{item_keyword.strip()}%", f"%{item_keyword.strip()}%"])

    target_items = conn.execute(query, params).fetchall()
    if not target_items:
        conn.close()
        return json.dumps({
            "error": f"01-NFR Validation Error: No matching items found in {dept_code} for keyword '{item_keyword}'.",
            "how_to_fix": "Verify the item name or SKU and try again."
        }, ensure_ascii=False)

    proposals = []
    shortages_without_surplus = []

    for item in target_items:
        deficit = max(0, (item["min_threshold"] * 1.5) - item["actual_quantity"])
        if item["actual_quantity"] <= item["min_threshold"]:
            needed = round(deficit if deficit > 0 else item["min_threshold"], 2)
            # البحث عن فائض لنفس المادة بالاسم في الأقسام الأخرى
            donors = conn.execute("""
                SELECT * FROM items
                WHERE name = ? AND department_code != ? AND actual_quantity > (min_threshold * 1.5)
            """, (item["name"], dept_code)).fetchall()

            transferred = 0
            for d in donors:
                available_surplus = d["actual_quantity"] - (d["min_threshold"] * 1.5)
                transfer_qty = round(min(needed - transferred, available_surplus), 2)
                if transfer_qty > 0:
                    details = {
                        "item_name": item["name"],
                        "from_department": d["department_code"],
                        "from_sku": d["sku"],
                        "donor_current_qty": d["actual_quantity"],
                        "to_department": dept_code,
                        "to_sku": item["sku"],
                        "target_current_qty": item["actual_quantity"],
                        "transfer_quantity": transfer_qty,
                        "unit": item["unit"]
                    }
                    dec_id = _save_pending_decision(
                        conn,
                        "TRANSFER_ORDER",
                        "smart_cross_inventory_balancer",
                        f"Transfer {transfer_qty} {item['unit']} of {item['name']} ({d['department_code']} -> {dept_code})",
                        details
                    )
                    details["pending_decision_id"] = dec_id
                    proposals.append(details)
                    transferred += transfer_qty

            if transferred < needed:
                shortages_without_surplus.append({
                    "sku": item["sku"],
                    "name": item["name"],
                    "current_qty": item["actual_quantity"],
                    "min_threshold": item["min_threshold"],
                    "remaining_deficit": round(needed - transferred, 2)
                })

    conn.close()
    return json.dumps({
        "tool": "smart_cross_inventory_balancer",
        "department_analyzed": dept_code,
        "draft_transfer_orders_created": proposals,
        "unfulfilled_shortages_needing_purchase": shortages_without_surplus,
        "note": "No inventory balances were modified directly. Drafts await Human Manager approval (02-NFR)."
    }, ensure_ascii=False)


# ==============================================================================
# 2. أداة التنبؤ السياقي ومحاكاة السيناريوهات
# ==============================================================================
def contextual_forecaster_and_simulator(department: str, item_keyword: str = "", horizon_days: int = 30, demand_multiplier_override: float = 0.0) -> str:
    """
    Forecasts future consumption using historical withdrawals + academic/seasonal calendar,
    supports what-if simulation (demand_multiplier_override), and drafts a PURCHASE_REQUEST if deficit is projected.
    """
    dept_code = _normalize_dept(department)
    if not dept_code:
        return json.dumps({
            "error": "01-NFR Validation Error: Invalid or missing 'department'.",
            "how_to_fix": "Provide GEN_TRADE, ECOMMERCE, REFRIGERATION, or COMP_LABS."
        }, ensure_ascii=False)

    if horizon_days <= 0 or horizon_days > 365:
        return json.dumps({
            "error": "01-NFR Validation Error: 'horizon_days' must be between 1 and 365.",
            "how_to_fix": "Pass a valid positive integer for forecast days (e.g., 30)."
        }, ensure_ascii=False)

    conn = get_connection()
    events = conn.execute("SELECT * FROM academic_and_seasonal_events WHERE department_code = ?", (dept_code,)).fetchall()
    calendar_multiplier = max([e["demand_multiplier"] for e in events], default=1.0)
    active_multiplier = demand_multiplier_override if demand_multiplier_override > 0 else calendar_multiplier

    query = "SELECT * FROM items WHERE department_code = ?"
    params = [dept_code]
    if item_keyword.strip():
        query += " AND (name LIKE ? OR sku LIKE ?)"
        params.extend([f"%{item_keyword.strip()}%", f"%{item_keyword.strip()}%"])

    items = conn.execute(query, params).fetchall()
    if not items:
        conn.close()
        return json.dumps({
            "error": f"01-NFR Validation Error: No items matched '{item_keyword}' in {dept_code}.",
            "how_to_fix": "Check the item name or SKU."
        }, ensure_ascii=False)

    forecasts = []
    purchase_drafts = []

    for item in items:
        tx_row = conn.execute("""
            SELECT COALESCE(SUM(quantity), 0) AS total_out
            FROM transactions WHERE item_sku = ? AND tx_type = 'OUT'
        """, (item["sku"],)).fetchone()
        base_30d_usage = tx_row["total_out"] if tx_row["total_out"] > 0 else (item["min_threshold"] * 0.5)
        daily_rate = (base_30d_usage / 30.0) * active_multiplier
        projected_demand = round(daily_rate * horizon_days, 2)
        projected_ending_stock = round(item["actual_quantity"] - projected_demand, 2)

        item_forecast = {
            "sku": item["sku"],
            "name": item["name"],
            "current_actual_qty": item["actual_quantity"],
            "base_30d_historical_out": base_30d_usage,
            "applied_multiplier": active_multiplier,
            "projected_demand": projected_demand,
            "projected_ending_stock": projected_ending_stock
        }
        forecasts.append(item_forecast)

        if projected_ending_stock < item["min_threshold"]:
            order_qty = round((item["min_threshold"] - projected_ending_stock) + (daily_rate * 7), 2)
            details = {
                "department": dept_code,
                "sku": item["sku"],
                "item_name": item["name"],
                "current_stock": item["actual_quantity"],
                "projected_demand": projected_demand,
                "recommended_purchase_qty": order_qty,
                "unit": item["unit"],
                "reason": f"Projected deficit within {horizon_days} days (multiplier={active_multiplier}x)"
            }
            dec_id = _save_pending_decision(
                conn,
                "PURCHASE_REQUEST",
                "contextual_forecaster_and_simulator",
                f"Purchase {order_qty} {item['unit']} of {item['name']} for {dept_code}",
                details
            )
            details["pending_decision_id"] = dec_id
            purchase_drafts.append(details)

    conn.close()
    return json.dumps({
        "tool": "contextual_forecaster_and_simulator",
        "department": dept_code,
        "horizon_days": horizon_days,
        "calendar_events_detected": [dict(e) for e in events],
        "applied_demand_multiplier": active_multiplier,
        "forecasts": forecasts,
        "draft_purchase_requests_created": purchase_drafts
    }, ensure_ascii=False)


# ==============================================================================
# 3. أداة التدقيق الجنائي وكشف فجوات السحب
# ==============================================================================
def anomaly_and_audit_investigator(department: str = "") -> str:
    """
    Audits inventory records to detect discrepancies between book_quantity and actual_quantity,
    as well as abnormal/after-hours withdrawal spikes, issuing AUDIT_ALERT drafts.
    """
    dept_code = _normalize_dept(department) if department.strip() else None
    if department.strip() and not dept_code:
        return json.dumps({
            "error": "01-NFR Validation Error: Invalid 'department' filter.",
            "how_to_fix": "Leave empty to audit all departments, or use GEN_TRADE, ECOMMERCE, REFRIGERATION, or COMP_LABS."
        }, ensure_ascii=False)

    conn = get_connection()
    item_sql = "SELECT * FROM items WHERE book_quantity != actual_quantity"
    params = []
    if dept_code:
        item_sql += " AND department_code = ?"
        params.append(dept_code)

    discrepancies = conn.execute(item_sql, params).fetchall()
    alerts_created = []

    for d in discrepancies:
        gap = round(d["actual_quantity"] - d["book_quantity"], 2)
        details = {
            "audit_type": "INVENTORY_COUNT_DISCREPANCY",
            "department": d["department_code"],
            "sku": d["sku"],
            "item_name": d["name"],
            "book_quantity": d["book_quantity"],
            "actual_quantity": d["actual_quantity"],
            "variance": gap,
            "shelf_location": d["shelf_location"]
        }
        dec_id = _save_pending_decision(
            conn,
            "AUDIT_ALERT",
            "anomaly_and_audit_investigator",
            f"Stock Discrepancy on {d['sku']} ({d['name']}): Book={d['book_quantity']} vs Actual={d['actual_quantity']}",
            details
        )
        details["pending_decision_id"] = dec_id
        alerts_created.append(details)

    # كشف السحوبات الشاذة (كمية تتجاوز 3 أضعاف المتوسط أو سحب ليلي متأخر)
    tx_sql = "SELECT * FROM transactions WHERE tx_type = 'OUT'"
    if dept_code:
        tx_sql += " AND department_code = ?"
    txs = conn.execute(tx_sql, params).fetchall()

    by_sku = {}
    for t in txs:
        by_sku.setdefault(t["item_sku"], []).append(t)

    anomalous_withdrawals = []
    for sku, rows in by_sku.items():
        avg_qty = sum(r["quantity"] for r in rows) / len(rows)
        for r in rows:
            hour = int(r["timestamp"].split(" ")[1].split(":")[0])
            is_after_hours = hour >= 21 or hour <= 5
            is_spike = len(rows) > 1 and r["quantity"] > (avg_qty * 1.8)
            if is_after_hours or is_spike:
                details = {
                    "audit_type": "ANOMALOUS_WITHDRAWAL",
                    "transaction_id": r["id"],
                    "department": r["department_code"],
                    "sku": sku,
                    "withdrawn_qty": r["quantity"],
                    "historical_avg_qty": round(avg_qty, 2),
                    "requested_by": r["requested_by"],
                    "timestamp": r["timestamp"],
                    "notes": r["notes"],
                    "flags": [f for f in ["AFTER_HOURS_ACCESS" if is_after_hours else None, "QUANTITY_SPIKE" if is_spike else None] if f]
                }
                dec_id = _save_pending_decision(
                    conn,
                    "AUDIT_ALERT",
                    "anomaly_and_audit_investigator",
                    f"Suspicious Withdrawal on {sku}: {r['quantity']} units by {r['requested_by']} at {r['timestamp']}",
                    details
                )
                details["pending_decision_id"] = dec_id
                anomalous_withdrawals.append(details)

    conn.close()
    return json.dumps({
        "tool": "anomaly_and_audit_investigator",
        "scope": dept_code or "ALL_DEPARTMENTS",
        "book_vs_actual_discrepancies": alerts_created,
        "anomalous_withdrawals_detected": anomalous_withdrawals
    }, ensure_ascii=False)


# ==============================================================================
# 4. حارس الصلاحية وسلسلة التبريد (FEFO & Waste Prevention)
# ==============================================================================
def perishability_and_cold_chain_guardian(warning_days: int = 15) -> str:
    """
    Tracks batch expiration dates using FEFO (First-Expired, First-Out), calculates projected
    unavoidable waste based on consumption rate, and creates DISPOSAL_REPORT drafts for expired stock.
    """
    if warning_days < 0 or warning_days > 365:
        return json.dumps({
            "error": "01-NFR Validation Error: 'warning_days' must be between 0 and 365.",
            "how_to_fix": "Provide a valid number of days (default is 15)."
        }, ensure_ascii=False)

    conn = get_connection()
    today = datetime(2026, 11, 13)
    batches = conn.execute("""
        SELECT b.*, i.name AS item_name, i.unit, i.requires_cold_chain
        FROM batches b
        JOIN items i ON b.item_sku = i.sku
        ORDER BY b.expiry_date ASC
    """).fetchall()

    fefo_schedule = []
    disposal_drafts = []
    urgent_clearance = []

    for b in batches:
        exp_date = datetime.strptime(b["expiry_date"], "%Y-%m-%d")
        days_left = (exp_date - today).days

        # حساب سرعة الاستهلاك اليومية
        out_row = conn.execute("""
            SELECT COALESCE(SUM(quantity), 0) AS total_out FROM transactions
            WHERE item_sku = ? AND tx_type = 'OUT'
        """, (b["item_sku"],)).fetchone()
        daily_consumption = max(out_row["total_out"] / 30.0, 0.2)

        entry = {
            "batch_code": b["batch_code"],
            "sku": b["item_sku"],
            "item_name": b["item_name"],
            "department": b["department_code"],
            "quantity": b["quantity"],
            "unit": b["unit"],
            "expiry_date": b["expiry_date"],
            "days_remaining": days_left,
            "cold_chain_required": bool(b["requires_cold_chain"])
        }
        fefo_schedule.append(entry)

        if days_left < 0:
            details = {
                "batch_code": b["batch_code"],
                "sku": b["item_sku"],
                "item_name": b["item_name"],
                "department": b["department_code"],
                "expired_quantity": b["quantity"],
                "unit": b["unit"],
                "expiry_date": b["expiry_date"],
                "days_overdue": abs(days_left)
            }
            dec_id = _save_pending_decision(
                conn,
                "DISPOSAL_REPORT",
                "perishability_and_cold_chain_guardian",
                f"Dispose Expired Batch {b['batch_code']} ({b['item_name']} - {b['quantity']} {b['unit']})",
                details
            )
            details["pending_decision_id"] = dec_id
            disposal_drafts.append(details)
        elif days_left <= warning_days:
            consumable_before_expiry = round(daily_consumption * days_left, 2)
            projected_waste = round(max(0, b["quantity"] - consumable_before_expiry), 2)
            entry["estimated_daily_usage"] = round(daily_consumption, 2)
            entry["projected_waste_if_unacted"] = projected_waste
            entry["action"] = "URGENT_FEFO_DISPATCH_OR_REDISTRIBUTION"
            urgent_clearance.append(entry)

    conn.close()
    return json.dumps({
        "tool": "perishability_and_cold_chain_guardian",
        "reference_date": today.strftime("%Y-%m-%d"),
        "fefo_priority_queue": fefo_schedule,
        "expired_batches_disposal_drafts": disposal_drafts,
        "at_risk_batches_urgent_clearance": urgent_clearance
    }, ensure_ascii=False)


# ==============================================================================
# 5. أداة التخطيط المكاني وقيود السلامة (ABC + Hazard + Cold Chain)
# ==============================================================================
def safety_and_layout_optimizer(department: str) -> str:
    """
    Audits shelf layout for safety violations (flammables/chemicals stored improperly,
    cold-chain items outside cold shelves) and optimizes placement using ABC turnover classification.
    """
    dept_code = _normalize_dept(department)
    if not dept_code:
        return json.dumps({
            "error": "01-NFR Validation Error: Invalid or missing 'department'.",
            "how_to_fix": "Specify GEN_TRADE, ECOMMERCE, REFRIGERATION, or COMP_LABS."
        }, ensure_ascii=False)

    conn = get_connection()
    items = conn.execute("SELECT * FROM items WHERE department_code = ?", (dept_code,)).fetchall()
    if not items:
        conn.close()
        return json.dumps({"error": f"No items found in {dept_code}."})

    violations = []
    recommendations = []

    # تجميع المواد حسب الرف لاكتشاف تعارض المواد الخطرة
    shelf_map = {}
    for item in items:
        shelf_map.setdefault(item["shelf_location"], []).append(item)

    for shelf, shelf_items in shelf_map.items():
        hazards = {i["hazard_level"] for i in shelf_items}
        if "FLAMMABLE" in hazards and len(shelf_items) > 1:
            violations.append({
                "shelf": shelf,
                "severity": "HIGH_SAFETY_RISK",
                "issue": "Flammable material stored on the same shelf with general/electronic items.",
                "items_involved": [f"{i['sku']} ({i['name']} - {i['hazard_level']})" for i in shelf_items],
                "recommended_fix": f"Isolate flammable item to dedicated HAZMAT-FLAM cabinet."
            })
        if "CHEMICAL" in hazards and "FRAGILE" in hazards:
            violations.append({
                "shelf": shelf,
                "severity": "MEDIUM_SAFETY_RISK",
                "issue": "Chemical substances stored alongside fragile items.",
                "items_involved": [f"{i['sku']} ({i['name']})" for i in shelf_items],
                "recommended_fix": "Move chemicals to lower spill-containment shelf."
            })

    for item in items:
        if item["requires_cold_chain"] == 1 and "COLD" not in item["shelf_location"].upper():
            violations.append({
                "shelf": item["shelf_location"],
                "severity": "CRITICAL_COLD_CHAIN_VIOLATION",
                "issue": f"Cold-chain item {item['sku']} ({item['name']}) is not in a refrigerated zone.",
                "recommended_fix": "Relocate immediately to C-COLD zone (2°C - 8°C)."
            })

        # توصية ABC
        zone_hint = "Golden Zone (Eye-level, near dispatch)" if item["abc_class"] == "A" else (
            "Middle Zone (Standard access)" if item["abc_class"] == "B" else "Upper/Back Zone (Low turnover)"
        )
        recommendations.append({
            "sku": item["sku"],
            "name": item["name"],
            "abc_class": item["abc_class"],
            "hazard_level": item["hazard_level"],
            "current_shelf": item["shelf_location"],
            "optimal_zone": zone_hint,
            "optimal_stock_range": f"{item['min_threshold']} - {item['max_capacity']} {item['unit']}"
        })

    dec_id = None
    if violations:
        dec_id = _save_pending_decision(
            conn,
            "LAYOUT_PLAN",
            "safety_and_layout_optimizer",
            f"Safety & ABC Layout Optimization Plan for {dept_code} ({len(violations)} violations)",
            {"department": dept_code, "violations": violations, "recommendations": recommendations}
        )

    conn.close()
    return json.dumps({
        "tool": "safety_and_layout_optimizer",
        "department": dept_code,
        "safety_violations_detected": violations,
        "pending_decision_id": dec_id,
        "abc_layout_map": recommendations
    }, ensure_ascii=False)

ALL_SMART_TOOLS = [
    smart_cross_inventory_balancer,
    contextual_forecaster_and_simulator,
    anomaly_and_audit_investigator,
    perishability_and_cold_chain_guardian,
    safety_and_layout_optimizer
]
