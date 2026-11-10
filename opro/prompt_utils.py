# Copyright 2023 The OPRO Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The utility functions for prompting GPT, Qwen, DeepSeek, and Google Cloud models."""

import os
import time

import google.generativeai as palm
import openai

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass


def init_openai_env():
    """Load environment variables and initialize OpenAI configuration."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and (not getattr(openai, "api_key", None) or openai.api_key == ""):
        openai.api_key = api_key

    api_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
    if api_base:
        openai.api_base = api_base


def call_openai_server_single_prompt(
    prompt,
    model="gpt-3.5-turbo",
    max_decode_steps=20,
    temperature=0.8,
    extra_body=None,
    **extra_kwargs,
):
    """The function to call OpenAI server with an input string."""
    init_openai_env()

    request_params = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_decode_steps,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    # Merge extra_body / custom parameters (e.g., enable_thinking for Qwen)
    merged_extra = {}
    if extra_body and isinstance(extra_body, dict):
        merged_extra.update(extra_body)
    merged_extra.update(extra_kwargs)

    # Check ENABLE_THINKING env var if enable_thinking not explicitly passed
    if "enable_thinking" not in merged_extra:
        env_thinking = os.getenv("ENABLE_THINKING")
        if env_thinking is not None:
            merged_extra["enable_thinking"] = env_thinking.strip().lower() in (
                "true",
                "1",
                "yes",
            )

    # In OpenAI SDK 0.27.x, kwargs passed to ChatCompletion.create are serialized
    # directly into the top-level request body JSON.
    request_params.update(merged_extra)

    try:
        completion = openai.ChatCompletion.create(**request_params)
        choice = completion.choices[0]  # type: ignore
        message = choice.message
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")

        # In case thinking/reasoning model outputs only reasoning_content
        if not content:
            reasoning = getattr(message, "reasoning_content", None)
            if reasoning is None and isinstance(message, dict):
                reasoning = message.get("reasoning_content")
            if reasoning:
                content = reasoning

        return content or ""

    except openai.error.AuthenticationError as e:  # type: ignore
        print(f"Authentication error: {e}. Please check your OPENAI_API_KEY in .env.")
        raise

    except openai.error.Timeout as e:  # type: ignore
        retry_time = e.retry_after if hasattr(e, "retry_after") else 30
        print(f"Timeout error occurred. Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )

    except openai.error.RateLimitError as e:  # type: ignore
        retry_time = e.retry_after if hasattr(e, "retry_after") else 30
        print(f"Rate limit exceeded. Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )

    except openai.error.APIError as e:  # type: ignore
        retry_time = e.retry_after if hasattr(e, "retry_after") else 30
        print(f"API error occurred: {e}. Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )

    except openai.error.APIConnectionError as e:  # type: ignore
        retry_time = e.retry_after if hasattr(e, "retry_after") else 30
        print(
            f"API connection error occurred: {e}. Retrying in {retry_time} seconds..."
        )
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )

    except openai.error.ServiceUnavailableError as e:  # type: ignore
        retry_time = e.retry_after if hasattr(e, "retry_after") else 30
        print(f"Service unavailable. Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )

    except OSError as e:
        retry_time = 5  # Adjust the retry time as needed
        print(f"Connection error occurred: {e}. Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_openai_server_single_prompt(
            prompt,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )


def call_openai_server_func(
    inputs,
    model="gpt-3.5-turbo",
    max_decode_steps=20,
    temperature=0.8,
    extra_body=None,
    **extra_kwargs,
):
    """The function to call OpenAI server with a list of input strings."""
    if isinstance(inputs, str):
        inputs = [inputs]
    outputs = []
    for input_str in inputs:
        output = call_openai_server_single_prompt(
            input_str,
            model=model,
            max_decode_steps=max_decode_steps,
            temperature=temperature,
            extra_body=extra_body,
            **extra_kwargs,
        )
        outputs.append(output)
    return outputs


def call_palm_server_from_cloud(
    input_text, model="text-bison-001", max_decode_steps=20, temperature=0.8
):
    """Calling the text-bison model from Cloud API."""
    assert isinstance(input_text, str)
    assert model == "text-bison-001"
    all_model_names = [
        m
        for m in palm.list_models()
        if "generateText" in m.supported_generation_methods
    ]
    model_name = all_model_names[0].name
    try:
        completion = palm.generate_text(
            model=model_name,
            prompt=input_text,
            temperature=temperature,
            max_output_tokens=max_decode_steps,
        )
        output_text = completion.result
        return [output_text]
    except:  # pylint: disable=bare-except  # noqa: E722
        retry_time = 10  # Adjust the retry time as needed
        print(f"Retrying in {retry_time} seconds...")
        time.sleep(retry_time)
        return call_palm_server_from_cloud(
            input_text, max_decode_steps=max_decode_steps, temperature=temperature
        )
