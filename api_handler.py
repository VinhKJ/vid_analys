"""Utilities for managing API keys and sending analysis requests.

This module defines a simple API manager that can rotate through a list
of provided API keys. If one key exceeds its daily usage limit, it can
be disabled and the next available key will be used. The
`call_api` function communicates with an AI service (OpenAI by default)
to analyse text prompts and return the generated response.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import requests  # type: ignore


class ApiManager:
    """Simple manager for rotating through multiple API keys.

    This class maintains a list of API keys and an index pointing to the
    currently selected key. When an API key is exhausted or otherwise
    disabled, the `disable_current_key` method marks it inactive and
    advances the index. The `get_active_key` method returns the next
    active key or ``None`` if no keys remain.
    """

    def __init__(self, api_keys: List[str]) -> None:
        # Initialize all keys as active. Keys can be any non‑empty strings.
        self.keys = [{"key": k.strip(), "active": True} for k in api_keys if k.strip()]
        self.current_index = 0
        logging.debug("ApiManager initialised with %d keys", len(self.keys))

    def get_active_key(self) -> Optional[str]:
        """Return the next active API key or ``None`` if none are available."""
        if not self.keys:
            logging.debug("No API keys have been configured.")
            return None
        for i in range(len(self.keys)):
            idx = (self.current_index + i) % len(self.keys)
            if self.keys[idx]["active"]:
                self.current_index = idx
                logging.debug("Using API key at index %d", idx)
                return self.keys[idx]["key"]
        # No active keys remain
        logging.warning("All API keys are inactive. Unable to continue sending requests.")
        return None

    def disable_current_key(self) -> None:
        """Mark the current key as inactive. This can be called when a key runs out of quota."""
        if self.keys:
            self.keys[self.current_index]["active"] = False
            logging.info("API key at index %d has been disabled due to quota exhaustion.", self.current_index)


def call_api(prompt: str, api_key: str) -> str:
    """Send a prompt to the AI analysis API and return its response.

    The implementation targets the OpenAI Chat Completions endpoint but
    can be adapted to other providers with similar semantics.

    Parameters
    ----------
    prompt: str
        The constructed prompt to send to the AI service.
    api_key: str
        The API key to use for authentication.

    Returns
    -------
    str
        The AI's response as plain text. If the service reports that the
        request exceeded the token limit, the string ``"TOKEN_LIMIT"`` is
        returned so the caller can react accordingly.
    """

    logging.debug("call_api invoked with key %s", api_key)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code in {400, 413} and "maximum context length" in response.text.lower():
            logging.warning("Token limit exceeded for request")
            return "TOKEN_LIMIT"
        if response.status_code == 401:
            raise PermissionError("Invalid API key")
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as exc:
        logging.error("API request failed: %s", exc)
        raise
    except (KeyError, IndexError) as exc:
        logging.error("Unexpected API response format: %s", exc)
        raise RuntimeError("Malformed API response") from exc
