from __future__ import annotations

import os
from pathlib import Path

from db.db_base import get_cursor, init_connection_pool


def drop_all_tables() -> None:
    """
    Drop all existing tables to ensure a clean rebuild.
    """
    with get_cursor(commit=True) as cur:
        # Drop all tables in the correct order (reverse of dependencies)
        cur.execute("""
            DROP TABLE IF EXISTS verifikasi_penerima_pupuk CASCADE;
            DROP TABLE IF EXISTS riwayat_stock_pupuk CASCADE;
            DROP TABLE IF EXISTS acara_distribusi_item CASCADE;
            DROP TABLE IF EXISTS acara_distribusi_pupuk CASCADE;
            DROP TABLE IF EXISTS jadwal_distribusi_item CASCADE;
            DROP TABLE IF EXISTS hasil_tani CASCADE;
            DROP TABLE IF EXISTS jadwal_distribusi_pupuk CASCADE;
            DROP TABLE IF EXISTS pengajuan_pupuk CASCADE;
            DROP TABLE IF EXISTS jadwal_distribusi_event CASCADE;
            DROP TABLE IF EXISTS stok_pupuk CASCADE;
            DROP TABLE IF EXISTS profile_petani CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
        """)


def init_schema() -> None:
    # First, drop all existing tables
    drop_all_tables()
    
    # Then apply the schema
    schema_path = Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")

    # psycopg2 can execute multiple statements in one execute() call
    with get_cursor(commit=True) as cur:
        cur.execute(sql)


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

