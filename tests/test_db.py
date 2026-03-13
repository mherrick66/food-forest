# tests/test_db.py
from forest_cli.db import search_suppliers, list_categories, list_suppliers, supplier_detail, add_supplier, get_connection


def test_init_db_creates_tables(db):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"suppliers", "categories", "supplier_categories", "items"}.issubset(tables)


def test_seed_db_populates_suppliers(db):
    count = db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count >= 5


def test_seed_db_populates_categories(db):
    cats = {row[0] for row in db.execute("SELECT name FROM categories").fetchall()}
    assert cats == {"plants", "fruit_trees", "irrigation", "seeds", "livestock"}


def test_search_suppliers_by_item_name(db):
    results = search_suppliers(db, "wax myrtle")
    assert len(results) >= 1
    names = [r["name"] for r in results]
    assert any("nursery" in n.lower() or "wilsons" in n.lower() or "sweet bay" in n.lower() for n in names)


def test_search_suppliers_by_category(db):
    results = search_suppliers(db, "irrigation")
    assert len(results) >= 1


def test_search_suppliers_case_insensitive(db):
    lower = search_suppliers(db, "mango")
    upper = search_suppliers(db, "MANGO")
    assert len(lower) == len(upper)


def test_search_suppliers_no_results_returns_empty_list(db):
    results = search_suppliers(db, "xyzzy_nonexistent_item_99999")
    assert results == []


def test_list_categories_returns_all_five(db):
    cats = list_categories(db)
    assert set(cats) == {"plants", "fruit_trees", "irrigation", "seeds", "livestock"}


def test_list_suppliers_no_filter(db):
    suppliers = list_suppliers(db)
    assert len(suppliers) >= 5


def test_list_suppliers_filtered_by_category(db):
    irrigation = list_suppliers(db, category="irrigation")
    all_s = list_suppliers(db)
    assert len(irrigation) < len(all_s)
    assert len(irrigation) >= 1


# T-22: SQL injection does not destroy data
def test_search_sql_injection_db_intact(db):
    search_suppliers(db, "'; DROP TABLE suppliers; --")
    count = db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count >= 5


# T-23: Missing DB path raises or creates
def test_missing_db_path_raises_or_creates(tmp_path):
    conn = get_connection(tmp_path / "nonexistent" / "forest.db")
    count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count >= 5
    conn.close()


# T-43: supplier_detail returns categories and items
def test_supplier_detail_includes_categories_and_items(db):
    row = db.execute("SELECT id FROM suppliers WHERE name LIKE '%Ewing%'").fetchone()
    assert row is not None
    detail = supplier_detail(db, row["id"])
    assert "irrigation" in detail["categories"]
    assert len(detail["items"]) >= 1
    assert any("drip" in item.lower() for item in detail["items"])


# T-44: add_supplier inserts and returns id
def test_add_supplier_inserts_and_returns_id(db):
    new_id = add_supplier(db, "Test Farm", "1 Farm Rd", "(941) 000-0000", "https://test.com", ["plants"], ["Blueberry"])
    assert isinstance(new_id, int)
    row = db.execute("SELECT * FROM suppliers WHERE id = ?", (new_id,)).fetchone()
    assert row["name"] == "Test Farm"
    item_row = db.execute("SELECT name FROM items WHERE supplier_id = ?", (new_id,)).fetchone()
    assert item_row["name"] == "Blueberry"


# T-45: add_supplier inserts new category if absent
def test_add_supplier_creates_new_category(db):
    add_supplier(db, "Fungi Farm", "", "", "", ["mushrooms"], ["Oyster mushroom"])
    row = db.execute("SELECT name FROM categories WHERE name = 'mushrooms'").fetchone()
    assert row is not None
