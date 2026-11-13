import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

def get_connection() -> sqlite3.Connection:
    """إنشاء اتصال بقاعدة البيانات مع تفعيل المفاتيح الأجنبية وإرجاع النتائج كقاموس."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """بناء الجداول الفارغة من ملف schema.sql."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with get_connection() as conn:
        conn.executescript(schema_sql)
    print(f"✅ تم إنشاء قاعدة البيانات الفارغة بنجاح في: {DB_PATH}")

if __name__ == "__main__":
    init_db()
