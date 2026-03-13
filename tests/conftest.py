# tests/conftest.py
import sqlite3
import pytest
from forest_cli.db import init_db, seed_db


@pytest.fixture
def db():
    """In-memory SQLite DB, initialized and seeded. Shared across test modules."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    seed_db(conn)
    return conn
