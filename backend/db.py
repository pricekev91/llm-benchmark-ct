# backend/db.py
import os
import sqlite3
import json
from typing import Optional, List, Dict, Any

DB_PATH = os.environ.get("DB_PATH", "/opt/ct/llm-benchmark/db/db.sqlite")
CONFIGS_DIR = os.environ.get("CONFIGS_DIR", "/opt/ct/llm-benchmark/configs")


def get_db_connection():
    """Establishes and returns a SQLite database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS endpoint_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            provider TEXT DEFAULT 'OpenAI',
            api_key TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            template TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            run_id TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            endpoint_id TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            response_text TEXT,
            latency_ms REAL,
            tokens_generated INTEGER,
            output_length INTEGER,
            throughput_tps REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            prompt_preset_id TEXT
        );
    """)

    conn.commit()
    conn.close()

    # Seed default presets if table is empty
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM prompt_presets")
    if cursor.fetchone()[0] == 0:
        presets = [
            ("preset_1", "Explain Quantum Computing",
             "Explain quantum computing in simple terms, as if to a 10-year-old.", "general"),
            ("preset_2", "Lonely Satellite Poem",
             "Write a short poem about a lonely satellite orbiting Earth at night.", "creative"),
            ("preset_3", "Debug Python Code",
             "Debug this Python code:\n\ndef fibonacci(n):\n    a, b = 0, 1\n    for i in range(n):\n        return a, b\n", "debugging"),
            ("preset_4", "SQL Query Generator",
             "Write a SQL query that finds the top 5 customers by total purchase amount from a 'customers' and 'orders' table.", "sql"),
            ("preset_5", "HTML Dashboard",
             "Generate a simple HTML dashboard with CSS showing three KPI cards: revenue, users, and conversion rate.", "html"),
            ("preset_6", "System Design",
             "Design a URL shortening service. Describe the API, data model, and scaling strategy.", "architecture"),
        ]
        cursor.executemany(
            "INSERT INTO prompt_presets (id, name, template, category) VALUES (?, ?, ?, ?)",
            presets
        )
        conn.commit()

    conn.close()
    print("Database initialized successfully.")
    return True


# --- Query Functions ---

def fetch_all_endpoints() -> List[Dict[str, Any]]:
    """Fetch all endpoint configurations from DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM endpoint_configs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_endpoint_by_id(endpoint_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single endpoint config by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM endpoint_configs WHERE id = ?", (endpoint_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_endpoint(endpoint: Dict[str, Any]) -> str:
    """Save or update an endpoint config. Returns the endpoint ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO endpoint_configs (id, name, base_url, provider, api_key) VALUES (?, ?, ?, ?, ?)",
        (endpoint["id"], endpoint["name"], endpoint["base_url"],
         endpoint.get("provider", "OpenAI"), endpoint.get("api_key", ""))
    )
    conn.commit()
    conn.close()
    print(f"Saved endpoint: {endpoint['name']} ({endpoint['base_url']})")
    return endpoint["id"]


def delete_endpoint(endpoint_id: str) -> bool:
    """Delete an endpoint config."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM endpoint_configs WHERE id = ?", (endpoint_id,))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def fetch_all_presets() -> List[Dict[str, Any]]:
    """Fetch all prompt presets from DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompt_presets ORDER BY category, name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_preset(preset: Dict[str, Any]) -> str:
    """Save a prompt preset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO prompt_presets (id, name, template, category) VALUES (?, ?, ?, ?)",
        (preset["id"], preset["name"], preset["template"],
         preset.get("category", "general"))
    )
    conn.commit()
    conn.close()
    return preset["id"]


def fetch_benchmark_runs(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetch benchmark runs with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM benchmark_runs WHERE 1=1"
    params = []

    if filters:
        if filters.get("model_name"):
            query += " AND model_name LIKE ?"
            params.append(f"%{filters['model_name']}%")
        if filters.get("endpoint_id"):
            query += " AND endpoint_id = ?"
            params.append(filters["endpoint_id"])
        if filters.get("start_date"):
            query += " AND timestamp >= ?"
            params.append(filters["start_date"])
        if filters.get("end_date"):
            query += " AND timestamp <= ?"
            params.append(filters["end_date"])

    query += " ORDER BY timestamp DESC"
    if filters and filters.get("limit"):
        query += " LIMIT ?"
        params.append(int(filters["limit"]))

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_benchmark_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single benchmark run by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM benchmark_runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_benchmark_run(run: Dict[str, Any]) -> str:
    """Persist a benchmark run to SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO benchmark_runs
        (run_id, model_name, endpoint_id, prompt_text, response_text,
         latency_ms, tokens_generated, output_length, throughput_tps,
         timestamp, prompt_preset_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run["run_id"], run["model_name"], run["endpoint_id"],
            run["prompt_text"], run.get("response_text", ""),
            run.get("latency_ms"), run.get("tokens_generated"),
            run.get("output_length"), run.get("throughput_tps"),
            run.get("timestamp"), run.get("prompt_preset_id")
        )
    )
    conn.commit()
    conn.close()
    print(f"Saved benchmark run: {run['run_id']}")
    return run["run_id"]


def fetch_comparison_stats(model_name: str) -> Dict[str, Any]:
    """Fetch comparison statistics for a model."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT COUNT(*) as total_runs,
                  AVG(latency_ms) as avg_latency,
                  MIN(latency_ms) as best_latency,
                  MAX(latency_ms) as worst_latency,
                  AVG(throughput_tps) as avg_throughput,
                  AVG(tokens_generated) as avg_tokens
           FROM benchmark_runs WHERE model_name = ?""",
        (model_name,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        data = dict(row)
        return {
            "model_name": model_name,
            "total_runs": data["total_runs"] or 0,
            "avg_latency_ms": round(data["avg_latency"], 2) if data["avg_latency"] else 0,
            "best_latency_ms": round(data["best_latency"], 2) if data["best_latency"] else 0,
            "worst_latency_ms": round(data["worst_latency"], 2) if data["worst_latency"] else 0,
            "avg_throughput_tps": round(data["avg_throughput"], 2) if data["avg_throughput"] else 0,
            "avg_tokens": round(data["avg_tokens"], 1) if data["avg_tokens"] else 0,
        }
    return {"model_name": model_name, "total_runs": 0}


def fetch_trends(model_name: str) -> List[Dict[str, Any]]:
    """Fetch latency trends grouped by date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT DATE(timestamp) as date,
                  COUNT(*) as runs,
                  ROUND(AVG(latency_ms), 2) as avg_latency,
                  ROUND(MIN(latency_ms), 2) as best_latency
           FROM benchmark_runs
           WHERE model_name = ?
           GROUP BY DATE(timestamp)
           ORDER BY date ASC
           LIMIT 30""",
        (model_name,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
