"""Utilities for managing API keys and sending analysis requests.

This module defines a simple API manager that can rotate through a list
of provided API keys. If one key exceeds its daily usage limit, it can
be disabled and the next available key will be used. The
`call_api` function is a stub meant to be replaced with actual logic to
contact your AI analysis service (e.g. AI Studio). It returns a mock
response for demonstration purposes.
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

    Parameters
    ----------
    prompt: str
        The constructed prompt to send to the AI service.
    api_key: str
        The API key to use for authentication.

    Returns
    -------
    str
        The AI's response as plain text.

    Notes
    -----
    The current implementation is a stub and merely returns a truncated
    version of the prompt for demonstration. Replace this with actual
    requests to your service endpoint. For example:

    .. code-block:: python

        url = "https://api.ai-studio.com/v1/analyse"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt}
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json().get("analysis", "")

    Handle HTTP errors, token limit errors, and other exceptions as
    appropriate for your API provider. If the API indicates the request
    exceeded allowed tokens, raise an exception or return a special
    marker string so that the caller can log the issue.
    """
    logging.debug("call_api invoked with key %s", api_key)
    # TODO: Replace the following with actual API interaction. This is
    # currently a placeholder that returns part of the prompt for
    # demonstration and testing of the GUI.
    return f"[Mô phỏng phân tích với khóa {api_key[:4]}]: {prompt[:200]}..."
