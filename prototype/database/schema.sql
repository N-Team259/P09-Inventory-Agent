PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department_code TEXT NOT NULL,
    unit TEXT NOT NULL,
    book_quantity REAL NOT NULL DEFAULT 0,
    actual_quantity REAL NOT NULL DEFAULT 0,
    min_threshold REAL NOT NULL DEFAULT 5,
    max_capacity REAL NOT NULL DEFAULT 100,
    abc_class TEXT CHECK(abc_class IN ('A', 'B', 'C')) DEFAULT 'B',
    hazard_level TEXT CHECK(hazard_level IN ('NONE', 'FLAMMABLE', 'CHEMICAL', 'FRAGILE')) DEFAULT 'NONE',
    requires_cold_chain INTEGER NOT NULL DEFAULT 0,
    shelf_location TEXT NOT NULL,
    FOREIGN KEY (department_code) REFERENCES departments(code)
);

CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code TEXT UNIQUE NOT NULL,
    item_sku TEXT NOT NULL,
    department_code TEXT NOT NULL,
    quantity REAL NOT NULL,
    expiry_date TEXT NOT NULL,
    received_date TEXT NOT NULL,
    FOREIGN KEY (item_sku) REFERENCES items(sku),
    FOREIGN KEY (department_code) REFERENCES departments(code)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_sku TEXT NOT NULL,
    department_code TEXT NOT NULL,
    tx_type TEXT CHECK(tx_type IN ('IN', 'OUT', 'ADJUST')) NOT NULL,
    quantity REAL NOT NULL,
    requested_by TEXT NOT NULL,
    notes TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (item_sku) REFERENCES items(sku),
    FOREIGN KEY (department_code) REFERENCES departments(code)
);

CREATE TABLE IF NOT EXISTS academic_and_seasonal_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    department_code TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    demand_multiplier REAL NOT NULL DEFAULT 1.0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pending_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_type TEXT CHECK(decision_type IN ('TRANSFER_ORDER', 'PURCHASE_REQUEST', 'DISPOSAL_REPORT', 'AUDIT_ALERT', 'LAYOUT_PLAN')) NOT NULL,
    source_tool TEXT NOT NULL,
    title TEXT NOT NULL,
    details_json TEXT NOT NULL,
    status TEXT CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')) NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    reviewer_notes TEXT
);

CREATE TABLE IF NOT EXISTS agent_execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input TEXT NOT NULL,
    tool_output TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT CHECK(role IN ('MANAGER', 'OPERATOR')) NOT NULL,
    department_scope TEXT NOT NULL,
    title TEXT NOT NULL
);
