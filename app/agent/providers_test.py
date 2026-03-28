"""Tests for LLM provider abstraction — mocked, no real API calls."""

from unittest.mock import MagicMock, patch
import json

import pytest

from app.agent.providers import get_provider
from app.models import ToolName


_SAMPLE_TOOLS = [
    {
        "name": "categorize_transactions",
        "description": "Categorize transactions",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# --- get_provider ---


def test_get_provider_default():
    with patch.dict("os.environ", {}, clear=True):
        assert get_provider() == "gemini"


def test_get_provider_from_env():
    with patch.dict("os.environ", {"XELSIUS_LLM_PROVIDER": "groq"}):
        assert get_provider() == "groq"


def test_get_provider_anthropic():
    with patch.dict("os.environ", {"XELSIUS_LLM_PROVIDER": "anthropic"}):
        assert get_provider() == "anthropic"


# --- resolve_via_anthropic (mocked) ---


def test_anthropic_provider_returns_tool_call():
    from app.agent.providers import resolve_via_anthropic

    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.name = "categorize_transactions"
    mock_block.input = {}

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = resolve_via_anthropic("test prompt", "system", _SAMPLE_TOOLS, api_key="fake-key")
    assert result.tool == ToolName.CATEGORIZE_TRANSACTIONS
    assert result.args == {}


def test_anthropic_provider_no_tool_call_raises():
    from app.agent.providers import resolve_via_anthropic

    mock_block = MagicMock()
    mock_block.type = "text"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(ValueError, match="did not return a tool call"):
            resolve_via_anthropic("test", "system", _SAMPLE_TOOLS, api_key="fake-key")


def test_anthropic_provider_no_key_raises():
    with patch.dict("os.environ", {}, clear=True):
        from app.agent.providers import resolve_via_anthropic
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            resolve_via_anthropic("test", "system", _SAMPLE_TOOLS)


# --- resolve_via_groq (mocked) ---


def test_groq_provider_returns_tool_call():
    from app.agent.providers import resolve_via_groq

    mock_tc = MagicMock()
    mock_tc.function.name = "categorize_transactions"
    mock_tc.function.arguments = "{}"

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tc]

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("groq.Groq", return_value=mock_client):
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            result = resolve_via_groq("test", "system", _SAMPLE_TOOLS)
    assert result.tool == ToolName.CATEGORIZE_TRANSACTIONS
    assert result.args == {}


def test_groq_provider_with_args():
    from app.agent.providers import resolve_via_groq

    mock_tc = MagicMock()
    mock_tc.function.name = "categorize_transactions"
    mock_tc.function.arguments = json.dumps({"groupBy": "category"})

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tc]

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("groq.Groq", return_value=mock_client):
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            result = resolve_via_groq("test", "system", _SAMPLE_TOOLS)
    assert result.args == {"groupBy": "category"}


def test_groq_provider_no_tool_call_raises():
    from app.agent.providers import resolve_via_groq

    mock_message = MagicMock()
    mock_message.tool_calls = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("groq.Groq", return_value=mock_client):
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            with pytest.raises(ValueError, match="did not return a tool call"):
                resolve_via_groq("test", "system", _SAMPLE_TOOLS)


def test_groq_provider_no_key_raises():
    with patch.dict("os.environ", {}, clear=True):
        from app.agent.providers import resolve_via_groq
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            resolve_via_groq("test", "system", _SAMPLE_TOOLS)


# --- resolve_via_gemini (mocked) ---


def test_gemini_provider_no_key_raises():
    with patch.dict("os.environ", {}, clear=True):
        from app.agent.providers import resolve_via_gemini
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            resolve_via_gemini("test", "system", _SAMPLE_TOOLS)
