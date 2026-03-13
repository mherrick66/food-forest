# tests/test_live.py
"""Live / integrity tests against the real on-disk database.

Run explicitly: pytest tests/test_live.py
Excluded from default suite via conftest or manual --ignore.
"""
import pytest
from forest_cli.db import get_connection

pytestmark = pytest.mark.live


# T-46
def test_live_db_supplier_count():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count >= 10
    conn.close()


# T-47
def test_live_db_fk_integrity():
    conn = get_connection()
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    assert violations == []
    conn.close()


# T-48
def test_live_db_items_have_valid_suppliers():
    conn = get_connection()
    orphans = conn.execute(
        "SELECT COUNT(*) FROM items i LEFT JOIN suppliers s ON s.id = i.supplier_id WHERE s.id IS NULL"
    ).fetchone()[0]
    assert orphans == 0
    conn.close()
