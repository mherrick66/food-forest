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

    def test_strips_markdown_code_fences(self):
        mock_content = MagicMock()
        mock_content.text = '```json\n[{"name": "Fence Nursery", "address": "", "phone": "", "website": ""}]\n```'
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        results = search_web(mock_client, "moringa")
        assert results[0]["name"] == "Fence Nursery"

    def test_non_list_json_returns_raw_fallback(self):
        mock_content = MagicMock()
        mock_content.text = '{"name": "Oops"}'
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        results = search_web(mock_client, "moringa")
        assert results[0].get("_raw") is not None

    def test_calls_correct_model(self):
        fake = [{"name": "X", "address": "", "phone": "", "website": ""}]
        client = _mock_client_response(fake)
        search_web(client, "moringa")
        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_max_tokens_at_least_512(self):
        fake = [{"name": "X", "address": "", "phone": "", "website": ""}]
        client = _mock_client_response(fake)
        search_web(client, "moringa")
        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] >= 512
