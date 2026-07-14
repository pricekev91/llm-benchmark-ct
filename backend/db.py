# backend/db.py
import sqlite3
from typing import Optional

DB_PATH = "/opt/ct/llm-benchmark/db/db.sqlite"

def get_db_connection():
    """Establishes and returns a SQLite database connection."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def initialize_database():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    # 1. Endpoint Configs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS endpoint_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL
        );
    """)

    # 2. Prompt Presets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            template TEXT NOT NULL
        );
    """)
    
    # 3. Benchmark Runs Table
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            prompt_preset_id TEXT -- Link to PromptPreset
        );
    """)
    
    conn.commit()
    conn.close()
    print("Database schema initialized successfully (Endpoints, Presets, Runs).")
    return True

# Run initialization when the application starts (handled in main.py startup event)
# initialize_database()