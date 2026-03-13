# Forest CLI Test Plan

**Date:** 2026-03-12
**Implementation plan:** `docs/plans/2026-03-12-forest-cli.md`
**Harnesses:** pytest 8, Click `CliRunner(mix_stderr=False)`, SQLite in-memory seed fixture

## Overview

Tests are ordered: scenario → integration → boundary/edge → invariants → unit.

Shared fixture (`conftest.py`):
```python
@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    seed_db(conn)
    return conn
```

Test files:
- `tests/test_cli.py` — CLI scenario, integration, and edge tests
- `tests/test_db.py` — unit tests for query helpers
- `tests/test_live.py` — opt-in database integrity tests (`@pytest.mark.live`; excluded via `--ignore=tests/test_live.py`)

---

## Scenario Tests

These tests exercise complete user-visible behavior end-to-end (mocked DB layer, real Click routing).

---

### T-01: Search returns matching supplier name

| Field | Value |
|-------|-------|
| **Name** | `test_search_returns_supplier_name` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + `unittest.mock.patch` |
| **Preconditions** | `get_connection` patched; `search_suppliers` returns one fake supplier; `supplier_detail` returns full detail dict |
| **Actions** | `runner.invoke(main, ["search", "wax myrtle"])` |
| **Expected outcome** | `result.exit_code == 0`; `"Test Nursery"` appears in `result.output` |
| **Interactions** | `search_suppliers` called once; `supplier_detail` called once with supplier id |

---

### T-02: Search no results — exit code zero

| Field | Value |
|-------|-------|
| **Name** | `test_search_no_results_exits_zero` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `search_suppliers` patched to return `[]` |
| **Actions** | `runner.invoke(main, ["search", "xyzzy_nonexistent"])` |
| **Expected outcome** | `result.exit_code == 0` |
| **Interactions** | `search_suppliers` called once; `supplier_detail` never called |

---

### T-03: Search no results — friendly message

| Field | Value |
|-------|-------|
| **Name** | `test_search_no_results_prints_message` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `search_suppliers` patched to return `[]` |
| **Actions** | `runner.invoke(main, ["search", "xyzzy_nonexistent"])` |
| **Expected outcome** | `result.output` (lowercased) contains `"no suppliers"` or `"not found"` |
| **Interactions** | None beyond the search call |

---

### T-04: Search result shows contact info

| Field | Value |
|-------|-------|
| **Name** | `test_search_shows_contact_info` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `search_suppliers` returns fake supplier with phone `(941) 555-0001`, address `123 Main St`, website `testnursery.com`; `supplier_detail` returns full dict |
| **Actions** | `runner.invoke(main, ["search", "wax"])` |
| **Expected outcome** | `result.exit_code == 0`; `"(941) 555-0001"` in output; `"123 Main St"` in output; `"testnursery.com"` in output |
| **Interactions** | `supplier_detail` called once |

---

### T-05: Search result shows categories and items

| Field | Value |
|-------|-------|
| **Name** | `test_search_shows_categories_and_items` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `supplier_detail` returns dict with `categories: ["plants"]` and `items: ["Wax Myrtle"]` |
| **Actions** | `runner.invoke(main, ["search", "wax"])` |
| **Expected outcome** | `"plants"` in output; `"Wax Myrtle"` in output |
| **Interactions** | `supplier_detail` called once |

---

### T-06: Search with NULL website does not crash

| Field | Value |
|-------|-------|
| **Name** | `test_search_null_website_does_not_crash` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `supplier_detail` returns dict with `website: None` |
| **Actions** | `runner.invoke(main, ["search", "plants"])` |
| **Expected outcome** | `result.exit_code == 0`; no exception in output |
| **Interactions** | `_print_supplier_card` branches on `detail.get("website")` — must not raise |

---

### T-07: list-categories shows all five categories

| Field | Value |
|-------|-------|
| **Name** | `test_list_categories_shows_all_five` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `list_categories` patched to return `["fruit_trees", "irrigation", "livestock", "plants", "seeds"]` |
| **Actions** | `runner.invoke(main, ["list-categories"])` |
| **Expected outcome** | `result.exit_code == 0`; each of the five category strings appears in output |
| **Interactions** | `list_categories` called once |

---

### T-08: list-suppliers shows supplier names

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_shows_all` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `list_suppliers` patched to return one fake supplier |
| **Actions** | `runner.invoke(main, ["list-suppliers"])` |
| **Expected outcome** | `result.exit_code == 0`; `"Test Nursery"` in output |
| **Interactions** | `list_suppliers` called with `category=None` |

---

### T-09: list-suppliers --category passes filter through

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_category_filter_passed_through` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch with side-effect capture |
| **Preconditions** | `list_suppliers` patched with a capturing side-effect |
| **Actions** | `runner.invoke(main, ["list-suppliers", "--category", "plants"])` |
| **Expected outcome** | `result.exit_code == 0`; captured `category` argument equals `"plants"` |
| **Interactions** | `list_suppliers` called exactly once with `category="plants"` |

---

### T-10: list-suppliers no results for unknown category

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_no_results_for_unknown_category` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `list_suppliers` patched to return `[]` |
| **Actions** | `runner.invoke(main, ["list-suppliers", "--category", "nonexistent"])` |
| **Expected outcome** | `result.exit_code == 0`; output contains `"no suppliers"` or `"not found"` (case-insensitive) |
| **Interactions** | `list_suppliers` called once |

---

### T-11: add-supplier prompts, inserts, and confirms

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_prompts_and_inserts` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch; `runner.invoke` with `input=` |
| **Preconditions** | `add_supplier` patched to return `42` |
| **Actions** | `runner.invoke(main, ["add-supplier"], input="New Farm\n999 Farm Rd\n(941) 555-9999\nhttps://newfarm.com\nplants,seeds\nBlueberry, Strawberry\n")` |
| **Expected outcome** | `result.exit_code == 0`; `add_supplier` mock called exactly once |
| **Interactions** | All six `click.prompt` calls answered in sequence; `add_supplier` receives parsed categories list and items list |

---

### T-12: add-supplier shows success message

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_shows_success_message` |
| **Type** | Scenario |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch |
| **Preconditions** | `add_supplier` patched to return `7` |
| **Actions** | `runner.invoke(main, ["add-supplier"], input="New Farm\n999 Farm Rd\n(941) 555-9999\nhttps://newfarm.com\nplants\nBlueberry\n")` |
| **Expected outcome** | `result.exit_code == 0`; output (lowercased) contains `"added"` or `"success"` or `"new farm"` |
| **Interactions** | Output references the supplier name entered |

---

## Integration Tests

These tests use the real in-memory seeded DB with no mocks (only `get_connection` is patched to return the `db` fixture connection).

---

### T-13: Integration — search "wax myrtle" returns nursery results

| Field | Value |
|-------|-------|
| **Name** | `test_search_wax_myrtle_returns_results` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture (in-memory seeded); `get_connection` patched to return `db` |
| **Preconditions** | Seed data contains "Wax Myrtle" items linked to Wilsons Nursery, Sweet Bay Nursery, Sarasota County Extension Office |
| **Actions** | `runner.invoke(main, ["search", "wax myrtle"])` |
| **Expected outcome** | `result.exit_code == 0`; at least one of `"Wax Myrtle"`, `"Wilsons"`, `"Sweet Bay"` appears in output |
| **Interactions** | Real `search_suppliers`, `supplier_detail` called against in-memory DB |

---

### T-14: Integration — search nonexistent term exits zero

| Field | Value |
|-------|-------|
| **Name** | `test_search_nonexistent_exits_zero` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Seeded DB contains no item or category matching `"xyzzy_nonexistent_9999"` |
| **Actions** | `runner.invoke(main, ["search", "xyzzy_nonexistent_9999"])` |
| **Expected outcome** | `result.exit_code == 0`; output contains a friendly no-results message |
| **Interactions** | `search_suppliers` returns `[]`; `supplier_detail` not called |

---

### T-15: Integration — list-categories shows all five real categories

| Field | Value |
|-------|-------|
| **Name** | `test_list_categories_shows_five_categories` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | `seed_db` inserts all five categories |
| **Actions** | `runner.invoke(main, ["list-categories"])` |
| **Expected outcome** | `result.exit_code == 0`; each of `plants`, `fruit_trees`, `irrigation`, `seeds`, `livestock` in output |
| **Interactions** | Real `list_categories` called |

---

### T-16: Integration — search "mango" returns tropical fruit suppliers

| Field | Value |
|-------|-------|
| **Name** | `test_search_mango_returns_tropical_suppliers` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Seed data has "Mango tree" linked to J&P Tropicals and Sweet Bay Nursery |
| **Actions** | `runner.invoke(main, ["search", "mango"])` |
| **Expected outcome** | `result.exit_code == 0`; `"J&P Tropicals"` or `"Sweet Bay"` in output |
| **Interactions** | Real `search_suppliers` and `supplier_detail` |

---

### T-17: Integration — search "chicken" returns livestock suppliers

| Field | Value |
|-------|-------|
| **Name** | `test_search_chicken_returns_livestock_suppliers` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Seed data has "chickens" item under Tractor Supply Co. and "chicken feed" under Myakka City Feed |
| **Actions** | `runner.invoke(main, ["search", "chicken"])` |
| **Expected outcome** | `result.exit_code == 0`; `"Tractor Supply"` or `"Myakka"` in output |
| **Interactions** | Real `search_suppliers` and `supplier_detail` |

---

### T-18: Integration — list-suppliers --category irrigation returns subset

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_category_irrigation_returns_subset` |
| **Type** | Integration |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Seed data contains Ewing, SiteOne, Suncoast Hydroponics in irrigation category |
| **Actions** | `runner.invoke(main, ["list-suppliers", "--category", "irrigation"])` |
| **Expected outcome** | `result.exit_code == 0`; at least one of `"Ewing"`, `"SiteOne"`, `"Suncoast"` in output; output does not contain livestock-only suppliers |
| **Interactions** | Real `list_suppliers` called with `category="irrigation"` |

---

## Boundary and Edge Case Tests

---

### T-19: Search — empty string argument

| Field | Value |
|-------|-------|
| **Name** | `test_search_empty_string_exits_zero` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Empty string passed as query; `search_suppliers("")` will match all rows (LIKE `'%%'`) |
| **Actions** | `runner.invoke(main, ["search", ""])` |
| **Expected outcome** | `result.exit_code == 0`; no unhandled exception; output is either a result list or a friendly message |
| **Interactions** | `search_suppliers` called with `""` |

---

### T-20: Search — whitespace-only argument

| Field | Value |
|-------|-------|
| **Name** | `test_search_whitespace_only_exits_zero` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Query is `"   "` (spaces only) |
| **Actions** | `runner.invoke(main, ["search", "   "])` |
| **Expected outcome** | `result.exit_code == 0`; no exception raised |
| **Interactions** | `search_suppliers` called; SQL LIKE with `%   %` pattern |

---

### T-21: Search — SQL injection string does not crash

| Field | Value |
|-------|-------|
| **Name** | `test_search_sql_injection_does_not_crash` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; `db` fixture; `get_connection` patched |
| **Preconditions** | Query is `"'; DROP TABLE suppliers; --"` |
| **Actions** | `runner.invoke(main, ["search", "'; DROP TABLE suppliers; --"])` |
| **Expected outcome** | `result.exit_code == 0`; DB intact (suppliers table still queryable); output is friendly no-results or result list |
| **Interactions** | Parameterized query in `search_suppliers` prevents injection |

---

### T-22: Search — SQL injection does not destroy data

| Field | Value |
|-------|-------|
| **Name** | `test_search_sql_injection_db_intact` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seeded in-memory DB |
| **Actions** | Call `search_suppliers(db, "'; DROP TABLE suppliers; --")`; then `db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]` |
| **Expected outcome** | No exception; supplier count remains >= 5 |
| **Interactions** | Verifies parameterized query in `db.py` is safe |

---

### T-23: Search — missing DB path raises graceful error

| Field | Value |
|-------|-------|
| **Name** | `test_missing_db_path_raises_or_creates` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `tmp_path` fixture |
| **Preconditions** | Pass a path that does not exist to `get_connection` |
| **Actions** | `get_connection(tmp_path / "nonexistent" / "forest.db")` |
| **Expected outcome** | Either a new DB is created at that path with schema initialized (parent dirs created), OR a clear exception is raised — no silent data loss |
| **Interactions** | `get_connection` calls `path.parent.mkdir(parents=True, exist_ok=True)` |

---

### T-24: Supplier with NULL website — card renders

| Field | Value |
|-------|-------|
| **Name** | `test_supplier_null_website_renders_card` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_db.py` + `tests/test_cli.py` |
| **Harness** | `db` fixture; `CliRunner` |
| **Preconditions** | Seed data includes Sweet Bay Nursery with `website = NULL` and Myakka City Feed & Farm Supply with `website = NULL` |
| **Actions** | (db) `supplier_detail(db, id_of_sweet_bay)` — assert `detail["website"]` is `None`; (cli) `runner.invoke(main, ["search", "wax myrtle"])` with real DB |
| **Expected outcome** | `detail["website"] is None`; CLI exits 0 with no crash |
| **Interactions** | `_print_supplier_card` skips website line when `None` |

---

### T-25: Search — missing required argument exits non-zero

| Field | Value |
|-------|-------|
| **Name** | `test_search_requires_query_arg` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` |
| **Preconditions** | No patches needed |
| **Actions** | `runner.invoke(main, ["search"])` |
| **Expected outcome** | `result.exit_code != 0`; Click usage error in output |
| **Interactions** | Click argument validation; DB is never opened |

---

### T-26: add-supplier — categories comma-parsed correctly

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_categories_comma_parsed` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch with capturing side-effect |
| **Preconditions** | `add_supplier` patched to capture args |
| **Actions** | `runner.invoke(main, ["add-supplier"], input="X Farm\n\n\n\nplants, seeds\nBlueberry\n")` |
| **Expected outcome** | `result.exit_code == 0`; `categories` arg to mock is `["plants", "seeds"]` (stripped, no empty strings) |
| **Interactions** | CLI splits on comma and strips whitespace |

---

### T-27: add-supplier — items comma-parsed and stripped

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_items_comma_parsed` |
| **Type** | Boundary/Edge |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` + patch with capturing side-effect |
| **Preconditions** | `add_supplier` patched to capture args |
| **Actions** | `runner.invoke(main, ["add-supplier"], input="X Farm\n\n\n\nplants\nBlueberry, Strawberry, Loquat\n")` |
| **Expected outcome** | `result.exit_code == 0`; `items` arg is `["Blueberry", "Strawberry", "Loquat"]` |
| **Interactions** | CLI splits on comma and strips each item |

---

## Invariant Tests

These assertions must hold regardless of input.

---

### T-28: All CLI commands exit 0 on --help

| Field | Value |
|-------|-------|
| **Name** | `test_all_commands_help_exit_zero` (parametrized) |
| **Type** | Invariant |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; parametrize over `["--help"]`, `["search", "--help"]`, `["list-categories", "--help"]`, `["list-suppliers", "--help"]`, `["add-supplier", "--help"]` |
| **Preconditions** | None (no DB needed for --help) |
| **Actions** | `runner.invoke(main, args)` for each |
| **Expected outcome** | `result.exit_code == 0` for all |
| **Interactions** | Click help generation only |

---

### T-29: Top-level --help lists all four subcommands

| Field | Value |
|-------|-------|
| **Name** | `test_main_help_lists_commands` |
| **Type** | Invariant |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` |
| **Preconditions** | None |
| **Actions** | `runner.invoke(main, ["--help"])` |
| **Expected outcome** | `result.exit_code == 0`; all four of `search`, `list-categories`, `list-suppliers`, `add-supplier` appear in output |
| **Interactions** | Click group help |

---

### T-30: list-suppliers --help shows --category option

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_help_shows_category_option` |
| **Type** | Invariant |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` |
| **Preconditions** | None |
| **Actions** | `runner.invoke(main, ["list-suppliers", "--help"])` |
| **Expected outcome** | `result.exit_code == 0`; `"--category"` appears in output |
| **Interactions** | Click option declaration in `list_suppliers_cmd` |

---

### T-31: search --help mentions QUERY

| Field | Value |
|-------|-------|
| **Name** | `test_search_help_mentions_query` |
| **Type** | Invariant |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)` |
| **Preconditions** | None |
| **Actions** | `runner.invoke(main, ["search", "--help"])` |
| **Expected outcome** | `result.exit_code == 0`; `"QUERY"` or `"query"` appears in output |
| **Interactions** | Click argument declaration |

---

### T-32: stderr is empty on successful commands

| Field | Value |
|-------|-------|
| **Name** | `test_no_stderr_on_success` (parametrized for search/list-categories/list-suppliers) |
| **Type** | Invariant |
| **File** | `tests/test_cli.py` |
| **Harness** | `CliRunner(mix_stderr=False)`; patches return valid data |
| **Preconditions** | `mix_stderr=False` enables separate `result.stderr` access |
| **Actions** | Invoke each command; check `result.output` and `result.stderr` |
| **Expected outcome** | `result.stderr == ""` (or `result.stderr_bytes == b""`) on successful invocations |
| **Interactions** | Rich console writes to stdout; nothing written to stderr on clean path |

---

## Unit Tests

These test individual functions in `db.py` directly against the `db` fixture.

---

### T-33: init_db creates all four tables

| Field | Value |
|-------|-------|
| **Name** | `test_init_db_creates_tables` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | `db` fixture calls `init_db` and `seed_db` |
| **Actions** | `db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()` |
| **Expected outcome** | Result set contains `suppliers`, `categories`, `supplier_categories`, `items` |
| **Interactions** | `init_db` only; tests schema creation |

---

### T-34: seed_db populates suppliers (>= 5)

| Field | Value |
|-------|-------|
| **Name** | `test_seed_db_populates_suppliers` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seed data has 10 suppliers |
| **Actions** | `db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]` |
| **Expected outcome** | `count >= 5` |
| **Interactions** | `seed_db` |

---

### T-35: seed_db populates exactly five categories

| Field | Value |
|-------|-------|
| **Name** | `test_seed_db_populates_categories` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | None |
| **Actions** | `{row[0] for row in db.execute("SELECT name FROM categories").fetchall()}` |
| **Expected outcome** | Result equals `{"plants", "fruit_trees", "irrigation", "seeds", "livestock"}` exactly |
| **Interactions** | `seed_db` category inserts |

---

### T-36: search_suppliers by item name

| Field | Value |
|-------|-------|
| **Name** | `test_search_suppliers_by_item_name` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seed data has "Wax Myrtle" items |
| **Actions** | `search_suppliers(db, "wax myrtle")` |
| **Expected outcome** | `len(results) >= 1`; at least one result name contains `"nursery"`, `"wilsons"`, or `"sweet bay"` (case-insensitive) |
| **Interactions** | LIKE query on `items.name` |

---

### T-37: search_suppliers by category name

| Field | Value |
|-------|-------|
| **Name** | `test_search_suppliers_by_category` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seed data has irrigation suppliers |
| **Actions** | `search_suppliers(db, "irrigation")` |
| **Expected outcome** | `len(results) >= 1` |
| **Interactions** | LIKE query on `categories.name` |

---

### T-38: search_suppliers is case-insensitive

| Field | Value |
|-------|-------|
| **Name** | `test_search_suppliers_case_insensitive` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seed data has "Mango tree" items |
| **Actions** | `lower = search_suppliers(db, "mango")`; `upper = search_suppliers(db, "MANGO")` |
| **Expected outcome** | `len(lower) == len(upper)` and `len(lower) >= 1` |
| **Interactions** | `LOWER(i.name) LIKE ?` in SQL |

---

### T-39: search_suppliers no results returns empty list

| Field | Value |
|-------|-------|
| **Name** | `test_search_suppliers_no_results_returns_empty_list` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | No item or category in seed data matches `"xyzzy_nonexistent_item_99999"` |
| **Actions** | `search_suppliers(db, "xyzzy_nonexistent_item_99999")` |
| **Expected outcome** | `results == []` |
| **Interactions** | SQL returns no rows; function returns `[]` not `None` |

---

### T-40: list_categories returns all five names

| Field | Value |
|-------|-------|
| **Name** | `test_list_categories_returns_all_five` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | None |
| **Actions** | `set(list_categories(db))` |
| **Expected outcome** | Equals `{"plants", "fruit_trees", "irrigation", "seeds", "livestock"}` |
| **Interactions** | `list_categories` returns list of strings, sorted |

---

### T-41: list_suppliers no filter returns all

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_no_filter` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | 10 suppliers seeded |
| **Actions** | `list_suppliers(db)` |
| **Expected outcome** | `len(result) >= 5` |
| **Interactions** | No JOIN; full table scan |

---

### T-42: list_suppliers filtered by category returns subset

| Field | Value |
|-------|-------|
| **Name** | `test_list_suppliers_filtered_by_category` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Irrigation suppliers are a proper subset of all suppliers |
| **Actions** | `irrigation = list_suppliers(db, category="irrigation")`; `all_s = list_suppliers(db)` |
| **Expected outcome** | `len(irrigation) < len(all_s)`; `len(irrigation) >= 1` |
| **Interactions** | JOIN through `supplier_categories` and `categories` |

---

### T-43: supplier_detail returns categories and items

| Field | Value |
|-------|-------|
| **Name** | `test_supplier_detail_includes_categories_and_items` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Seed data for Ewing has irrigation items |
| **Actions** | Look up Ewing's id; call `supplier_detail(db, ewing_id)` |
| **Expected outcome** | `detail["categories"]` is a non-empty list containing `"irrigation"`; `detail["items"]` is a non-empty list containing at least one irrigation item (e.g., `"drip tape"`) |
| **Interactions** | `_supplier_categories` and `_supplier_items` helpers |

---

### T-44: add_supplier inserts and returns id

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_inserts_and_returns_id` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | None |
| **Actions** | `new_id = add_supplier(db, "Test Farm", "1 Farm Rd", "(941) 000-0000", "https://test.com", ["plants"], ["Blueberry"])`; then `db.execute("SELECT * FROM suppliers WHERE id = ?", (new_id,)).fetchone()` |
| **Expected outcome** | `new_id` is an integer; queried row has `name == "Test Farm"`; `db.execute("SELECT name FROM items WHERE supplier_id = ?", (new_id,)).fetchone()["name"] == "Blueberry"` |
| **Interactions** | `add_supplier` inserts into `suppliers`, `categories` (OR IGNORE), `supplier_categories`, `items` |

---

### T-45: add_supplier inserts new category if absent

| Field | Value |
|-------|-------|
| **Name** | `test_add_supplier_creates_new_category` |
| **Type** | Unit |
| **File** | `tests/test_db.py` |
| **Harness** | pytest; `db` fixture |
| **Preconditions** | Category `"mushrooms"` does not exist in seed data |
| **Actions** | `add_supplier(db, "Fungi Farm", "", "", "", ["mushrooms"], ["Oyster mushroom"])`; then `db.execute("SELECT name FROM categories WHERE name = 'mushrooms'").fetchone()` |
| **Expected outcome** | Row is not `None`; category `"mushrooms"` exists |
| **Interactions** | `INSERT OR IGNORE INTO categories` in `add_supplier` |

---

## Live / Integrity Tests (`test_live.py`)

These tests require the real on-disk database. Opt in by running `pytest tests/test_live.py`; excluded from default suite via `--ignore=tests/test_live.py`.

Mark all tests: `@pytest.mark.live`

---

### T-46: Live DB has expected supplier count

| Field | Value |
|-------|-------|
| **Name** | `test_live_db_supplier_count` |
| **Type** | Integrity |
| **File** | `tests/test_live.py` |
| **Harness** | pytest; `get_connection()` (real default path) |
| **Preconditions** | `~/.local/share/forest-cli/forest.db` exists and is seeded |
| **Actions** | `conn = get_connection(); count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]` |
| **Expected outcome** | `count >= 10` |
| **Interactions** | `get_connection` creates/seeds on first call |

---

### T-47: Live DB foreign key integrity

| Field | Value |
|-------|-------|
| **Name** | `test_live_db_fk_integrity` |
| **Type** | Integrity |
| **File** | `tests/test_live.py` |
| **Harness** | pytest |
| **Preconditions** | Live DB initialized |
| **Actions** | `conn.execute("PRAGMA foreign_key_check").fetchall()` |
| **Expected outcome** | Empty result (no FK violations) |
| **Interactions** | SQLite FK check pragma |

---

### T-48: Live DB all items have valid supplier references

| Field | Value |
|-------|-------|
| **Name** | `test_live_db_items_have_valid_suppliers` |
| **Type** | Integrity |
| **File** | `tests/test_live.py` |
| **Harness** | pytest |
| **Preconditions** | Live DB initialized |
| **Actions** | `conn.execute("SELECT COUNT(*) FROM items i LEFT JOIN suppliers s ON s.id = i.supplier_id WHERE s.id IS NULL").fetchone()[0]` |
| **Expected outcome** | Count equals `0` |
| **Interactions** | Items with dangling supplier_id references |

---

## conftest.py Reference

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

---

## Test Count Summary

| Category | Count |
|----------|-------|
| Scenario | 12 (T-01 – T-12) |
| Integration | 6 (T-13 – T-18) |
| Boundary/Edge | 9 (T-19 – T-27) |
| Invariant | 5 (T-28 – T-32) |
| Unit | 13 (T-33 – T-45) |
| Live/Integrity | 3 (T-46 – T-48) |
| **Total** | **48** |
