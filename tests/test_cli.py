# tests/test_cli.py
import pytest
from click.testing import CliRunner
from unittest.mock import patch
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


# --- Scenario Tests ---

class TestSearchCommand:
    # T-01
    def test_search_returns_supplier_name(self, runner):
        with patch("forest_cli.cli.get_connection") as mock_conn, \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value={**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}):
            result = runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0
        assert "Test Nursery" in result.output

    # T-02
    def test_search_no_results_exits_zero(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=[]):
            result = runner.invoke(main, ["search", "xyzzy_nonexistent"])
        assert result.exit_code == 0

    # T-03
    def test_search_no_results_prints_message(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=[]):
            result = runner.invoke(main, ["search", "xyzzy_nonexistent"])
        assert "no suppliers" in result.output.lower() or "not found" in result.output.lower()

    # T-04
    def test_search_shows_contact_info(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "wax"])
        assert "(941) 555-0001" in result.output
        assert "123 Main St" in result.output
        assert "testnursery.com" in result.output

    # T-05
    def test_search_shows_categories_and_items(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "wax"])
        assert "plants" in result.output
        assert "Wax Myrtle" in result.output

    # T-06
    def test_search_null_website_does_not_crash(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "website": None, "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=[{**FAKE_SUPPLIERS[0], "website": None}]), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "plants"])
        assert result.exit_code == 0

    # T-25
    def test_search_requires_query_arg(self, runner):
        result = runner.invoke(main, ["search"])
        assert result.exit_code != 0

    # T-31
    def test_search_help(self, runner):
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output or "query" in result.output.lower()


class TestListCategoriesCommand:
    # T-07
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
    # T-08
    def test_list_suppliers_shows_all(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_suppliers", return_value=FAKE_SUPPLIERS):
            result = runner.invoke(main, ["list-suppliers"])
        assert result.exit_code == 0
        assert "Test Nursery" in result.output

    # T-09
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

    # T-10
    def test_list_suppliers_no_results_for_unknown_category(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_suppliers", return_value=[]):
            result = runner.invoke(main, ["list-suppliers", "--category", "nonexistent"])
        assert result.exit_code == 0
        assert "no suppliers" in result.output.lower() or "not found" in result.output.lower()

    # T-30
    def test_list_suppliers_help_shows_category_option(self, runner):
        result = runner.invoke(main, ["list-suppliers", "--help"])
        assert result.exit_code == 0
        assert "--category" in result.output


class TestAddSupplierCommand:
    # T-11
    def test_add_supplier_prompts_and_inserts(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", return_value=42) as mock_add:
            result = runner.invoke(
                main, ["add-supplier"],
                input="New Farm\n999 Farm Rd\n(941) 555-9999\nhttps://newfarm.com\nplants,seeds\nBlueberry, Strawberry\n"
            )
        assert result.exit_code == 0
        mock_add.assert_called_once()

    # T-12
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

    # T-26
    def test_add_supplier_categories_comma_parsed(self, runner):
        captured = {}

        def _capture(conn, name, address, phone, website, categories, items):
            captured["categories"] = categories
            captured["items"] = items
            return 99

        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", side_effect=_capture):
            result = runner.invoke(
                main, ["add-supplier"],
                input="X Farm\n\n\n\nplants, seeds\nBlueberry\n"
            )
        assert result.exit_code == 0
        assert captured["categories"] == ["plants", "seeds"]

    # T-27
    def test_add_supplier_items_comma_parsed(self, runner):
        captured = {}

        def _capture(conn, name, address, phone, website, categories, items):
            captured["items"] = items
            return 99

        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", side_effect=_capture):
            result = runner.invoke(
                main, ["add-supplier"],
                input="X Farm\n\n\n\nplants\nBlueberry, Strawberry, Loquat\n"
            )
        assert result.exit_code == 0
        assert captured["items"] == ["Blueberry", "Strawberry", "Loquat"]

    def test_add_supplier_duplicate_name_exits_nonzero(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.add_supplier", side_effect=ValueError("Supplier 'Dup Farm' already exists")):
            result = runner.invoke(
                main, ["add-supplier"],
                input="Dup Farm\n\n\n\nplants\nSomething\n"
            )
        assert result.exit_code != 0
        assert "already exists" in result.output or "already exists" in result.stderr


# --- Invariant Tests ---

class TestTopLevelHelp:
    # T-29
    def test_main_help_lists_commands(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        for cmd in ["search", "list-categories", "list-suppliers", "add-supplier", "web-search"]:
            assert cmd in result.output


# T-28
@pytest.mark.parametrize("args", [
    ["--help"],
    ["search", "--help"],
    ["list-categories", "--help"],
    ["list-suppliers", "--help"],
    ["add-supplier", "--help"],
    ["web-search", "--help"],
])
def test_all_commands_help_exit_zero(runner, args):
    result = runner.invoke(main, args)
    assert result.exit_code == 0


# T-32: stderr is empty on successful commands
class TestNoStderr:
    def test_no_stderr_on_search(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "wax"])
        assert result.stderr == ""

    def test_no_stderr_on_list_categories(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_categories", return_value=FAKE_CATEGORIES):
            result = runner.invoke(main, ["list-categories"])
        assert result.stderr == ""

    def test_no_stderr_on_list_suppliers(self, runner):
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.list_suppliers", return_value=FAKE_SUPPLIERS):
            result = runner.invoke(main, ["list-suppliers"])
        assert result.stderr == ""


# --- Boundary / Edge Case Tests ---

class TestBoundaryEdge:
    # T-19
    def test_search_empty_string_exits_zero(self, runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = runner.invoke(main, ["search", ""])
        assert result.exit_code == 0

    # T-20
    def test_search_whitespace_only_exits_zero(self, runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = runner.invoke(main, ["search", "   "])
        assert result.exit_code == 0

    # T-21
    def test_search_sql_injection_does_not_crash(self, runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = runner.invoke(main, ["search", "'; DROP TABLE suppliers; --"])
        assert result.exit_code == 0

    # T-24 (CLI side)
    def test_supplier_null_website_renders_card(self, runner, db):
        # Sweet Bay Nursery has website=NULL in seed data
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0


# --- Integration Tests (real in-memory DB, no mocks except get_connection) ---

class TestIntegration:
    """Smoke tests against real seeded DB (no mocks)."""

    @pytest.fixture
    def int_runner(self):
        return CliRunner(mix_stderr=False)

    # T-13
    def test_search_wax_myrtle_returns_results(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0
        assert "Wax Myrtle" in result.output or "Wilsons" in result.output or "Sweet Bay" in result.output

    # T-14
    def test_search_nonexistent_exits_zero(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "xyzzy_nonexistent_9999"])
        assert result.exit_code == 0

    # T-15
    def test_list_categories_shows_five_categories(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["list-categories"])
        assert result.exit_code == 0
        for cat in ["plants", "fruit_trees", "irrigation", "seeds", "livestock"]:
            assert cat in result.output

    # T-16
    def test_search_mango_returns_tropical_suppliers(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "mango"])
        assert result.exit_code == 0
        assert "J&P Tropicals" in result.output or "Sweet Bay" in result.output

    # T-17
    def test_search_chicken_returns_livestock_suppliers(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["search", "chicken"])
        assert result.exit_code == 0
        assert "Tractor Supply" in result.output or "Myakka" in result.output

    # T-18
    def test_list_suppliers_category_irrigation_returns_subset(self, int_runner, db):
        with patch("forest_cli.cli.get_connection", return_value=db):
            result = int_runner.invoke(main, ["list-suppliers", "--category", "irrigation"])
        assert result.exit_code == 0
        assert "Ewing" in result.output or "SiteOne" in result.output or "Suncoast" in result.output


class TestWebSearchCommand:
    # W-02: missing ANTHROPIC_API_KEY prints error to stderr and exits nonzero
    def test_web_search_no_api_key_exits_nonzero(self, runner, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code != 0
        # ClickException writes to stderr when mix_stderr=False
        assert "ANTHROPIC_API_KEY" in result.stderr or "api key" in result.stderr.lower()

    # W-03: successful search prints supplier name to stdout
    def test_web_search_prints_supplier_name(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Web Nursery", "address": "5 Web St", "phone": "(941) 555-9999", "website": "https://webnursery.com"}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code == 0
        assert "Web Nursery" in result.output

    # W-04: zero results shows informative message
    def test_web_search_no_results_message(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with patch("forest_cli.cli.search_web", return_value=[]):
            result = runner.invoke(main, ["web-search", "xyzzy_impossible"])
        assert result.exit_code == 0
        assert "no" in result.output.lower() or "not found" in result.output.lower()

    # W-05: raw fallback result prints warning and raw text to stdout
    def test_web_search_raw_fallback_prints_warning(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with patch("forest_cli.cli.search_web", return_value=[{"_raw": "some raw text"}]):
            result = runner.invoke(main, ["web-search", "avocado"])
        assert result.exit_code == 0
        # Warning message and raw text both go to stdout (not ClickException)
        assert "raw" in result.output.lower() or "some raw text" in result.output

    # W-06: AI disclaimer is printed for each result card
    def test_web_search_prints_ai_disclaimer(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Web Nursery", "address": "5 Web St", "phone": "(941) 555-9999", "website": "https://webnursery.com"}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code == 0
        # The ai_sourced disclaimer must appear — this is the key differentiator from local search
        assert "AI-generated" in result.output or "verify before visiting" in result.output.lower()

    # W-07: no stderr on successful web-search (consistent with TestNoStderr)
    def test_no_stderr_on_web_search(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Web Nursery", "address": "5 Web St", "phone": "(941) 555-9999", "website": "https://webnursery.com"}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.stderr == ""

    # W-08: search_web not called when API key is missing
    def test_web_search_no_api_key_does_not_call_search_web(self, runner, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("forest_cli.cli.search_web") as mock_search_web:
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code != 0
        mock_search_web.assert_not_called()

    # W-09: missing query arg exits nonzero
    def test_web_search_requires_query_arg(self, runner):
        result = runner.invoke(main, ["web-search"])
        assert result.exit_code != 0

    # W-10: multiple results — all names printed
    def test_web_search_multiple_results(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [
            {"name": "Nursery One", "address": "1 St", "phone": "", "website": ""},
            {"name": "Nursery Two", "address": "2 St", "phone": "", "website": ""},
            {"name": "Nursery Three", "address": "3 St", "phone": "", "website": ""},
        ]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "avocado"])
        assert result.exit_code == 0
        assert "Nursery One" in result.output
        assert "Nursery Two" in result.output
        assert "Nursery Three" in result.output

    # W-11: empty string optional fields do not crash
    def test_web_search_empty_optional_fields(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Minimal Nursery", "address": "", "phone": "", "website": ""}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code == 0
        assert "Minimal Nursery" in result.output

    # W-12: None values for optional fields do not crash
    def test_web_search_none_optional_fields(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Null Nursery", "address": None, "phone": None, "website": None}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code == 0
        assert "Null Nursery" in result.output

    # R-01: local search does not print AI disclaimer (regression)
    def test_local_search_no_ai_disclaimer(self, runner):
        detail = {**FAKE_SUPPLIERS[0], "categories": ["plants"], "items": ["Wax Myrtle"]}
        with patch("forest_cli.cli.get_connection"), \
             patch("forest_cli.cli.search_suppliers", return_value=FAKE_SUPPLIERS), \
             patch("forest_cli.cli.supplier_detail", return_value=detail):
            result = runner.invoke(main, ["search", "wax myrtle"])
        assert result.exit_code == 0
        assert "AI-generated" not in result.output
        assert "verify before visiting" not in result.output.lower()

    # R-02: anthropic not imported at module level (regression)
    def test_anthropic_not_imported_at_module_level(self):
        import sys
        import subprocess
        # Run in a fresh subprocess so sys.modules is clean
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; import forest_cli.cli; "
             "assert 'anthropic' not in sys.modules, "
             "'anthropic was imported at module level'"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"anthropic was imported at module level: {result.stderr}"
