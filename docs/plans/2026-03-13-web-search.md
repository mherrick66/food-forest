# Web Search Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use trycycle-executing to implement this plan task-by-task.

**Goal:** Add a `forest web-search` command that uses the Anthropic Claude API to find suppliers, complementing (not replacing) the existing local `forest search` command.

**Architecture:** A new `web_search.py` module calls the Anthropic Claude API with a structured prompt asking Claude to recall suppliers near Sarasota, FL from its training knowledge. Results are printed using the existing `_print_supplier_card()` helper (extended with an optional `ai_sourced` flag) to stay DRY. The local DB is never touched by this feature.

**Important framing:** This is not a live internet search — it queries Claude's training knowledge about local businesses. The command is still named `web-search` because it retrieves information not in the local DB, but all output is clearly labelled as AI-sourced so users know to verify. The CLI docstring must not claim "internet" access.

**Tech Stack:** Python 3.11+, `anthropic` SDK (>=0.25), `click`, `rich`, existing `forest_cli` package structure.

---

## Implementation Notes

### Claude API Strategy

Call `claude-3-5-haiku-20241022` (fast, cheap) with a system prompt asking it to list real local suppliers for a given item in the Sarasota, FL area. Claude's training data includes business listings and can synthesize plausible results. No `web_search` tool needed — a plain completion works and avoids needing extra API permissions.

API key: read from env var `ANTHROPIC_API_KEY`. If unset, raise `click.ClickException` and exit 1.

### Output Format

Results printed using the existing `_print_supplier_card()` in `cli.py`, extended with an optional `ai_sourced=False` parameter that appends `[dim italic]Source: AI-generated — verify before visiting[/dim italic]` after the normal card fields. This avoids duplicating 12 lines of Rich formatting logic. The web-search command passes `ai_sourced=True`.

**Why extend rather than duplicate:** `_print_supplier_card` already handles `None` values gracefully via `if detail.get(...)`. Web results simply lack `categories` and `items` keys — those `if` branches are skipped naturally. The only delta is the AI-sourced disclaimer line. Keeping one function makes both `search` and `web-search` consistent by construction.

### Response Parsing

Ask Claude to return JSON. Use a system prompt that requests a JSON array of supplier objects with keys: `name`, `address`, `phone`, `website`. Parse with `json.loads`. Strip markdown code fences if present. If parse fails, fall back to a `[{"_raw": <text>}]` sentinel list. The CLI displays the raw text with a warning in this case.

### Import Strategy

Import `anthropic` inside the `web_search_cmd` function body, not at module level. This avoids loading the heavy Anthropic SDK (and its transitive dependencies) for every invocation of `forest search`, `forest list-categories`, etc. `from forest_cli.web_search import search_web` at module level is fine — `web_search.py` itself only imports `json` and `typing`, both stdlib.

### Test Stderr Behaviour

The test suite uses `CliRunner(mix_stderr=False)`. In this mode, `ClickException` messages (and all stderr output) go to `result.stderr`, not `result.output`. Any test asserting on error messages **must** check `result.stderr`, not `result.output`. This is an established pattern in the existing suite (see `test_add_supplier_duplicate_name_exits_nonzero`).

---

## Task 1: Add `anthropic` dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add the dependency**

Edit `pyproject.toml`, add `"anthropic>=0.25"` to `dependencies`:

```toml
dependencies = [
    "click>=8.1,<8.2",
    "rich>=13.0",
    "anthropic>=0.25",
]
```

**Step 2: Install it**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && pip install -e ".[dev]"
```

Expected: `Successfully installed anthropic-...`

**Step 3: Verify import works**

```bash
python -c "import anthropic; print(anthropic.__version__)"
```

Expected: version number printed, no error.

**Step 4: Commit**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && git add pyproject.toml && git commit -m "feat: add anthropic dependency for web-search feature"
```

---

## Task 2: Create `web_search.py` module with Claude API call

**Files:**
- Create: `src/forest_cli/web_search.py`
- Create: `tests/test_web_search.py`

**Step 1: Write the failing test**

Create `tests/test_web_search.py`:

```python
# tests/test_web_search.py
import json
from unittest.mock import MagicMock
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
        # fallback: returns list with one dict containing raw '_raw' key
        assert isinstance(results, list)
        assert results[0].get("_raw") is not None

    def test_calls_claude_api_with_query_in_prompt(self):
        fake = [{"name": "X", "address": "", "phone": "", "website": ""}]
        client = _mock_client_response(fake)
        search_web(client, "jackfruit")
        call_kwargs = client.messages.create.call_args[1]
        # The query must appear somewhere in the messages list
        messages_str = str(call_kwargs.get("messages", ""))
        assert "jackfruit" in messages_str.lower()
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
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && git add src/forest_cli/web_search.py tests/test_web_search.py && git commit -m "feat: add web_search module with Claude API call and tests"
```

---

## Task 3: Wire `web-search` CLI command

**Files:**
- Modify: `src/forest_cli/cli.py`
- Modify: `tests/test_cli.py` (add new class)

**Step 1: Write the failing test**

Add to `tests/test_cli.py` (at end of file, before or after the last class). Note: `runner` fixture is already defined in this file; `monkeypatch` is a built-in pytest fixture. Both work as method parameters in a class-based test.

Note on stderr: `CliRunner(mix_stderr=False)` separates stdout and stderr. `click.ClickException` writes to stderr. Tests that assert on error messages use `result.stderr`. Tests that assert on successful output use `result.output` (stdout).

```python
class TestWebSearchCommand:
    # W-01: command exists and shows help
    def test_web_search_help(self, runner):
        result = runner.invoke(main, ["web-search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output or "query" in result.output.lower()

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

    # W-06: main help lists web-search command
    def test_main_help_includes_web_search(self, runner):
        result = runner.invoke(main, ["--help"])
        assert "web-search" in result.output

    # W-07: no stderr on successful web-search (consistent with TestNoStderr)
    def test_no_stderr_on_web_search(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        fake_results = [{"name": "Web Nursery", "address": "5 Web St", "phone": "(941) 555-9999", "website": "https://webnursery.com"}]
        with patch("forest_cli.cli.search_web", return_value=fake_results):
            result = runner.invoke(main, ["web-search", "moringa"])
        assert result.stderr == ""
```

**Step 2: Run test to verify it fails**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_cli.py::TestWebSearchCommand -v
```

Expected: `AttributeError` or `UsageError` — `web-search` command not found.

**Step 3: Write minimal implementation**

Edit `src/forest_cli/cli.py`:

**3a. Add import at top**, after existing imports:

```python
from forest_cli.web_search import search_web
```

Do NOT add `import anthropic` or `import os` at module level. Both are imported lazily inside `web_search_cmd` (see 3b). `search_web` itself only imports `json` — no heavy startup cost.

**3b. Add the `web-search` command** after `add_supplier_cmd`:

```python
@main.command("web-search")
@click.argument("query")
def web_search_cmd(query: str) -> None:
    """Ask Claude AI to recall local suppliers for QUERY near Sarasota, FL.

    QUERY: plant or item to search for (e.g. 'moringa', 'drip tape')

    Results come from Claude's training knowledge, not a live internet search.
    Requires ANTHROPIC_API_KEY environment variable.
    Results are AI-generated — verify before visiting.
    """
    import os
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise click.ClickException(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it to your Anthropic API key to use web-search."
        )

    client = anthropic.Anthropic(api_key=api_key)

    console.print(f"\n[cyan]Asking Claude about '[bold]{query}[/bold]' suppliers near Sarasota, FL...[/cyan]\n")

    results = search_web(client, query)

    if not results:
        console.print(f"[yellow]No suppliers found for '[bold]{query}[/bold]'.[/yellow]")
        return

    # Handle raw fallback
    if len(results) == 1 and "_raw" in results[0]:
        console.print("[yellow]Warning: Could not parse structured results. Raw response:[/yellow]")
        console.print(results[0]["_raw"])
        return

    console.print(f"[green bold]Found {len(results)} supplier(s) (AI-generated — verify before visiting):[/green bold]\n")

    for supplier in results:
        _print_supplier_card(supplier, ai_sourced=True)
```

**3c. Extend `_print_supplier_card`** at the bottom of `cli.py` to accept an `ai_sourced` parameter:

```python
def _print_supplier_card(detail: dict, *, ai_sourced: bool = False) -> None:
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
    if ai_sourced:
        panel_content.append("[dim italic]Source: AI-generated — verify before visiting[/dim italic]")

    console.rule(f"[bold cyan]{detail['name']}[/bold cyan]")
    for line in panel_content:
        console.print(f"  {line}")
    console.print()
```

**Why reuse `_print_supplier_card` instead of a separate helper:** The two card types are identical except for the AI disclaimer line. A second function would duplicate 12 lines of Rich formatting logic, creating two places to update if the card format ever changes. The keyword-only `ai_sourced` parameter adds zero noise to existing call sites (defaults to `False`) and makes the distinction explicit at the `web_search_cmd` call site (`ai_sourced=True`).

**Step 4: Run tests to verify they pass**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/test_cli.py::TestWebSearchCommand -v
```

Expected: All 7 tests PASS.

**Step 5: Run full test suite to check for regressions**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && python -m pytest tests/ -v
```

Expected: All existing tests pass, no regressions.

**Step 6: Commit**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && git add src/forest_cli/cli.py tests/test_cli.py && git commit -m "feat: add web-search command using Claude API"
```

---

## Task 4: Smoke test the live command

**Purpose:** Verify the command works end-to-end with a real API key. This is an acceptance check, not a development task — no code changes are expected. If the smoke test reveals a bug, fix it in a follow-up commit before declaring this task done.

**Step 1: Check if ANTHROPIC_API_KEY is set**

```bash
echo $ANTHROPIC_API_KEY | head -c 20
```

Expected: `sk-ant-...` (first 20 chars). If empty, this task cannot proceed — skip to the error-path test below and note that the live test was skipped.

**Step 2: Run live smoke test**

```bash
cd /home/mikeherrick/claude/food-forest/.worktrees/web-search && forest web-search "moringa"
```

Expected: Prints 1-8 supplier cards with name, address, phone, website fields. Each card ends with the `Source: AI-generated — verify before visiting` disclaimer. No Python tracebacks.

**Step 3: Test no-API-key error path**

```bash
ANTHROPIC_API_KEY="" forest web-search "moringa"
```

Expected: `Error: ANTHROPIC_API_KEY environment variable is not set.` printed to stderr, exit code 1.

**Step 4: If the smoke test found a bug, fix and commit**

Only commit if a real code defect was found and fixed:

```bash
git add -p
git commit -m "fix: address issues found in smoke testing web-search"
```
