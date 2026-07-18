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
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

# ---------------------------------------------------------------------------
# Database Path
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "db")
DB_PATH = os.path.join(DB_DIR, "benchmark.db")


def _format_timestamp() -> str:
    """Return current timestamp in EST, 12-hour format with seconds: '2026-07-16 07:50:45 PM EDT'."""
    try:
        eastern = ZoneInfo("US/Eastern")
    except Exception:
        eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern)
    return now.strftime("%Y-%m-%d %I:%M:%S %p %Z")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Engine configurations table (dynamic engine management)
CREATE TABLE IF NOT EXISTS engines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    engine_type TEXT NOT NULL DEFAULT 'llama.cpp',  -- llama.cpp, openai, custom
    description TEXT DEFAULT '',
    port INTEGER DEFAULT 80,
    ssh_enabled INTEGER DEFAULT 0,
    ssh_host TEXT DEFAULT '',
    ssh_user TEXT DEFAULT 'root',
    ssh_key_path TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bench_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_id INTEGER,
    engine TEXT NOT NULL,
    model TEXT NOT NULL,
    model_path TEXT,
    tok_s REAL,
    context_size INTEGER,
    mtp INTEGER DEFAULT 0,
    quantization TEXT DEFAULT 'unknown',
    max_tokens INTEGER DEFAULT 128,
    prompt_tokens INTEGER,
    generated_tokens INTEGER,
    eval_ms REAL,
    prompt_eval_ms REAL,
    latency_ms REAL,
    ttft_ms REAL,  -- Time to first token
    input_tok_s REAL,  -- Input tokens per second
    output_tok_s REAL,  -- Output tokens per second
    benchmark_source TEXT DEFAULT 'api',
    run_number INTEGER DEFAULT 1,  -- For multi-run: which run this is
    run_group TEXT DEFAULT '',  -- For multi-run: group ID for averaging
    timestamp TEXT NOT NULL,
    raw_data TEXT  -- JSON dump of full result
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_id INTEGER,
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
    ttft_ms REAL,
    ctx_size INTEGER DEFAULT 8192,
    mtp INTEGER DEFAULT 0,
    quantization TEXT DEFAULT 'unknown',
    run_number INTEGER DEFAULT 1,
    run_group TEXT DEFAULT '',
    timestamp TEXT NOT NULL,
    raw_data TEXT  -- JSON dump of full result
);

CREATE INDEX IF NOT EXISTS idx_bench_engine ON bench_runs(engine);
CREATE INDEX IF NOT EXISTS idx_bench_model ON bench_runs(model);
CREATE INDEX IF NOT EXISTS idx_bench_ts ON bench_runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_bench_run_group ON bench_runs(run_group);
CREATE INDEX IF NOT EXISTS idx_bench_engine_id ON bench_runs(engine_id);

CREATE INDEX IF NOT EXISTS idx_prompt_engine ON prompt_runs(engine);
CREATE INDEX IF NOT EXISTS idx_prompt_model ON prompt_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_prompt_ts ON prompt_runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_prompt_run_group ON prompt_runs(run_group);
CREATE INDEX IF NOT EXISTS idx_prompt_engine_id ON prompt_runs(engine_id);
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


def reload_config():
    """Reload server configuration from config/engines.json.
    
    Call this after config/engines.json has been modified to refresh
    SERVER_URLS, CTX_SIZES, and MTP_OPTIONS without restarting.
    """
    from app.models import reload_config as models_reload
    models_reload()


# ---------------------------------------------------------------------------
# Engine Management Functions
# ---------------------------------------------------------------------------

def add_engine(name: str, url: str, engine_type: str = "llama.cpp",
               description: str = "", port: int = 80,
               ssh_enabled: bool = False, ssh_host: str = "",
               ssh_user: str = "root", ssh_key_path: str = "") -> int:
    """Add a new engine configuration.

    Args:
        name: Unique engine name (e.g., 'HLH', 'PLH', 'Claude')
        url: Base URL of the engine's API endpoint
        engine_type: Type of engine (llama.cpp, openai, custom)
        description: Optional description
        port: Port number (default 80)
        ssh_enabled: Whether SSH is enabled for model discovery
        ssh_host: SSH hostname
        ssh_user: SSH username
        ssh_key_path: Path to SSH private key

    Returns:
        Row ID of the inserted record
    """
    now = _format_timestamp()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO engines (name, url, engine_type, description, port,
               ssh_enabled, ssh_host, ssh_user, ssh_key_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, url, engine_type, description, port,
             int(ssh_enabled), ssh_host, ssh_user, ssh_key_path, now, now),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_engine(engine_id: int, **kwargs) -> bool:
    """Update an existing engine configuration.

    Args:
        engine_id: Engine ID to update
        **kwargs: Fields to update (name, url, engine_type, description, port, etc.)

    Returns:
        True if updated, False if not found
    """
    allowed_fields = {'url', 'engine_type', 'description', 'port',
                      'ssh_enabled', 'ssh_host', 'ssh_user', 'ssh_key_path'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not updates:
        return False

    updates['updated_at'] = _format_timestamp()
    set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
    values = list(updates.values()) + [engine_id]

    conn = _get_connection()
    try:
        cursor = conn.execute(
            f'UPDATE engines SET {set_clause} WHERE id = ?',
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_engine(engine_id: int) -> bool:
    """Delete an engine configuration.

    Args:
        engine_id: Engine ID to delete

    Returns:
        True if deleted, False if not found
    """
    conn = _get_connection()
    try:
        cursor = conn.execute('DELETE FROM engines WHERE id = ?', (engine_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_engine(engine_id: int) -> Optional[dict]:
    """Get a single engine by ID.

    Args:
        engine_id: Engine ID

    Returns:
        Engine dict or None
    """
    conn = _get_connection()
    try:
        row = conn.execute('SELECT * FROM engines WHERE id = ?', (engine_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_engine_by_name(name: str) -> Optional[dict]:
    """Get a single engine by name.

    Args:
        name: Engine name

    Returns:
        Engine dict or None
    """
    conn = _get_connection()
    try:
        row = conn.execute('SELECT * FROM engines WHERE name = ?', (name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_engines() -> list[dict]:
    """Get all engine configurations.

    Returns:
        List of engine dicts
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM engines ORDER BY name'
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_engine_url(engine_name: str) -> Optional[str]:
    """Get the base URL for an engine by name.

    Args:
        engine_name: Engine name

    Returns:
        Base URL or None
    """
    engine = get_engine_by_name(engine_name)
    if engine:
        port = engine.get('port', 80)
        url = engine.get('url', '')
        if port and port != 80:
            return f"{url}:{port}"
        return url
    return None


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
               (engine_id, engine, model, model_path, tok_s, context_size, mtp,
                quantization, max_tokens, prompt_tokens, generated_tokens,
                eval_ms, prompt_eval_ms, latency_ms, ttft_ms,
                input_tok_s, output_tok_s, benchmark_source,
                run_number, run_group, timestamp, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("engine_id"),
                result.get("engine", ""),
                result.get("model", ""),
                result.get("model_path", ""),
                result.get("tok_s", 0),
                result.get("context_size", 0),
                result.get("mtp", 0),
                result.get("quantization", "unknown"),
                result.get("max_tokens", 128),
                result.get("prompt_tokens", 0),
                result.get("generated_tokens", 0),
                result.get("eval_ms", 0),
                result.get("prompt_eval_ms", 0),
                result.get("latency_ms", 0),
                result.get("ttft_ms"),
                result.get("input_tok_s"),
                result.get("output_tok_s"),
                result.get("benchmark_source", "api"),
                result.get("run_number", 1),
                result.get("run_group", ""),
                result.get("timestamp", _format_timestamp()),
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
               (engine_id, engine, model_name, model_path, prompt, response,
                latency_ms, output_tokens, prompt_tokens, total_tokens,
                tokens_per_second, ttft_ms, ctx_size, mtp, quantization,
                run_number, run_group, timestamp, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("engine_id"),
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
                result.get("ttft_ms"),
                result.get("ctx_size", 8192),
                result.get("mtp", 0),
                result.get("quantization", "unknown"),
                result.get("run_number", 1),
                result.get("run_group", ""),
                result.get("timestamp", _format_timestamp()),
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


# ---------------------------------------------------------------------------
# Multi-Run Aggregation Functions
# ---------------------------------------------------------------------------

def get_run_group_avg(engine: str, model: str, run_group: str,
                      bench_only: bool = True) -> Optional[dict]:
    """Get averaged results for a multi-run group.

    Args:
        engine: Engine name
        model: Model name
        run_group: Run group ID
        bench_only: If True, only aggregate bench_runs

    Returns:
        Dict with averaged metrics or None
    """
    conn = _get_connection()
    try:
        if bench_only:
            row = conn.execute(
                """SELECT
                    AVG(tok_s) as avg_tok_s,
                    MIN(tok_s) as min_tok_s,
                    MAX(tok_s) as max_tok_s,
                    AVG(input_tok_s) as avg_input_tok_s,
                    AVG(output_tok_s) as avg_output_tok_s,
                    AVG(ttft_ms) as avg_ttft_ms,
                    AVG(latency_ms) as avg_latency,
                    AVG(prompt_tokens) as avg_prompt_tokens,
                    AVG(generated_tokens) as avg_generated_tokens,
                    COUNT(*) as run_count,
                    AVG(context_size) as avg_context_size,
                    AVG(mtp) as avg_mtp
                FROM bench_runs
                WHERE engine = ? AND model = ? AND run_group = ?""",
                (engine, model, run_group),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT
                    AVG(tokens_per_second) as avg_tok_s,
                    MIN(tokens_per_second) as min_tok_s,
                    MAX(tokens_per_second) as max_tok_s,
                    AVG(ttft_ms) as avg_ttft_ms,
                    AVG(latency_ms) as avg_latency,
                    AVG(prompt_tokens) as avg_prompt_tokens,
                    AVG(output_tokens) as avg_generated_tokens,
                    COUNT(*) as run_count,
                    AVG(ctx_size) as avg_context_size,
                    AVG(mtp) as avg_mtp
                FROM prompt_runs
                WHERE engine = ? AND model_name = ? AND run_group = ?""",
                (engine, model, run_group),
            ).fetchone()

        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_multi_run_summary(engine: str, model: str) -> list[dict]:
    """Get all run groups for an engine/model combination.

    Args:
        engine: Engine name
        model: Model name

    Returns:
        List of run group summaries with averages
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT DISTINCT run_group FROM bench_runs
               WHERE engine = ? AND model = ? AND run_group != ''
               ORDER BY timestamp DESC""",
            (engine, model),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
