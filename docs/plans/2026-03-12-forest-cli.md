# Forest CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task.

**Goal:** Build a `forest` CLI tool that searches a curated SQLite database of Sarasota, FL local suppliers for food forest supplies (plants, fruit trees, irrigation, seeds, livestock).

**Architecture:** Single-package Python CLI with a `src/forest_cli/` layout. All data lives in a bundled SQLite database seeded with real Sarasota-area suppliers. Commands use Click for argument parsing and Rich for beautiful colored output. The database module is the only layer between CLI commands and `sqlite3` stdlib — no ORM, no migrations framework.

**Tech Stack:** Python 3.11+, Click 8.1, Rich, sqlite3 (stdlib), pytest 8, hatchling

---

## Project Layout

```
food-forest-cli/
├── pyproject.toml
├── src/
│   └── forest_cli/
│       ├── __init__.py
│       ├── cli.py          # Click group + all commands
│       ├── db.py           # Database init, seed, query helpers
│       └── data/
│           └── seed.sql    # INSERT statements for Sarasota suppliers
├── tests/
│   ├── conftest.py         # shared fixtures
│   ├── test_db.py          # unit tests for db module
│   └── test_cli.py         # CLI tests via CliRunner(mix_stderr=False)
└── docs/
    └── plans/
        └── 2026-03-12-forest-cli.md
```

---

## Database Schema

```sql
CREATE TABLE suppliers (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    address   TEXT,
    phone     TEXT,
    website   TEXT
);

CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE   -- plants | fruit_trees | irrigation | seeds | livestock
);

CREATE TABLE supplier_categories (
    supplier_id INTEGER REFERENCES suppliers(id),
    category_id INTEGER REFERENCES categories(id),
    PRIMARY KEY (supplier_id, category_id)
);

CREATE TABLE items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id),
    name        TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id)
);
```

Search is a single SQL query: `SELECT DISTINCT s.* FROM suppliers s JOIN items i ON i.supplier_id = s.id WHERE LOWER(i.name) LIKE LOWER('%<query>%') OR LOWER(i.category_name) LIKE LOWER('%<query>%')`.

---

## Seed Data (Sarasota-area suppliers)

Real suppliers to include:

| Name | Categories | Notes |
|------|-----------|-------|
| Wilsons Nursery & Landscaping, Sarasota | plants, fruit_trees | local nursery |
| Sweet Bay Nursery, Sarasota | plants, fruit_trees | native plants focus |
| Tropical Fruit World / J&P Tropicals (Venice area) | fruit_trees | mango, avocado, citrus |
| Punta Gorda Nursery (placeholder if no local equiv) | fruit_trees | — |
| Sarasota Farmers Market vendors | plants, seeds | seasonal |
| Suncoast Hydroponics (Bradenton) | seeds, irrigation | hydro supplies |
| SiteOne Landscape Supply (Sarasota) | irrigation | commercial irrigation parts |
| Ewing Irrigation (Sarasota) | irrigation | sprinklers, drip, valves |
| Seed Savers Exchange (online, placeholder) | seeds | heirloom seeds |
| Southern States (Sarasota / Myakka) | seeds, livestock | farm supply store |
| Tractor Supply Co. (Sarasota / Bradenton) | seeds, livestock | poultry, livestock supplies |
| Myakka City Feed & Farm Supply | livestock, seeds | local feed store |
| Sarasota County Extension Office | plants, seeds | educational resource |

Each supplier gets representative items seeded (e.g., "Wax Myrtle", "Orange tree", "Mango tree", "drip tape", "soaker hose", "chickens", "layer pellets", "heirloom tomato seed").

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/forest_cli/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "forest-cli"
version = "0.1.0"
description = "Find local Sarasota suppliers for your food forest"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1,<8.2",
    "rich>=13.0",
]

[project.scripts]
forest = "forest_cli.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/forest_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create `src/forest_cli/__init__.py`** (empty file)

**Step 3: Create `tests/conftest.py`**

```python
# tests/conftest.py
# Shared fixtures — populated in Task 2 once db.py exists.
```

**Step 4: Install in editable mode**

```bash
pip install -e ".[dev]"
```

Expected: installs without errors, `forest --help` prints usage.

**Step 5: Commit**

```bash
git add pyproject.toml src/forest_cli/__init__.py tests/conftest.py
git commit -m "chore: scaffold project structure"
```

---

## Task 2: Database Module

**Files:**
- Create: `src/forest_cli/db.py`
- Create: `src/forest_cli/data/seed.sql`
- Create: `src/forest_cli/data/__init__.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_db.py`

**Step 1: Update `tests/conftest.py` with the shared `db` fixture**

```python
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
```

**Step 3: Write the failing tests**

```python
# tests/test_db.py
from forest_cli.db import search_suppliers, list_categories, list_suppliers


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
```

**Step 4: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'forest_cli.db'`

**Step 5: Create `src/forest_cli/data/seed.sql`**

```sql
-- Categories
INSERT OR IGNORE INTO categories (name) VALUES ('plants');
INSERT OR IGNORE INTO categories (name) VALUES ('fruit_trees');
INSERT OR IGNORE INTO categories (name) VALUES ('irrigation');
INSERT OR IGNORE INTO categories (name) VALUES ('seeds');
INSERT OR IGNORE INTO categories (name) VALUES ('livestock');

-- Suppliers (INSERT OR IGNORE so seed.sql is idempotent)
INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Wilsons Nursery & Landscaping',
   '4218 Bee Ridge Rd, Sarasota, FL 34233',
   '(941) 378-0600',
   'https://wilsonsnursery.net');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Sweet Bay Nursery',
   '6831 Swift Rd, Sarasota, FL 34231',
   '(941) 923-6909',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('J&P Tropicals',
   '7150 Hatton Ave, North Port, FL 34287',
   '(941) 426-1145',
   'https://jptropicals.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Ewing Irrigation & Landscape Supply',
   '1725 Cattlemen Rd, Sarasota, FL 34232',
   '(941) 371-3331',
   'https://ewing1.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('SiteOne Landscape Supply',
   '8750 Fruitville Rd, Sarasota, FL 34240',
   '(941) 377-9922',
   'https://siteone.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Suncoast Hydroponics',
   '1208 53rd Ave E, Bradenton, FL 34203',
   '(941) 753-4769',
   'https://suncoasthydroponics.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Tractor Supply Co. — Sarasota',
   '6240 S Tamiami Trail, Sarasota, FL 34231',
   '(941) 923-1113',
   'https://tractorsupply.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Myakka City Feed & Farm Supply',
   '10900 State Road 70 E, Myakka City, FL 34251',
   '(941) 322-1500',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Sarasota County Extension Office',
   '6700 Clark Rd, Sarasota, FL 34241',
   '(941) 861-9900',
   'https://sfyl.ifas.ufl.edu/sarasota');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Southern States — Sarasota',
   '7281 Fruitville Rd, Sarasota, FL 34240',
   '(941) 371-2533',
   'https://southernstates.com');

-- supplier_categories (resolved by name for readability — handled in seed_db())
-- Items per supplier are inserted by seed_db() Python function for clarity.
```

**Step 4: Create `src/forest_cli/db.py`**

```python
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
    name    TEXT NOT NULL,
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
    ("Wilsons Nursery & Landscaping", "plants",      ["Wax Myrtle", "Beautyberry", "Firebush", "Muhly Grass", "Wild Coffee"]),
    ("Wilsons Nursery & Landscaping", "fruit_trees", ["Orange tree", "Lemon tree", "Fig tree"]),
    ("Sweet Bay Nursery",             "plants",      ["Wax Myrtle", "Simpson Stopper", "Coontie", "Cabbage Palm", "Sabal Palm"]),
    ("Sweet Bay Nursery",             "fruit_trees", ["Mango tree", "Avocado tree", "Loquat tree"]),
    ("J&P Tropicals",                 "fruit_trees", ["Mango tree", "Avocado tree", "Banana", "Papaya", "Jackfruit", "Starfruit", "Sapodilla", "Lychee", "Longan"]),
    ("Ewing Irrigation & Landscape Supply", "irrigation", ["drip tape", "soaker hose", "irrigation controller", "emitters", "poly tubing", "filter", "pressure regulator"]),
    ("SiteOne Landscape Supply",      "irrigation",  ["drip irrigation kit", "sprinkler heads", "valve box", "PVC fittings", "poly pipe"]),
    ("Suncoast Hydroponics",          "seeds",       ["heirloom tomato seed", "pepper seed", "basil seed", "herb seed mix", "cover crop mix"]),
    ("Suncoast Hydroponics",          "irrigation",  ["drip manifold", "netted pots", "grow media", "timer"]),
    ("Tractor Supply Co. — Sarasota", "seeds",       ["sunflower seed", "pumpkin seed", "squash seed", "wildflower mix", "pasture mix"]),
    ("Tractor Supply Co. — Sarasota", "livestock",   ["chickens", "ducks", "layer pellets", "chick starter feed", "rabbit feed", "goat feed", "cattle panels"]),
    ("Myakka City Feed & Farm Supply","livestock",   ["goats", "pigs", "chicken feed", "pig feed", "hay", "salt lick"]),
    ("Myakka City Feed & Farm Supply","seeds",       ["field peas", "sorghum seed", "bahia grass seed"]),
    ("Sarasota County Extension Office","plants",    ["native plant guides", "Wax Myrtle", "Firebush"]),
    ("Sarasota County Extension Office","seeds",     ["seed saving workshops", "heirloom seeds"]),
    ("Southern States — Sarasota",    "seeds",       ["cover crop seed", "corn seed", "soybean seed", "rye grass seed"]),
    ("Southern States — Sarasota",    "livestock",   ["poultry supplies", "layer pellets", "cattle feed", "veterinary supplies"]),
]


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
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
    # executescript() issues an implicit COMMIT before running, so call it first
    # while no in-flight transaction exists.
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


def search_suppliers(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Return suppliers whose items or categories match query (case-insensitive substring)."""
    pattern = f"%{query.lower()}%"
    sql = """
        SELECT DISTINCT s.id, s.name, s.address, s.phone, s.website
        FROM suppliers s
        JOIN items i ON i.supplier_id = s.id
        JOIN categories c ON c.id = i.category_id
        WHERE LOWER(i.name) LIKE ?
           OR LOWER(c.name) LIKE ?
        ORDER BY s.name
    """
    rows = conn.execute(sql, (pattern, pattern)).fetchall()
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


def supplier_detail(conn: sqlite3.Connection, supplier_id: int) -> dict[str, Any]:
    """Return full supplier info including categories and items."""
    row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
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
    """Insert a new supplier and return its id."""
    cur = conn.execute(
        "INSERT INTO suppliers (name, address, phone, website) VALUES (?, ?, ?, ?)",
        (name, address, phone, website),
    )
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
```

**Step 6: Create `src/forest_cli/data/__init__.py`** (empty)

**Step 7: Run tests**

```bash
pytest tests/test_db.py -v
```

Expected: all tests PASS.

**Step 8: Commit**

```bash
git add src/forest_cli/db.py src/forest_cli/data/__init__.py src/forest_cli/data/seed.sql tests/conftest.py tests/test_db.py
git commit -m "feat: add db module with schema, seed data, and query helpers"
```

---

## Task 3: CLI — all four commands

**Files:**
- Create: `src/forest_cli/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing tests**

```python
# tests/test_cli.py
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from forest_cli.cli import main


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


FAKE_SUPPLIERS = [
    {
        "id": 1,
        "name": "Test Nursery",
        "address": "123 Main St, Sarasota, FL",
        "phone": "(941) 555-0001",
        "website": "https://testnursery.com",
    }
]

FAKE_CATEGORIES = ["fruit_trees", "irrigation", "livestock", "plants", "seeds"]


class TestSearchCommand:
    def test_search_returns_supplier_name(self, runner):
        with patch("forest_cli.cli.get_connection") as mock_conn, \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value={**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}):
            result = runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0
        assert "Test Nursery" in result.output

    def test_search_no_results_exits_zero(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=[]):
            result = runner.invoke(main, ["search", "xyzzy_nonexistent"])
        assert result.exit_code == 0

    def test_search_no_results_prints_message(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=[]):
            result = runner.invoke(main, ["search", "xyzzy_nonexistent"])
        assert "no suppliers" in result.output.lower() or "not found" in result.output.lower()

    def test_search_shows_contact_info(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "wax"])
        assert "(941) 555-0001" in result.output
        assert "123 Main St" in result.output
        assert "testnursery.com" in result.output

    def test_search_requires_query_arg(self, runner):
        result = runner.invoke(main, ["search"])
        assert result.exit_code != 0

    def test_search_help(self, runner):
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output or "query" in result.output.lower()


class TestListCategoriesCommand:
    def test_list_categories_shows_all_five(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_categories", return_value=FAKE_CATEGORIES):
            result = runner.invoke(main, ["list-categories"])
        assert result.exit_code == 0
        for cat in FAKE_CATEGORIES:
            assert cat in result.output

    def test_list_categories_help(self, runner):
        result = runner.invoke(main, ["list-categories", "--help"])
        assert result.exit_code == 0


class TestListSuppliersCommand:
    def test_list_suppliers_shows_all(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_suppliers", return_value=FAKE_SUPPLIERS):
            result = runner.invoke(main, ["list-suppliers"])
        assert result.exit_code == 0
        assert "Test Nursery" in result.output

    def test_list_suppliers_category_filter_passed_through(self, runner):
        captured = {}

        def _capture(conn, category=None):
            captured["category"] = category
            return FAKE_SUPPLIERS

        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_suppliers", side_effect=_capture):
            result = runner.invoke(main, ["list-suppliers", "--category", "plants"])
        assert result.exit_code == 0
        assert captured["category"] == "plants"

    def test_list_suppliers_help_shows_category_option(self, runner):
        result = runner.invoke(main, ["list-suppliers", "--help"])
        assert result.exit_code == 0
        assert "--category" in result.output


class TestAddSupplierCommand:
    def test_add_supplier_prompts_and_inserts(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", return_value=42) as mock_add:
            result = runner.invoke(
                main, ["add-supplier"],
                input="New Farm\n999 Farm Rd\n(941) 555-9999\nhttps://newfarm.com\nplants,seeds\nBlueberry, Strawberry\n"
            )
        assert result.exit_code == 0
        mock_add.assert_called_once()

    def test_add_supplier_shows_success_message(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", return_value=7):
            result = runner.invoke(
                main, ["add-supplier"],
                input="New Farm\n999 Farm Rd\n(941) 555-9999\nhttps://newfarm.com\nplants\nBlueberry\n"
            )
        assert result.exit_code == 0
        assert "added" in result.output.lower() or "success" in result.output.lower() or "new farm" in result.output.lower()

    def test_add_supplier_help(self, runner):
        result = runner.invoke(main, ["add-supplier", "--help"])
        assert result.exit_code == 0


class TestTopLevelHelp:
    def test_main_help_lists_commands(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        for cmd in ["search", "list-categories", "list-suppliers", "add-supplier"]:
            assert cmd in result.output
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'forest_cli.cli'`

**Step 3: Create `src/forest_cli/cli.py`**

```python
"""CLI entry point for forest-cli."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich import box

from forest_cli.db import (
    get_connection,
    search_suppliers,
    supplier_detail,
    list_categories,
    list_suppliers,
    add_supplier,
)

console = Console()


@click.group()
def main() -> None:
    """Find local Sarasota suppliers for your food forest."""


@main.command()
@click.argument("query")
def search(query: str) -> None:
    """Search suppliers by item name or category (substring, case-insensitive).

    QUERY: word or phrase to search for (e.g. 'wax myrtle', 'mango', 'drip tape')
    """
    conn = get_connection()
    results = search_suppliers(conn, query)

    if not results:
        console.print(f"[yellow]No suppliers found for '[bold]{query}[/bold]'.[/yellow]")
        return

    console.print(f"\n[green bold]Found {len(results)} supplier(s) matching '[italic]{query}[/italic]':[/green bold]\n")

    for row in results:
        detail = supplier_detail(conn, row["id"])
        _print_supplier_card(detail)


@main.command("list-categories")
def list_categories_cmd() -> None:
    """List all available supply categories."""
    conn = get_connection()
    cats = list_categories(conn)
    console.print("\n[bold cyan]Available categories:[/bold cyan]")
    for cat in cats:
        console.print(f"  [green]•[/green] {cat}")
    console.print()


@main.command("list-suppliers")
@click.option("--category", default=None, help="Filter by category name (e.g. plants, irrigation).")
def list_suppliers_cmd(category: str | None) -> None:
    """List all suppliers, optionally filtered by --category."""
    conn = get_connection()
    suppliers = list_suppliers(conn, category=category)

    if not suppliers:
        msg = f"No suppliers found for category '[bold]{category}[/bold]'." if category else "No suppliers found."
        console.print(f"[yellow]{msg}[/yellow]")
        return

    table = Table(title="Sarasota Food Forest Suppliers", box=box.ROUNDED)
    table.add_column("Name", style="bold cyan", no_wrap=False)
    table.add_column("Address", style="dim")
    table.add_column("Phone", style="green")
    table.add_column("Website", style="blue")

    for s in suppliers:
        table.add_row(
            s["name"] or "",
            s["address"] or "",
            s["phone"] or "",
            s["website"] or "",
        )

    console.print()
    console.print(table)
    console.print()


@main.command("add-supplier")
def add_supplier_cmd() -> None:
    """Interactively add a new supplier to the database."""
    console.print("[bold cyan]Add a new supplier[/bold cyan]\n")

    name = click.prompt("Supplier name")
    address = click.prompt("Address", default="")
    phone = click.prompt("Phone", default="")
    website = click.prompt("Website", default="")
    cats_input = click.prompt("Categories (comma-separated, e.g. plants,fruit_trees)")
    items_input = click.prompt("Items carried (comma-separated)")

    categories = [c.strip() for c in cats_input.split(",") if c.strip()]
    items = [i.strip() for i in items_input.split(",") if i.strip()]

    conn = get_connection()
    supplier_id = add_supplier(conn, name, address, phone, website, categories, items)

    console.print(f"\n[green bold]✓ Added '[italic]{name}[/italic]' (id={supplier_id})[/green bold]")


def _print_supplier_card(detail: dict) -> None:
    """Print a Rich-formatted supplier card."""
    panel_content = []
    if detail.get("address"):
        panel_content.append(f"[dim]Address:[/dim]  {detail['address']}")
    if detail.get("phone"):
        panel_content.append(f"[dim]Phone:[/dim]    [green]{detail['phone']}[/green]")
    if detail.get("website"):
        panel_content.append(f"[dim]Website:[/dim]  [blue]{detail['website']}[/blue]")
    if detail.get("categories"):
        panel_content.append(f"[dim]Categories:[/dim] {', '.join(detail['categories'])}")
    if detail.get("items"):
        panel_content.append(f"[dim]Items:[/dim]    {', '.join(detail['items'])}")

    console.rule(f"[bold cyan]{detail['name']}[/bold cyan]")
    for line in panel_content:
        console.print(f"  {line}")
    console.print()
```

**Step 4: Run tests**

```bash
pytest tests/test_cli.py -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add src/forest_cli/cli.py tests/test_cli.py
git commit -m "feat: add CLI commands search, list-categories, list-suppliers, add-supplier"
```

---

## Task 4: Integration smoke test

**Files:**
- Modify: `tests/test_cli.py` — add one integration test using real in-memory DB

**Step 1: Add integration test at bottom of `tests/test_cli.py`**

```python
# --- Integration tests (real in-memory DB, no mocks) ---
# `db` fixture comes from conftest.py — already initialized and seeded.

class TestIntegration:
    """Smoke tests against real seeded DB (no mocks)."""

    @pytest.fixture
    def int_runner(self):
        return CliRunner(mix_stderr=False)

    def test_search_wax_myrtle_returns_results(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0
        assert "Wax Myrtle" in result.output or "Wilsons" in result.output or "Sweet Bay" in result.output

    def test_search_nonexistent_exits_zero(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "xyzzy_nonexistent_9999"])
        assert result.exit_code == 0

    def test_list_categories_shows_five_categories(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["list-categories"])
        assert result.exit_code == 0
        for cat in ["plants", "fruit_trees", "irrigation", "seeds", "livestock"]:
            assert cat in result.output
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add integration smoke tests against real seeded DB"
```

---

## Task 5: Manual verification

**Step 1: Install and run**

```bash
pip install -e ".[dev]"
forest --help
forest list-categories
forest list-suppliers
forest list-suppliers --category irrigation
forest search "mango"
forest search "drip"
forest search "wax myrtle"
forest search "chicken"
forest search "xyzzy_does_not_exist"
```

Expected outputs:
- `forest list-categories` → prints 5 categories
- `forest list-suppliers` → table with 10 suppliers
- `forest list-suppliers --category irrigation` → 2-3 irrigation suppliers
- `forest search "mango"` → J&P Tropicals, Sweet Bay Nursery
- `forest search "drip"` → Ewing, SiteOne, Suncoast Hydroponics
- `forest search "wax myrtle"` → Wilsons, Sweet Bay, Sarasota Extension
- `forest search "chicken"` → Tractor Supply, Myakka City Feed
- `forest search "xyzzy_does_not_exist"` → "No suppliers found" message, exit 0

**Step 2: Test `add-supplier` interactively**

```bash
forest add-supplier
```

Enter: `Test Farm | 1 Test Rd | (941) 000-0000 | https://test.com | plants | Blueberry`

Expected: "Added 'Test Farm' (id=11)" and the supplier appears in `forest list-suppliers`.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: final verification complete"
```

---

## Summary

Total tasks: 5
Estimated time: 30-45 minutes
Test coverage: unit tests for db module, unit tests for all 4 CLI commands (mocked), integration smoke tests against real seeded DB, zero-results exits with code 0 (per approved testing strategy).
