"""
SQLite database module for llm-benchmark-ct.

Provides:
- Schema initialization
- Insert functions for bench_runs and prompt_runs
- Query functions for results and comparison
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Database Path
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "db")
DB_PATH = os.path.join(DB_DIR, "benchmark.db")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bench_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine TEXT NOT NULL,
    model TEXT NOT NULL,
    model_path TEXT,
    tok_s REAL,
    context_size INTEGER,
    prompt_tokens INTEGER,
    generated_tokens INTEGER,
    eval_ms REAL,
    prompt_eval_ms REAL,
    latency_ms REAL,
    benchmark_source TEXT DEFAULT 'api',
    timestamp TEXT NOT NULL,
    raw_data TEXT  -- JSON dump of full result
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_path TEXT,
    prompt TEXT,
    response TEXT,
    latency_ms REAL,
    output_tokens INTEGER,
    prompt_tokens INTEGER,
    total_tokens INTEGER,
    tokens_per_second REAL,
    timestamp TEXT NOT NULL,
    raw_data TEXT  -- JSON dump of full result
);

CREATE INDEX IF NOT EXISTS idx_bench_engine ON bench_runs(engine);
CREATE INDEX IF NOT EXISTS idx_bench_model ON bench_runs(model);
CREATE INDEX IF NOT EXISTS idx_bench_ts ON bench_runs(timestamp);

CREATE INDEX IF NOT EXISTS idx_prompt_engine ON prompt_runs(engine);
CREATE INDEX IF NOT EXISTS idx_prompt_model ON prompt_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_prompt_ts ON prompt_runs(timestamp);
"""


# ---------------------------------------------------------------------------
# Connection Helper
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the DB if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = _get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Insert Functions
# ---------------------------------------------------------------------------

def insert_bench_run(result: dict) -> int:
    """Insert a benchmark run result into the database.

    Args:
        result: Dict from run_bench_via_api() or similar

    Returns:
        Row ID of the inserted record
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO bench_runs
               (engine, model, model_path, tok_s, context_size,
                prompt_tokens, generated_tokens, eval_ms, prompt_eval_ms,
                latency_ms, benchmark_source, timestamp, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("engine", ""),
                result.get("model", ""),
                result.get("model_path", ""),
                result.get("tok_s", 0),
                result.get("context_size", 0),
                result.get("prompt_tokens", 0),
                result.get("generated_tokens", 0),
                result.get("eval_ms", 0),
                result.get("prompt_eval_ms", 0),
                result.get("latency_ms", 0),
                result.get("benchmark_source", "api"),
                result.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
                json.dumps(result),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_prompt_run(result: dict) -> int:
    """Insert a prompt run result into the database.

    Args:
        result: Dict from run_prompt_via_api() or similar

    Returns:
        Row ID of the inserted record
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO prompt_runs
               (engine, model_name, model_path, prompt, response,
                latency_ms, output_tokens, prompt_tokens, total_tokens,
                tokens_per_second, timestamp, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("engine", ""),
                result.get("model_name", ""),
                result.get("model_path", ""),
                result.get("prompt", ""),
                result.get("response", ""),
                result.get("latency_ms", 0),
                result.get("output_tokens", 0),
                result.get("prompt_tokens", 0),
                result.get("total_tokens", 0),
                result.get("tokens_per_second", 0),
                result.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
                json.dumps(result),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Query Functions
# ---------------------------------------------------------------------------

def get_bench_runs(limit: int = 50, engine: Optional[str] = None) -> list[dict]:
    """Get benchmark run history."""
    conn = _get_connection()
    try:
        if engine:
            rows = conn.execute(
                "SELECT * FROM bench_runs WHERE engine = ? ORDER BY timestamp DESC LIMIT ?",
                (engine, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bench_runs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_prompt_runs(limit: int = 50, engine: Optional[str] = None) -> list[dict]:
    """Get prompt run history."""
    conn = _get_connection()
    try:
        if engine:
            rows = conn.execute(
                "SELECT * FROM prompt_runs WHERE engine = ? ORDER BY timestamp DESC LIMIT ?",
                (engine, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM prompt_runs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_runs(limit: int = 50) -> dict:
    """Get latest runs from both tables."""
    return {
        "bench_runs": get_bench_runs(limit),
        "prompt_runs": get_prompt_runs(limit),
    }


def get_comparison() -> dict:
    """Get aggregated comparison data across engines and models."""
    conn = _get_connection()
    try:
        bench = conn.execute(
            """SELECT engine, model, AVG(tok_s) as avg_tok_s,
                      AVG(latency_ms) as avg_latency, COUNT(*) as run_count
               FROM bench_runs
               GROUP BY engine, model
               ORDER BY avg_tok_s DESC"""
        ).fetchall()

        prompt = conn.execute(
            """SELECT engine, model_name, AVG(latency_ms) as avg_latency,
                      AVG(tokens_per_second) as avg_tps, COUNT(*) as run_count
               FROM prompt_runs
               GROUP BY engine, model_name
               ORDER BY avg_tps DESC"""
        ).fetchall()

        return {
            "bench_comparison": [dict(r) for r in bench],
            "prompt_comparison": [dict(r) for r in prompt],
        }
    finally:
        conn.close()
