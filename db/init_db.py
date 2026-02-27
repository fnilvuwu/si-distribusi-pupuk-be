from __future__ import annotations

import os

from sqlalchemy import inspect, text
from db.db_base import engine
from db.models import Base

def drop_all_tables() -> None:
    """
    Drop all existing tables to ensure a clean rebuild.
    Supports PostgreSQL (CASCADE) and MySQL (FOREIGN_KEY_CHECKS toggle).
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    elif engine.dialect.name == "mysql":
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    else:
        Base.metadata.drop_all(bind=engine)

def init_schema() -> None:
    """
    Initialize the database schema by dropping existing tables and recreating them.
    """
    # First, drop all existing tables
    drop_all_tables()
    
    # Then apply the schema
    Base.metadata.create_all(bind=engine)

def maybe_init_schema() -> None:
    """
    Initialize DB schema when AUTO_CREATE_TABLES=1/true/yes.
    """
    flag = (os.getenv("AUTO_CREATE_TABLES") or "").strip().lower()
    if flag in {"1", "true", "yes", "y", "on"}:
        init_schema()

if __name__ == "__main__":
    init_schema()
    print("[db] schema initialized")

