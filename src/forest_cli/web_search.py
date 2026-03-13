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
        model="claude-haiku-4-5-20251001",
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
