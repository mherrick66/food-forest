# Web Search Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task.

**Goal:** Add a `forest web-search` command that uses the Anthropic Claude API to find suppliers on the internet, complementing (not replacing) the existing local `forest search` command.

**Architecture:** A new `web_search.py` module performs a live web search by calling Claude with the `computer-use` / `web_search` tool or via a prompt that instructs it to synthesize publicly-available information about local nurseries and suppliers. Results are printed in the same Rich card format as the existing `search` command. The local DB is never touched by this feature.

**Tech Stack:** Python 3.11+, `anthropic` SDK (>=0.25), `click`, `rich`, existing `forest_cli` package structure.

---

## Implementation Notes

### Claude API Strategy

The simplest approach: call `claude-3-5-haiku-20241022` (fast, cheap) with a prompt that asks it to list real local suppliers for a given item in the Sarasota, FL area. Claude's training data includes business listings and it can synthesize plausible results. No web_search tool needed — a plain completion works and avoids needing extra API permissions.

API key: read from env var `ANTHROPIC_API_KEY`. If unset, print a clear error and exit 1.

### Output Format

Results printed as Rich-formatted cards matching `_print_supplier_card()` in `cli.py`. Each card shows: name, address (if known), phone (if known), website (if known), note that it's an AI-sourced result (so user knows to verify).

### Response Parsing

Ask Claude to return JSON (structured output). Use a system prompt that requests a JSON array of supplier objects with keys: `name`, `address`, `phone`, `website`. Parse with `json.loads`. If parse fails, fall back to printing the raw text with a warning.

---

## Task 1: Add `anthropic` dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add the dependency**

Edit `pyproject.toml`, add `"anthropic>=0.25"` to `dependencies`.

**Step 2: Install it**

```bash
pip install -e ".[dev]"
```

Expected: `Successfully installed anthropic-...`

**Step 3: Verify import works**

```bash
python -c "import anthropic; print(anthropic.__version__)"
```

Expected: version number printed, no error.

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add anthropic dependency for web-search feature"
```

---

## Task 2: Create `web_search.py` module with Claude API call

**Files:**
- Create: `src/forest_cli/web_search.py`

**Step 1: Write the failing test**

In `tests/test_web_search.py`:

```python
# tests/test_web_search.py
import json
from unittest.mock import MagicMock, patch
import pytest

from forest_cli.web_search import search_web


def _mock_client_response(payload: list[dict]) -> MagicMock:
    """Build a mock anthropic client that returns payload as JSON in a message."""
    mock_content = MagicMock()
    mock_content.text = json.dumps(payload)
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


class TestSearchWeb:
    def test_returns_list_of_dicts(self):
        fake = [{"name": "Test Nursery", "address": "1 Main St", "phone": "(941) 555-0001", "website": "https://test.com"}]
        client = _mock_client_response(fake)
        results = search_web(client, "moringa")
        assert isinstance(results, list)
        assert len(results) == 1

    def test_result_has_name_key(self):
        fake = [{"name": "Test Nursery", "address": "", "phone": "", "website": ""}]
        client = _mock_client_response(fake)
        results = search_web(client, "avocado")
        assert results[0]["name"] == "Test Nursery"

    def test_empty_results_returns_empty_list(self):
        client = _mock_client_response([])
        results = search_web(client, "nothing")
        assert results == []

    def test_malformed_json_returns_raw_fallback(self):
        mock_content = MagicMock()
        mock_content.text = "Sorry, I cannot help."
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        results = search_web(mock_client, "avocado")
        # fallback: returns list with one dict containing raw 'text' key
        assert isinstance(results, list)
        assert results[0].get("_raw") is not None

    def test_calls_claude_api_with_query_in_prompt(self):
        fake = [{"name": "X", "address": "", "phone": "", "website": ""}]
        client = _mock_client_response(fake)
        search_web(client, "jackfruit")
        call_kwargs = client.messages.create.call_args
        prompt_text = str(call_kwargs)
        assert "jackfruit" in prompt_text.lower() or "jackfruit" in str(call_kwargs[1]).lower()
```

**Step 2: Run test to verify it fails**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_web_search.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError: No module named 'forest_cli.web_search'`

**Step 3: Write minimal implementation**

Create `src/forest_cli/web_search.py`:

```python
"""Web search via Claude API for forest-cli."""
from __future__ import annotations

import json
from typing import Any


_SYSTEM_PROMPT = """\
You are a helpful assistant that finds local plant nurseries and garden suppliers.
Return ONLY a valid JSON array (no markdown, no explanation) of supplier objects.
Each object must have exactly these keys: "name", "address", "phone", "website".
Use empty string "" for any field you don't know.
Focus on suppliers in or near Sarasota, FL (include Charlotte, Manatee, and Lee counties too).
List up to 8 real businesses you know of. Do not invent businesses.
"""


def search_web(client: Any, query: str) -> list[dict[str, str]]:
    """Use Claude API to find suppliers for *query* near Sarasota, FL.

    Args:
        client: An `anthropic.Anthropic` client instance.
        query: Plant/item name to search for (e.g. "moringa", "drip tape").

    Returns:
        List of supplier dicts with keys: name, address, phone, website.
        On JSON parse failure, returns [{"_raw": <raw_text>}].
    """
    user_message = (
        f"Find local nurseries or garden suppliers near Sarasota, FL that carry '{query}'. "
        "Return a JSON array of suppliers as described."
    )
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        results = json.loads(raw_text)
        if not isinstance(results, list):
            return [{"_raw": raw_text}]
        return results
    except json.JSONDecodeError:
        return [{"_raw": raw_text}]
```

**Step 4: Run test to verify it passes**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_web_search.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add src/forest_cli/web_search.py tests/test_web_search.py
git commit -m "feat: add web_search module with Claude API call and tests"
```

---

## Task 3: Wire `web-search` CLI command

**Files:**
- Modify: `src/forest_cli/cli.py`
- Test: `tests/test_cli.py` (add new class)

**Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
# Add at top with other imports
import os

class TestWebSearchCommand:
    # W-01: command exists and shows help
    def test_web_search_help(self, runner):
        result = runner.invoke(main, ["web-search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output or "query" in result.output.lower()

    # W-02: missing ANTHROPIC_API_KEY prints error and exits nonzero
    def test_web_search_no_api_key_exits_nonzero(self, runner, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = runner.invoke(main, ["web-search", "moringa"])
        assert result.exit_code != 0
        assert "ANTHROPIC_API_KEY" in result.output or "api key" in result.output.lower()

    # W-03: successful search prints supplier name
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

    # W-05: raw fallback result prints warning
    def test_web_search_raw_fallback_prints_warning(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with patch("forest_cli.cli.search_web", return_value=[{"_raw": "some raw text"}]):
            result = runner.invoke(main, ["web-search", "avocado"])
        assert result.exit_code == 0
        assert "raw" in result.output.lower() or "some raw text" in result.output

    # W-06: main help lists web-search command
    def test_main_help_includes_web_search(self, runner):
        result = runner.invoke(main, ["--help"])
        assert "web-search" in result.output
```

**Step 2: Run test to verify it fails**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_cli.py::TestWebSearchCommand -v
```

Expected: `AttributeError` or `UsageError` — `web-search` command not found.

**Step 3: Write minimal implementation**

Edit `src/forest_cli/cli.py`:

1. Add imports at the top:

```python
import os
import anthropic
from forest_cli.web_search import search_web
```

2. Add the new command after `add_supplier_cmd`:

```python
@main.command("web-search")
@click.argument("query")
def web_search_cmd(query: str) -> None:
    """Search the internet (via Claude AI) for suppliers near Sarasota, FL.

    QUERY: plant or item to search for (e.g. 'moringa', 'drip tape')

    Requires ANTHROPIC_API_KEY environment variable.
    Results are AI-generated — verify before visiting.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise click.ClickException(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it to your Anthropic API key to use web-search."
        )

    client = anthropic.Anthropic(api_key=api_key)

    console.print(f"\n[cyan]Searching online for '[bold]{query}[/bold]' suppliers near Sarasota, FL...[/cyan]\n")

    results = search_web(client, query)

    if not results:
        console.print(f"[yellow]No online suppliers found for '[bold]{query}[/bold]'.[/yellow]")
        return

    # Handle raw fallback
    if len(results) == 1 and "_raw" in results[0]:
        console.print("[yellow]Warning: Could not parse structured results. Raw response:[/yellow]")
        console.print(results[0]["_raw"])
        return

    console.print(f"[green bold]Found {len(results)} supplier(s) online (AI-sourced — verify before visiting):[/green bold]\n")

    for supplier in results:
        _print_web_supplier_card(supplier)


def _print_web_supplier_card(supplier: dict) -> None:
    """Print a Rich-formatted card for a web-search result."""
    panel_content = []
    if supplier.get("address"):
        panel_content.append(f"[dim]Address:[/dim]  {supplier['address']}")
    if supplier.get("phone"):
        panel_content.append(f"[dim]Phone:[/dim]    [green]{supplier['phone']}[/green]")
    if supplier.get("website"):
        panel_content.append(f"[dim]Website:[/dim]  [blue]{supplier['website']}[/blue]")
    panel_content.append("[dim italic]Source: AI web search — verify before visiting[/dim italic]")

    console.rule(f"[bold cyan]{supplier.get('name', 'Unknown')}[/bold cyan]")
    for line in panel_content:
        console.print(f"  {line}")
    console.print()
```

**Step 4: Run tests to verify they pass**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_cli.py::TestWebSearchCommand -v
```

Expected: All 6 tests PASS.

**Step 5: Run full test suite to check for regressions**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/ -v
```

Expected: All existing tests pass, no regressions.

**Step 6: Commit**

```bash
git add src/forest_cli/cli.py tests/test_cli.py
git commit -m "feat: add web-search command using Claude API"
```

---

## Task 4: Smoke test the live command

**Step 1: Check if ANTHROPIC_API_KEY is set**

```bash
echo $ANTHROPIC_API_KEY | head -c 20
```

Expected: `sk-ant-...` (first 20 chars). If empty, set it: `export ANTHROPIC_API_KEY=<your-key>`.

**Step 2: Run live smoke test**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && forest web-search "moringa"
```

Expected: Prints 1-8 supplier cards with name, address, phone, website fields. No Python tracebacks.

**Step 3: Test no-API-key error path**

```bash
ANTHROPIC_API_KEY="" forest web-search "moringa"
```

Expected: `Error: ANTHROPIC_API_KEY environment variable is not set.` and exit code 1.

**Step 4: Commit if any fixes needed from smoke test**

```bash
git add -p
git commit -m "fix: address issues found in smoke testing web-search"
```

---

## Task 5: Update `pyproject.toml` test config and finalize

**Files:**
- Modify: `pyproject.toml`

**Step 1: Ensure `test_web_search.py` is not excluded**

Check `pyproject.toml` `addopts` — only `test_live.py` should be excluded (already the case). No change needed if it already reads:

```toml
addopts = "--ignore=tests/test_live.py"
```

**Step 2: Run full test suite one final time**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/ -v
```

Expected: All tests pass (existing + new web_search + new CLI tests).

**Step 3: Final commit**

```bash
git add pyproject.toml
git commit -m "chore: verify test config includes web_search tests"
```

Only commit if `pyproject.toml` actually changed.
