from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import text

from db.db_base import get_cursor, init_connection_pool


def init_schema() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")

    # psycopg2 can execute multiple statements in one execute() call
    with get_cursor(commit=True) as cur:
        cur.execute(text(sql))


def maybe_init_schema() -> None:
    """
    Initialize DB schema when AUTO_CREATE_TABLES=1/true/yes.
    """
    flag = (os.getenv("AUTO_CREATE_TABLES") or "").strip().lower()
    if flag in {"1", "true", "yes", "y", "on"}:
        init_schema()


if __name__ == "__main__":
    init_connection_pool()
    init_schema()
    print("[db] schema initialized")

