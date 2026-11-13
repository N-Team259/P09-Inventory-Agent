PRAGMA foreign_keys = ON;

-- 1. جدول المخازن أو الأقسام
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    location TEXT
);

-- 2. جدول الأصناف والمواد
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    min_threshold INTEGER NOT NULL DEFAULT 5,
    warehouse_id INTEGER,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE SET NULL
);

-- 3. جدول سجل الحركات (إدخال / إخراج / تعديل)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('IN', 'OUT', 'ADJUST')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    notes TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);
