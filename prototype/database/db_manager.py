import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_and_seed_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # 1. الأقسام الأربعة المعتمدة في المحضر
    departments = [
        ("GEN_TRADE", "General Trade", "مخازن التجارة العامة والمستلزمات الأساسية"),
        ("ECOMMERCE", "E-commerce", "مخازن التجارة الإلكترونية والتغليف والشحن"),
        ("REFRIGERATION", "Refrigeration", "مخازن التبريد والمواد الحساسة للحرارة"),
        ("COMP_LABS", "Computer Labs", "مختبرات الحاسبات والعتاد الشبكي والبرمجي")
    ]
    conn.executemany("INSERT INTO departments (code, name, description) VALUES (?, ?, ?)", departments)

    # 2. بيانات مصطنعة (11 مادة لكل قسم = 44 مادة) تغطي جميع السيناريوهات
    items = [
        # --- القسم 1: التجارة العامة (GEN_TRADE) ---
        ("GT-001", "Cat6 Network Cable Roll (305m)", "GEN_TRADE", "roll", 28, 28, 5, 50, "A", "NONE", 0, "A1-S1"),
        ("GT-002", "A4 Printing Paper Box (5 Reams)", "GEN_TRADE", "box", 65, 65, 15, 100, "A", "NONE", 0, "A1-S2"),
        ("GT-003", "Industrial Cleaning Alcohol (5L)", "GEN_TRADE", "can", 18, 18, 5, 30, "B", "FLAMMABLE", 0, "A2-S1"),
        ("GT-004", "Heavy Duty Power Strip", "GEN_TRADE", "unit", 42, 42, 10, 60, "B", "NONE", 0, "A2-S2"),
        ("GT-005", "LED Panel Light 60x60", "GEN_TRADE", "unit", 35, 30, 8, 50, "B", "FRAGILE", 0, "A3-S1"),
        ("GT-006", "Thermal Receipt Paper Roll", "GEN_TRADE", "roll", 120, 120, 25, 200, "A", "NONE", 0, "A3-S2"),
        ("GT-007", "Safety Gloves Box (100 pcs)", "GEN_TRADE", "box", 40, 40, 10, 80, "C", "NONE", 0, "A4-S1"),
        ("GT-008", "Whiteboard Markers Pack", "GEN_TRADE", "pack", 55, 55, 12, 100, "C", "NONE", 0, "A4-S2"),
        ("GT-009", "Packaging Tape 48mm", "GEN_TRADE", "roll", 90, 90, 20, 150, "B", "NONE", 0, "A5-S1"),
        ("GT-010", "USB-C Docking Station", "GEN_TRADE", "unit", 22, 22, 4, 30, "A", "NONE", 0, "A5-S2"),
        ("GT-011", "Sodium Hypochlorite Disinfectant", "GEN_TRADE", "bottle", 14, 14, 5, 25, "C", "CHEMICAL", 0, "A1-S3"),

        # --- القسم 2: التجارة الإلكترونية (ECOMMERCE) ---
        ("EC-001", "Corrugated Shipping Box Medium", "ECOMMERCE", "unit", 140, 140, 200, 1000, "A", "NONE", 0, "B1-S1"),
        ("EC-002", "Bubble Wrap Roll (100m)", "ECOMMERCE", "roll", 12, 12, 20, 80, "A", "FLAMMABLE", 0, "B1-S2"),
        ("EC-003", "Barcode Shipping Labels (1000/roll)", "ECOMMERCE", "roll", 18, 18, 25, 100, "A", "NONE", 0, "B2-S1"),
        ("EC-004", "Tamper-Evident Courier Bags", "ECOMMERCE", "pack", 45, 45, 30, 150, "A", "NONE", 0, "B2-S2"),
        ("EC-005", "Handheld Barcode Scanner", "ECOMMERCE", "unit", 16, 11, 5, 25, "B", "FRAGILE", 0, "B3-S1"),
        ("EC-006", "Fragile Warning Stickers Roll", "ECOMMERCE", "roll", 34, 34, 10, 60, "C", "NONE", 0, "B3-S2"),
        ("EC-007", "Stretch Film Wrap Roll", "ECOMMERCE", "roll", 28, 28, 10, 50, "B", "NONE", 0, "B4-S1"),
        ("EC-008", "Digital Parcel Scale 50kg", "ECOMMERCE", "unit", 6, 6, 3, 10, "B", "FRAGILE", 0, "B4-S2"),
        ("EC-009", "Thermal Label Printer Ribbon", "ECOMMERCE", "roll", 22, 22, 8, 40, "B", "NONE", 0, "B5-S1"),
        ("EC-010", "Kraft Padded Mailers (50 pcs)", "ECOMMERCE", "pack", 60, 60, 15, 120, "B", "NONE", 0, "B5-S2"),
        ("EC-011", "Lithium Battery Warning Labels", "ECOMMERCE", "roll", 19, 19, 5, 30, "C", "NONE", 0, "B6-S1"),

        # --- القسم 3: التبريد (REFRIGERATION) ---
        ("RF-001", "Biological Reagent Kit A", "REFRIGERATION", "kit", 24, 24, 6, 40, "A", "CHEMICAL", 1, "C1-COLD"),
        ("RF-002", "Temperature-Sensitive Enzyme Vial", "REFRIGERATION", "vial", 50, 50, 10, 80, "A", "NONE", 1, "C1-COLD"),
        ("RF-003", "Cold Gel Ice Packs", "REFRIGERATION", "unit", 85, 85, 20, 150, "B", "NONE", 1, "C2-COLD"),
        ("RF-004", "Medical Grade Vaccine Carrier", "REFRIGERATION", "unit", 10, 10, 3, 15, "B", "FRAGILE", 1, "C2-COLD"),
        ("RF-005", "Dairy Culture Starter Pack", "REFRIGERATION", "pack", 30, 30, 8, 50, "A", "NONE", 1, "C3-COLD"),
        ("RF-006", "Digital Cold-Chain Data Logger", "REFRIGERATION", "unit", 14, 14, 4, 20, "A", "FRAGILE", 0, "C3-DRY"),
        ("RF-007", "Sterile Nutrient Agar Plates", "REFRIGERATION", "pack", 40, 40, 10, 60, "A", "NONE", 1, "C4-COLD"),
        ("RF-008", "R134a Refrigerant Gas Cylinder", "REFRIGERATION", "cylinder", 8, 6, 3, 15, "B", "FLAMMABLE", 0, "C4-DRY"),
        ("RF-009", "Insulated Thermal Box Liner", "REFRIGERATION", "unit", 45, 45, 12, 80, "C", "NONE", 0, "C5-DRY"),
        ("RF-010", "pH Calibration Buffer Solution", "REFRIGERATION", "bottle", 18, 18, 5, 30, "B", "CHEMICAL", 1, "C5-COLD"),
        ("RF-011", "Cryogenic Storage Vials (100/box)", "REFRIGERATION", "box", 20, 20, 5, 35, "C", "NONE", 1, "C6-COLD"),

        # --- القسم 4: مختبرات الحاسبات (COMP_LABS) ---
        ("CL-001", "Cat6 Network Cable Roll (305m)", "COMP_LABS", "roll", 2, 2, 6, 15, "A", "NONE", 0, "D1-S1"),
        ("CL-002", "NVMe SSD 512GB Storage Drive", "COMP_LABS", "unit", 4, 4, 10, 30, "A", "FRAGILE", 0, "D1-S2"),
        ("CL-003", "RJ45 Modular Connectors (100/pack)", "COMP_LABS", "pack", 15, 15, 5, 40, "A", "NONE", 0, "D2-S1"),
        ("CL-004", "DDR4 16GB RAM Module", "COMP_LABS", "unit", 12, 9, 5, 25, "A", "FRAGILE", 0, "D2-S2"),
        ("CL-005", "Crimping Tool Kit", "COMP_LABS", "kit", 18, 18, 6, 25, "B", "NONE", 0, "D3-S1"),
        ("CL-006", "Arduino Uno R3 Microcontroller", "COMP_LABS", "unit", 32, 32, 10, 50, "A", "FRAGILE", 0, "D3-S2"),
        ("CL-007", "Raspberry Pi 4 Model B (4GB)", "COMP_LABS", "unit", 14, 14, 5, 25, "A", "FRAGILE", 0, "D4-S1"),
        ("CL-008", "USB-C Docking Station", "COMP_LABS", "unit", 2, 2, 5, 15, "B", "NONE", 0, "D4-S2"),
        ("CL-009", "Isopropyl Alcohol 99% Electronics Cleaner", "COMP_LABS", "bottle", 9, 9, 4, 20, "B", "FLAMMABLE", 0, "D1-S1"),
        ("CL-010", "HDMI to VGA Active Adapter", "COMP_LABS", "unit", 25, 25, 8, 40, "C", "NONE", 0, "D5-S1"),
        ("CL-011", "24-Port Gigabit Network Switch", "COMP_LABS", "unit", 5, 5, 2, 10, "B", "FRAGILE", 0, "D5-S2"),
    ]
    conn.executemany("""
        INSERT INTO items (
            sku, name, department_code, unit, book_quantity, actual_quantity,
            min_threshold, max_capacity, abc_class, hazard_level, requires_cold_chain, shelf_location
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, items)

    # 3. دفعات الصلاحية (FEFO) لاختبار حارس الصلاحية وسلسلة التبريد
    today = datetime(2026, 11, 13)
    batches = [
        ("BCH-RF01-A", "RF-001", "REFRIGERATION", 10, (today + timedelta(days=5)).strftime("%Y-%m-%d"), "2026-08-01"),
        ("BCH-RF01-B", "RF-001", "REFRIGERATION", 14, (today + timedelta(days=90)).strftime("%Y-%m-%d"), "2026-10-15"),
        ("BCH-RF02-A", "RF-002", "REFRIGERATION", 35, (today + timedelta(days=8)).strftime("%Y-%m-%d"), "2026-07-10"),
        ("BCH-RF02-B", "RF-002", "REFRIGERATION", 15, (today + timedelta(days=120)).strftime("%Y-%m-%d"), "2026-10-20"),
        ("BCH-RF07-A", "RF-007", "REFRIGERATION", 25, (today - timedelta(days=2)).strftime("%Y-%m-%d"), "2026-06-01"),
        ("BCH-RF07-B", "RF-007", "REFRIGERATION", 15, (today + timedelta(days=60)).strftime("%Y-%m-%d"), "2026-10-01"),
        ("BCH-GT11-A", "GT-011", "GEN_TRADE", 14, (today + timedelta(days=12)).strftime("%Y-%m-%d"), "2026-05-12"),
    ]
    conn.executemany("""
        INSERT INTO batches (batch_code, item_sku, department_code, quantity, expiry_date, received_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, batches)

    # 4. سجلات حركات السحب (تتضمن استهلاكاً طبيعياً + سحوبات شاذة لكشفها بالتدقيق الجنائي)
    txs = [
        ("CL-001", "COMP_LABS", "OUT", 2, "Lab Supervisor", "Weekly networking lab", "2026-10-15 10:00:00"),
        ("CL-001", "COMP_LABS", "OUT", 2, "Lab Supervisor", "Weekly networking lab", "2026-10-22 10:30:00"),
        ("CL-001", "COMP_LABS", "OUT", 3, "Lab Supervisor", "Midterm lab prep", "2026-10-29 11:00:00"),
        ("CL-002", "COMP_LABS", "OUT", 3, "Lab Technician", "OS installation lab", "2026-10-20 09:15:00"),
        ("CL-002", "COMP_LABS", "OUT", 4, "Lab Technician", "Database lab setup", "2026-11-01 12:00:00"),
        ("CL-004", "COMP_LABS", "OUT", 1, "Lab Technician", "PC upgrade", "2026-10-25 13:00:00"),
        ("CL-004", "COMP_LABS", "OUT", 9, "Unknown_User", "Unverified after-hours withdrawal", "2026-11-11 23:40:00"),
        ("EC-001", "ECOMMERCE", "OUT", 80, "Packing Team", "Daily orders dispatch", "2026-11-05 14:00:00"),
        ("EC-001", "ECOMMERCE", "OUT", 95, "Packing Team", "Daily orders dispatch", "2026-11-08 15:00:00"),
        ("EC-005", "ECOMMERCE", "OUT", 1, "Shift Lead", "Scanner replacement", "2026-10-18 11:20:00"),
        ("EC-005", "ECOMMERCE", "OUT", 7, "Temp_Staff", "Bulk removal without ticket", "2026-11-10 22:15:00"),
        ("RF-001", "REFRIGERATION", "OUT", 1, "Bio Lab Tech", "Routine test", "2026-11-02 09:00:00"),
        ("RF-002", "REFRIGERATION", "OUT", 2, "Bio Lab Tech", "Routine test", "2026-11-06 10:00:00"),
    ]
    conn.executemany("""
        INSERT INTO transactions (item_sku, department_code, tx_type, quantity, requested_by, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, txs)

    # 5. التقويم الأكاديمي والمواسم
    events = [
        ("Practical Final Exams - Computer Labs", "COMP_LABS", "2026-11-20", "2026-12-10", 2.5, "ارتفاع استهلاك كابلات الشبكة وأقراص التخزين"),
        ("White Friday & Year-End E-commerce Sale", "ECOMMERCE", "2026-11-25", "2026-12-05", 3.0, "تضاعف طلبات الشحن والتغليف 3 أضعاف"),
        ("Winter Cold-Chain Calibration Period", "REFRIGERATION", "2026-12-01", "2026-12-20", 1.4, "فحوصات دورية للمواد المبردة"),
    ]
    conn.executemany("""
        INSERT INTO academic_and_seasonal_events (event_name, department_code, start_date, end_date, demand_multiplier, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, events)

    conn.commit()
    conn.close()
    print("✅ تم إنشاء قاعدة البيانات وتعبئتها بـ 44 مادة للأقسام الأربعة بنجاح!")

if __name__ == "__main__":
    init_and_seed_db()
