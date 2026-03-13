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
        for cmd in ["search", "list-categories", "list-suppliers", "add-supplier"]:
            assert cmd in result.output


# T-28
@pytest.mark.parametrize("args", [
    ["--help"],
    ["search", "--help"],
    ["list-categories", "--help"],
    ["list-suppliers", "--help"],
    ["add-supplier", "--help"],
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
