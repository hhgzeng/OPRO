"""Unit tests for prompt_utils OpenAI compatibility and parameter handling."""

import os
from unittest import mock
import openai
import pytest

from opro import prompt_utils


def test_init_openai_env():
  with mock.patch.dict(
      os.environ,
      {
          "OPENAI_API_KEY": "test-key-123",
          "OPENAI_API_BASE": "https://custom.endpoint.com/v1",
      },
  ):
    openai.api_key = None
    openai.api_base = "https://api.openai.com/v1"
    prompt_utils.init_openai_env()
    assert openai.api_key == "test-key-123"
    assert openai.api_base == "https://custom.endpoint.com/v1"


def test_call_openai_server_single_prompt_success():
  mock_response = mock.MagicMock()
  mock_choice = mock.MagicMock()
  mock_choice.message.content = "42"
  mock_choice.message.reasoning_content = None
  mock_response.choices = [mock_choice]

  with mock.patch.object(
      openai.ChatCompletion, "create", return_value=mock_response
  ) as mock_create:
    res = prompt_utils.call_openai_server_single_prompt(
        prompt="What is the answer?",
        model="qwen3.8-max-0902",
        max_decode_steps=50,
        temperature=0.7,
        extra_body={"enable_thinking": False},
    )
    assert res == "42"
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["model"] == "qwen3.8-max-0902"
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["max_tokens"] == 50
    assert call_kwargs["enable_thinking"] is False


def test_call_openai_server_single_prompt_fallback_to_reasoning():
  mock_response = mock.MagicMock()
  mock_choice = mock.MagicMock()
  mock_choice.message.content = ""
  mock_choice.message.reasoning_content = "Thinking concluded: the result is 100."
  mock_response.choices = [mock_choice]

  with mock.patch.object(
      openai.ChatCompletion, "create", return_value=mock_response
  ):
    res = prompt_utils.call_openai_server_single_prompt(
        prompt="Calculate something",
        model="qwen3.8-max-0902",
    )
    assert "Thinking concluded" in res


def test_call_openai_server_single_prompt_env_thinking():
  mock_response = mock.MagicMock()
  mock_choice = mock.MagicMock()
  mock_choice.message.content = "OK"
  mock_response.choices = [mock_choice]

  with mock.patch.dict(os.environ, {"ENABLE_THINKING": "false"}):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_response
    ) as mock_create:
      res = prompt_utils.call_openai_server_single_prompt("Test prompt")
      assert res == "OK"
      call_kwargs = mock_create.call_args[1]
      assert call_kwargs["enable_thinking"] is False
