# Web Search Feature — Test Plan

**Feature:** `forest web-search` command using Claude API to recall suppliers from training knowledge.
**Date:** 2026-03-13
**Fidelity:** Medium (agreed in session)

---

## Harness Requirements

No new harnesses need to be built. The existing harnesses from the food-forest test suite are sufficient:

### Harness 1: CLI harness — `CliRunner(mix_stderr=False)`
- **What it does:** Invokes Click commands in-process, captures stdout and stderr separately.
- **What it exposes:** `result.output` (stdout), `result.stderr` (stderr), `result.exit_code`.
- **Estimated complexity:** Already built (`tests/test_cli.py`, `runner` fixture in `conftest.py`).
- **Tests that depend on it:** W-01 through W-09, R-01 through R-04.

### Harness 2: Mock Anthropic client
- **What it does:** Replaces the `anthropic.Anthropic` client with a `MagicMock` that returns a controlled response, eliminating network calls and API key requirements in unit and CLI tests.
- **What it exposes:** `_mock_client_response(payload: list[dict])` helper that returns a mock client whose `messages.create()` returns a mock message with `content[0].text = json.dumps(payload)`.
- **Estimated complexity:** ~10 lines, built inline in `tests/test_web_search.py`. Already specified in the implementation plan.
- **Tests that depend on it:** W-01 through W-05 (unit), W-03 through W-08 (CLI via `patch("forest_cli.cli.search_web", ...)`).

### Harness 3: In-memory SQLite seed fixture (`db`)
- **What it does:** Provides an initialized and seeded SQLite in-memory database.
- **What it exposes:** `conn` passed to `get_connection` patches.
- **Estimated complexity:** Already built (`tests/conftest.py`).
- **Tests that depend on it:** R-01 through R-04.

---

## Test Plan

### Scenario Tests

---

**Test 1**
- **Name:** User runs `forest web-search "moringa"` and sees supplier cards with AI disclaimer
- **Type:** scenario
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", ...)`
- **Preconditions:** `ANTHROPIC_API_KEY` set to any non-empty string; `search_web` patched to return one valid supplier dict.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])` with `ANTHROPIC_API_KEY` set via `monkeypatch.setenv`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains the supplier name; `result.output` contains `"AI-generated"` or `"verify before visiting"` (the ai_sourced disclaimer from `_print_supplier_card(ai_sourced=True)`). Source of truth: implementation plan §Output Format — "appends `[dim italic]Source: AI-generated — verify before visiting[/dim italic]`".
- **Interactions:** `_print_supplier_card` (extended with `ai_sourced`), `search_web` import in `cli.py`.

---

**Test 2**
- **Name:** User runs `forest web-search "xyzzy_impossible"` and sees a "no suppliers" message
- **Type:** scenario
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", return_value=[])`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` returns empty list.
- **Actions:** `runner.invoke(main, ["web-search", "xyzzy_impossible"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains `"no"` (case-insensitive) or `"not found"`. Source of truth: user description — "shouldn't replace the existing local search" implies graceful zero-results handling; implementation plan `web_search_cmd` block — `console.print(f"[yellow]No suppliers found for ...")`.
- **Interactions:** early-return path in `web_search_cmd`.

---

**Test 3**
- **Name:** User runs `forest web-search` without ANTHROPIC_API_KEY set and gets a clear error
- **Type:** scenario
- **Harness:** CLI harness + `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)`
- **Preconditions:** `ANTHROPIC_API_KEY` not set in environment.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])`.
- **Expected outcome:** `result.exit_code != 0` (exit 1); `result.stderr` contains `"ANTHROPIC_API_KEY"` (case-sensitive) or `"api key"` (case-insensitive). No Python traceback in output. Source of truth: implementation plan — "If unset, raise `click.ClickException` and exit 1"; plan §Test Stderr Behaviour — `ClickException` writes to stderr with `mix_stderr=False`.
- **Interactions:** `os.environ.get` inside `web_search_cmd`, `click.ClickException` → stderr routing.

---

**Test 4**
- **Name:** User runs `forest web-search "avocado"` when Claude returns unparseable text and sees a raw fallback warning
- **Type:** scenario
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", return_value=[{"_raw": "Sorry, I cannot help."}])`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` returns raw fallback list.
- **Actions:** `runner.invoke(main, ["web-search", "avocado"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains `"raw"` (case-insensitive) or `"Sorry, I cannot help."`. No traceback. Source of truth: implementation plan §Response Parsing — "The CLI displays the raw text with a warning in this case."
- **Interactions:** `_raw` sentinel detection in `web_search_cmd`, raw fallback branch.

---

**Test 5**
- **Name:** User runs `forest web-search` alongside `forest search` and existing local search is unaffected
- **Type:** scenario
- **Harness:** CLI harness + in-memory SQLite seed fixture
- **Preconditions:** Seeded in-memory DB available; no `ANTHROPIC_API_KEY` needed for local search.
- **Actions:** `runner.invoke(main, ["search", "wax myrtle"])` with `patch("forest_cli.cli.get_connection", return_value=db)`.
- **Expected outcome:** `result.exit_code == 0`; output contains a known seeded supplier name (e.g. `"Wilsons"` or `"Sweet Bay"`); output does NOT contain `"AI-generated"` or `"verify before visiting"`. Source of truth: user description — "shouldn't replace the existing local search"; regression requirement that `_print_supplier_card` defaults `ai_sourced=False`.
- **Interactions:** `_print_supplier_card` called from `search` command without `ai_sourced` — verifies default parameter.

---

### Integration Tests

---

**Test 6**
- **Name:** `search_web` passes the query string to the Claude API messages payload
- **Type:** integration
- **Harness:** Mock Anthropic client (direct call, no CLI)
- **Preconditions:** Mock client built with `_mock_client_response([{"name": "X", "address": "", "phone": "", "website": ""}])`.
- **Actions:** Call `search_web(mock_client, "jackfruit")` directly.
- **Expected outcome:** `mock_client.messages.create` called exactly once; `str(call_kwargs["messages"])` contains `"jackfruit"` (case-insensitive). Source of truth: implementation plan §Claude API Strategy — "Ask Claude to list real local suppliers for a given item"; the prompt template in `web_search.py` must embed the query.
- **Interactions:** `search_web` → `client.messages.create` API boundary.

---

**Test 7**
- **Name:** `search_web` returns a list of dicts with expected keys on valid JSON response
- **Type:** integration
- **Harness:** Mock Anthropic client (direct call)
- **Preconditions:** Mock client returning `[{"name": "Test Nursery", "address": "1 Main St", "phone": "(941) 555-0001", "website": "https://test.com"}]`.
- **Actions:** `results = search_web(mock_client, "moringa")`.
- **Expected outcome:** `isinstance(results, list)` is `True`; `len(results) == 1`; `results[0]["name"] == "Test Nursery"`. Source of truth: implementation plan §Response Parsing — "Parse with `json.loads`"; return type documented as `list[dict[str, str]]`.
- **Interactions:** JSON parsing in `search_web`, mock message content extraction.

---

**Test 8**
- **Name:** `search_web` returns empty list when Claude returns empty JSON array
- **Type:** integration
- **Harness:** Mock Anthropic client (direct call)
- **Preconditions:** Mock client returning `[]`.
- **Actions:** `results = search_web(mock_client, "nothing")`.
- **Expected outcome:** `results == []`. Source of truth: implementation plan — "Returns: List of supplier dicts...".
- **Interactions:** Empty-list branch of `search_web`.

---

**Test 9**
- **Name:** `search_web` returns raw fallback sentinel when Claude returns non-JSON text
- **Type:** integration
- **Harness:** Mock Anthropic client returning `"Sorry, I cannot help."` as text (direct call)
- **Preconditions:** Mock content `.text = "Sorry, I cannot help."`.
- **Actions:** `results = search_web(mock_client, "avocado")`.
- **Expected outcome:** `isinstance(results, list)` is `True`; `results[0].get("_raw") is not None`. Source of truth: implementation plan §Response Parsing — "fall back to a `[{'_raw': <text>}]` sentinel list".
- **Interactions:** `json.JSONDecodeError` catch path in `search_web`.

---

**Test 10**
- **Name:** `search_web` strips markdown code fences before parsing JSON
- **Type:** integration
- **Harness:** Mock Anthropic client returning JSON wrapped in triple-backtick fences (direct call)
- **Preconditions:** Mock content `.text = "```json\n[{\"name\": \"Fence Nursery\", \"address\": \"\", \"phone\": \"\", \"website\": \"\"}]\n```"`.
- **Actions:** `results = search_web(mock_client, "moringa")`.
- **Expected outcome:** `results[0]["name"] == "Fence Nursery"` — parse succeeds without the raw fallback. Source of truth: implementation plan §Response Parsing — "Strip markdown code fences if present."
- **Interactions:** Code fence stripping logic in `search_web` before `json.loads`.

---

**Test 11**
- **Name:** `web-search` command does not call `search_web` when API key is missing
- **Type:** integration
- **Harness:** CLI harness + `monkeypatch.delenv` + `patch("forest_cli.cli.search_web")`
- **Preconditions:** `ANTHROPIC_API_KEY` not set.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])` with `search_web` patched.
- **Expected outcome:** `result.exit_code != 0`; patched `search_web` was NOT called (`mock_search_web.assert_not_called()`). Source of truth: implementation plan — API key check is the first action in `web_search_cmd`, before `search_web` is called.
- **Interactions:** Short-circuit guard in `web_search_cmd` before `anthropic.Anthropic` instantiation.

---

**Test 12**
- **Name:** `_print_supplier_card` omits AI disclaimer when called without `ai_sourced`
- **Type:** integration
- **Harness:** CLI harness
- **Preconditions:** `search_suppliers` patched to return one supplier; `supplier_detail` patched to return full detail dict.
- **Actions:** `runner.invoke(main, ["search", "wax myrtle"])`.
- **Expected outcome:** `result.output` does NOT contain `"AI-generated"` and does NOT contain `"verify before visiting"`. Source of truth: implementation plan §Output Format — "`ai_sourced=False` parameter...appends disclaimer only when `ai_sourced=True`". This is the critical regression check for the `_print_supplier_card` modification.
- **Interactions:** `_print_supplier_card` default parameter path; `search` command call site.

---

### Invariant Tests

---

**Test 13**
- **Name:** `forest --help` lists `web-search` among commands
- **Type:** invariant
- **Harness:** CLI harness
- **Preconditions:** Package installed from worktree.
- **Actions:** `runner.invoke(main, ["--help"])`.
- **Expected outcome:** `result.exit_code == 0`; all of `["search", "list-categories", "list-suppliers", "add-supplier", "web-search"]` appear in `result.output`. Source of truth: implementation plan §Task 3 — command registered as `@main.command("web-search")`.
- **Interactions:** Click group command registration.

---

**Test 14**
- **Name:** `forest web-search --help` exits zero and describes the command
- **Type:** invariant
- **Harness:** CLI harness
- **Preconditions:** None.
- **Actions:** `runner.invoke(main, ["web-search", "--help"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains `"QUERY"` or `"query"`. Source of truth: implementation plan §Task 3 — `@click.argument("query")` on `web_search_cmd`.
- **Interactions:** Click help generation.

---

**Test 15**
- **Name:** Successful `web-search` produces no output on stderr
- **Type:** invariant
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", ...)`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` patched to return one valid supplier dict.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])`.
- **Expected outcome:** `result.stderr == ""`. Source of truth: existing `TestNoStderr` invariant pattern — all successful commands produce empty stderr with `mix_stderr=False`.
- **Interactions:** `CliRunner(mix_stderr=False)` stderr routing.

---

### Boundary and Edge-Case Tests

---

**Test 16**
- **Name:** `forest web-search` without a query argument exits nonzero
- **Type:** boundary
- **Harness:** CLI harness
- **Preconditions:** None.
- **Actions:** `runner.invoke(main, ["web-search"])`.
- **Expected outcome:** `result.exit_code != 0`. Source of truth: implementation plan — `@click.argument("query")` is required (no `default`, no `required=False`).
- **Interactions:** Click argument validation.

---

**Test 17**
- **Name:** `search_web` returns raw fallback when Claude returns a JSON object instead of array
- **Type:** boundary
- **Harness:** Mock Anthropic client returning `{"name": "Oops"}` as text (direct call)
- **Preconditions:** Mock content `.text = '{"name": "Oops"}'`.
- **Actions:** `results = search_web(mock_client, "moringa")`.
- **Expected outcome:** `results[0].get("_raw") is not None`. Source of truth: implementation plan §Response Parsing — "If parse fails [or] not isinstance(results, list), return `[{'_raw': <text>}]`".
- **Interactions:** Non-list JSON parse guard in `search_web`.

---

**Test 18**
- **Name:** `web-search` with multiple results prints all supplier names
- **Type:** boundary
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", ...)`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` patched to return three supplier dicts.
- **Actions:** `runner.invoke(main, ["web-search", "avocado"])`.
- **Expected outcome:** `result.exit_code == 0`; all three supplier names appear in `result.output`. Source of truth: implementation plan `web_search_cmd` — `for supplier in results: _print_supplier_card(supplier, ai_sourced=True)`.
- **Interactions:** Loop over results in `web_search_cmd`, multiple `_print_supplier_card` calls.

---

**Test 19**
- **Name:** `web-search` result card with missing optional fields does not crash
- **Type:** boundary
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", ...)`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` returns `[{"name": "Minimal Nursery", "address": "", "phone": "", "website": ""}]`.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains `"Minimal Nursery"`. Source of truth: implementation plan §Output Format — "Web results simply lack `categories` and `items` keys — those `if` branches are skipped naturally."
- **Interactions:** `_print_supplier_card` empty-string and None-guard branches.

---

**Test 20**
- **Name:** `web-search` result card with `None` values for optional fields does not crash
- **Type:** boundary
- **Harness:** CLI harness + `patch("forest_cli.cli.search_web", ...)`
- **Preconditions:** `ANTHROPIC_API_KEY` set; `search_web` returns `[{"name": "Null Nursery", "address": None, "phone": None, "website": None}]`.
- **Actions:** `runner.invoke(main, ["web-search", "moringa"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains `"Null Nursery"`. Source of truth: implementation plan §Output Format — "`_print_supplier_card` already handles `None` values gracefully via `if detail.get(...)`".
- **Interactions:** `detail.get("address")` falsy-check branches in `_print_supplier_card`.

---

### Regression Tests

---

**Test 21**
- **Name:** Existing `forest search` command still returns supplier name and contact info after `_print_supplier_card` is extended
- **Type:** regression
- **Harness:** CLI harness + mocked `search_suppliers`, `supplier_detail`
- **Preconditions:** `search_suppliers` patched to return one supplier; `supplier_detail` patched to return full detail with address, phone, website.
- **Actions:** `runner.invoke(main, ["search", "wax myrtle"])`.
- **Expected outcome:** `result.exit_code == 0`; `result.output` contains supplier name, address, and phone. Source of truth: existing test T-04 (`test_search_shows_contact_info`) characterizes this behavior before the change.
- **Interactions:** `_print_supplier_card` with `ai_sourced=False` (default) — the most likely regression site.

---

**Test 22**
- **Name:** Importing `forest_cli.cli` does not import `anthropic` at module level
- **Type:** regression
- **Harness:** Direct Python import check (no CLI)
- **Preconditions:** `anthropic` package installed.
- **Actions:** `import sys; import forest_cli.cli; assert "anthropic" not in sys.modules`.
- **Expected outcome:** `"anthropic"` is not in `sys.modules` immediately after importing `forest_cli.cli` (before any command is invoked). Source of truth: implementation plan §Import Strategy — "Import `anthropic` inside the `web_search_cmd` function body, not at module level."
- **Interactions:** Module-level import chain; lazy-import guard for SDK startup cost.

---

**Test 23**
- **Name:** `forest search` produces no stderr after `web-search` command is added to the group
- **Type:** regression
- **Harness:** CLI harness + mocked `search_suppliers`, `supplier_detail`
- **Preconditions:** `search_suppliers` and `supplier_detail` patched with valid data.
- **Actions:** `runner.invoke(main, ["search", "wax myrtle"])`.
- **Expected outcome:** `result.stderr == ""`. Source of truth: existing `TestNoStderr::test_no_stderr_on_search` invariant — adding a new command to the group must not pollute stderr of existing commands.
- **Interactions:** Click group stderr routing after adding `web-search` command.

---

### Unit Tests

---

**Test 24**
- **Name:** `search_web` calls `client.messages.create` with the correct model name
- **Type:** unit
- **Harness:** Mock Anthropic client (direct call)
- **Preconditions:** Mock client set up with `_mock_client_response([{"name": "X", "address": "", "phone": "", "website": ""}])`.
- **Actions:** `search_web(mock_client, "moringa")`.
- **Expected outcome:** `mock_client.messages.create.call_args[1]["model"] == "claude-3-5-haiku-20241022"`. Source of truth: implementation plan §Claude API Strategy — "Call `claude-3-5-haiku-20241022`".
- **Interactions:** `messages.create` kwargs; model selection.

---

**Test 25**
- **Name:** `search_web` sets `max_tokens` to at least 512 in the API call
- **Type:** unit
- **Harness:** Mock Anthropic client (direct call)
- **Preconditions:** Mock client with any valid response.
- **Actions:** `search_web(mock_client, "moringa")`.
- **Expected outcome:** `mock_client.messages.create.call_args[1]["max_tokens"] >= 512`. Source of truth: implementation plan §Task 2 — `max_tokens=1024`. A floor assertion (not exact match) avoids brittleness to minor plan tweaks while catching a missing or near-zero value.
- **Interactions:** `messages.create` kwargs; token budget.

---

## Coverage Summary

### Areas covered

| Area | Tests |
|---|---|
| `forest web-search` happy path (returns results) | 1, 6, 7, 18 |
| `forest web-search` zero results | 2, 8 |
| Missing `ANTHROPIC_API_KEY` — error and exit 1 | 3, 11 |
| Raw fallback (`_raw` sentinel) | 4, 9, 17 |
| AI disclaimer on every result card | 1 |
| Markdown code fence stripping | 10 |
| `web-search` missing query arg | 16 |
| `search_web` query embedded in API prompt | 6 |
| `search_web` correct model and token settings | 24, 25 |
| `_print_supplier_card` extended with `ai_sourced` | 1, 12, 19, 20 |
| `web-search` in `--help` output | 13, 14 |
| No stderr on success | 15, 23 |
| Lazy `anthropic` import | 22 |
| Regression: existing `forest search` unaffected | 5, 12, 21, 23 |

### Explicitly excluded per agreed strategy

- **Live API calls:** All tests mock `search_web` or the Anthropic client. Live end-to-end testing (real `ANTHROPIC_API_KEY`, real Claude response) is excluded from the automated suite per the Medium fidelity agreement. The implementation plan covers this as a manual smoke test (Task 4). Risk: the JSON response shape from the live API could differ from mocks; this is mitigated by the code fence stripping and raw fallback sentinel.
- **Rate limit and network timeout behavior:** Not addressed. Risk: low for a local tool where the user controls invocation frequency.
- **Performance:** Not tested. The command issues a single API call; no latency regression risk relative to existing commands.
- **Content quality of AI-generated supplier data:** Out of scope. The feature is explicitly framed as recalling training knowledge, not verifying business data. The AI disclaimer disclaimer in output acknowledges this to the user.
