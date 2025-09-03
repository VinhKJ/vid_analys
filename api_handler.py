"""Utilities for managing API keys and sending analysis requests.

This module defines a simple API manager that can rotate through a list
of provided API keys. If one key exceeds its daily usage limit, it can
be disabled and the next available key will be used. The
``call_api`` function communicates with the Google AI Studio
Generative Language API (Gemini) to analyse text prompts and return the
generated response.
"""

from __future__ import annotations

import logging
from typing import List, Optional

# ``google-genai`` is imported lazily inside ``call_api`` so that the module
# can be imported even if the dependency is missing (e.g. in minimal test
# environments). The real client will be loaded when ``call_api`` is invoked.


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
    """Send a prompt to Gemini and return its textual response.

    Parameters
    ----------
    prompt:
        The constructed prompt to send to the AI service.
    api_key:
        Google AI Studio API key used for authentication.

    Returns
    -------
    str
        The AI's response as plain text. If the service reports that the
        request exceeded the token limit, the string ``"TOKEN_LIMIT"`` is
        returned so the caller can react accordingly.
    """

    logging.debug("call_api invoked with key %s", api_key)

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:  # pragma: no cover - handled at runtime
        raise RuntimeError("google-genai library is required") from exc

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return response.text.strip()
    except Exception as exc:  # pragma: no cover - depends on external API
        message = str(exc).lower()
        if "api key" in message and "invalid" in message:
            raise PermissionError("Invalid API key") from exc
        if "too long" in message or "token" in message:
            logging.warning("Token limit exceeded for request")
            return "TOKEN_LIMIT"
        logging.error("API request failed: %s", exc)
        raise
