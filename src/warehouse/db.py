"""Postgres connection helper for the data warehouse."""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv


def get_pg_dsn() -> str:
    load_dotenv()
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]
    port = os.getenv("POSTGRES_PORT", "5432")
    host = os.getenv("POSTGRES_HOST", "localhost")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_pg_connection() -> psycopg.Connection:
    """Open a new psycopg connection. Caller is responsible for closing it."""
    return psycopg.connect(get_pg_dsn())


@contextmanager
def pg_connection():
    """Context-managed Postgres connection."""
    conn = get_pg_connection()
    try:
        yield conn
    finally:
        conn.close()
