from __future__ import annotations

import os

from db.db_base import engine
from db.models import Base

def drop_all_tables() -> None:
    """
    Drop all existing tables to ensure a clean rebuild.
    """
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

