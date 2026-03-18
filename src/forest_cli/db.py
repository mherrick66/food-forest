"""Database initialization, seeding, and query helpers for forest-cli."""
from __future__ import annotations

import importlib.resources
import sqlite3
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "forest-cli" / "forest.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    address TEXT,
    phone   TEXT,
    website TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS supplier_categories (
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (supplier_id, category_id)
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id)
);
"""

# Seed data: (supplier_name, category_name, [item_names])
SEED_ITEMS: list[tuple[str, str, list[str]]] = [
    ("Sweet Bay Nursery",             "plants",      ["Wax Myrtle", "Simpson Stopper", "Coontie", "Cabbage Palm", "Sabal Palm"]),
    ("Sweet Bay Nursery",             "fruit_trees", ["Mango tree", "Avocado tree", "Loquat tree"]),
    ("Ewing Outdoor Supply",          "irrigation",  ["drip tape", "soaker hose", "irrigation controller", "emitters", "poly tubing", "filter", "pressure regulator"]),
    ("SiteOne Landscape Supply",      "irrigation",  ["drip irrigation kit", "sprinkler heads", "valve box", "PVC fittings", "poly pipe"]),
    ("Tractor Supply Co. — Sarasota", "seeds",       ["sunflower seed", "pumpkin seed", "squash seed", "wildflower mix", "pasture mix"]),
    ("Tractor Supply Co. — Sarasota", "livestock",   ["chickens", "ducks", "layer pellets", "chick starter feed", "rabbit feed", "goat feed", "cattle panels"]),
    ("Myakka Ranch & Farm Supply",    "livestock",   ["goats", "pigs", "chicken feed", "pig feed", "hay", "salt lick"]),
    ("Myakka Ranch & Farm Supply",    "seeds",       ["field peas", "sorghum seed", "bahia grass seed"]),
    ("Sarasota County Extension Office","plants",    ["native plant guides", "Wax Myrtle", "Firebush"]),
    ("Sarasota County Extension Office","seeds",     ["seed saving workshops", "heirloom seeds"]),
    ("Sarasota Farmers Market",       "plants",      ["native plants", "herb starts", "vegetable starts"]),
    ("Sarasota Farmers Market",       "seeds",       ["heirloom seeds", "herb seeds", "vegetable seeds"]),
    ("Sarasota Farmers Market",       "fruit_trees", ["citrus", "banana", "fig"]),
    ("Home Depot Garden Center — Sarasota", "plants",      ["Areca Palm", "Bougainvillea", "Firebush", "Plumbago"]),
    ("Home Depot Garden Center — Sarasota", "fruit_trees", ["Citrus tree", "Fig tree", "Lemon tree", "Lime tree", "Orange tree"]),
    ("Home Depot Garden Center — Sarasota", "irrigation",  ["drip irrigation kit", "garden hose", "soaker hose", "sprinkler heads", "timer"]),
    ("Home Depot Garden Center — Sarasota", "seeds",       ["herb seeds", "vegetable seeds", "wildflower mix"]),
    ("Lowes Garden Center — Sarasota","plants",      ["Firebush", "Plumbago", "ornamental grasses"]),
    ("Lowes Garden Center — Sarasota","fruit_trees", ["Citrus tree", "Fig tree", "Lemon tree", "Orange tree"]),
    ("Lowes Garden Center — Sarasota","irrigation",  ["drip irrigation kit", "garden hose", "soaker hose", "sprinkler heads", "timer"]),
    ("Lowes Garden Center — Sarasota","seeds",       ["herb seeds", "vegetable seeds", "wildflower mix"]),
    ("DG Ace Hardware",               "livestock",   ["chicken feed", "chick starter feed", "layer pellets", "rabbit feed"]),
    ("DG Ace Hardware",               "seeds",       ["bahia grass seed", "pasture mix", "wildflower mix"]),
    ("DG Ace Hardware",               "irrigation",  ["drip tape", "garden hose", "soaker hose", "timer"]),
]


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    if conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0:
        seed_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create schema tables if they don't exist."""
    conn.executescript(SCHEMA)
    conn.commit()


def seed_db(conn: sqlite3.Connection) -> None:
    """Insert seed supplier and item data."""
    sql_text = importlib.resources.files("forest_cli.data").joinpath("seed.sql").read_text()
    conn.executescript(sql_text)

    # Insert categories
    for cat in ("plants", "fruit_trees", "irrigation", "seeds", "livestock"):
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))

    # Link suppliers -> categories -> items
    for supplier_name, category_name, item_names in SEED_ITEMS:
        row = conn.execute("SELECT id FROM suppliers WHERE name = ?", (supplier_name,)).fetchone()
        if not row:
            continue
        supplier_id = row["id"]
        cat_row = conn.execute("SELECT id FROM categories WHERE name = ?", (category_name,)).fetchone()
        if not cat_row:
            continue
        category_id = cat_row["id"]
        conn.execute(
            "INSERT OR IGNORE INTO supplier_categories (supplier_id, category_id) VALUES (?, ?)",
            (supplier_id, category_id),
        )
        for item_name in item_names:
            conn.execute(
                "INSERT INTO items (supplier_id, name, category_id) VALUES (?, ?, ?)",
                (supplier_id, item_name, category_id),
            )

    conn.commit()


def _escape_like(text: str) -> str:
    """Escape LIKE wildcards so user input is treated literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_suppliers(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Return suppliers whose name, items, or categories match query (case-insensitive substring)."""
    escaped = _escape_like(query.lower())
    pattern = f"%{escaped}%"
    sql = """
        SELECT DISTINCT s.id, s.name, s.address, s.phone, s.website
        FROM suppliers s
        LEFT JOIN items i ON i.supplier_id = s.id
        LEFT JOIN categories c ON c.id = i.category_id
        WHERE LOWER(s.name) LIKE ? ESCAPE '\\'
           OR LOWER(i.name) LIKE ? ESCAPE '\\'
           OR LOWER(c.name) LIKE ? ESCAPE '\\'
        ORDER BY s.name
    """
    rows = conn.execute(sql, (pattern, pattern, pattern)).fetchall()
    return [dict(r) for r in rows]


def _supplier_items(conn: sqlite3.Connection, supplier_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM items WHERE supplier_id = ? ORDER BY name", (supplier_id,)
    ).fetchall()
    return [r["name"] for r in rows]


def _supplier_categories(conn: sqlite3.Connection, supplier_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT c.name FROM categories c
           JOIN supplier_categories sc ON sc.category_id = c.id
           WHERE sc.supplier_id = ? ORDER BY c.name""",
        (supplier_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def supplier_detail(conn: sqlite3.Connection, supplier_id: int) -> dict[str, Any] | None:
    """Return full supplier info including categories and items, or None if not found."""
    row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["categories"] = _supplier_categories(conn, supplier_id)
    d["items"] = _supplier_items(conn, supplier_id)
    return d


def list_categories(conn: sqlite3.Connection) -> list[str]:
    """Return all category names, sorted."""
    rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def list_suppliers(conn: sqlite3.Connection, category: str | None = None) -> list[dict[str, Any]]:
    """Return all suppliers, optionally filtered by category name."""
    if category:
        sql = """
            SELECT DISTINCT s.id, s.name, s.address, s.phone, s.website
            FROM suppliers s
            JOIN supplier_categories sc ON sc.supplier_id = s.id
            JOIN categories c ON c.id = sc.category_id
            WHERE LOWER(c.name) = LOWER(?)
            ORDER BY s.name
        """
        rows = conn.execute(sql, (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def add_supplier(
    conn: sqlite3.Connection,
    name: str,
    address: str,
    phone: str,
    website: str,
    categories: list[str],
    items: list[str],
) -> int:
    """Insert a new supplier and return its id.

    Raises ValueError if a supplier with the same name already exists.
    """
    try:
        cur = conn.execute(
            "INSERT INTO suppliers (name, address, phone, website) VALUES (?, ?, ?, ?)",
            (name, address, phone, website),
        )
    except sqlite3.IntegrityError:
        raise ValueError(f"Supplier '{name}' already exists")
    supplier_id = cur.lastrowid
    for cat_name in categories:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat_name,))
        cat_row = conn.execute("SELECT id FROM categories WHERE name = ?", (cat_name,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO supplier_categories (supplier_id, category_id) VALUES (?, ?)",
            (supplier_id, cat_row["id"]),
        )
    for item_name in items:
        conn.execute(
            "INSERT INTO items (supplier_id, name) VALUES (?, ?)",
            (supplier_id, item_name),
        )
    conn.commit()
    return supplier_id
