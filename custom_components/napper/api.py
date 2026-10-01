"""Shared API utilities for Napper integration.

The Napper API returns Content-Type: text/plain for ALL endpoints,
even when the response body is JSON. This module provides consistent
JSON parsing that handles this quirk.
"""

import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


async def parse_json_response(response: aiohttp.ClientResponse) -> dict[str, Any] | None:
    """Parse API response as JSON, handling text/plain content-type.
    
    The Napper API returns Content-Type: text/plain for all endpoints,
    even when the response body contains JSON. This function reads the
    response as text first, then parses it as JSON.
    
    Args:
        response: The aiohttp ClientResponse to parse
        
    Returns:
        Parsed JSON as dict, or None if response is empty
        Returns the dict even if it's empty (e.g., {})
        
    Raises:
        aiohttp.ClientError: If response cannot be parsed as JSON
    """
    response_text = await response.text()
    
    # Empty response (e.g., from send-otp endpoint)
    if not response_text or response_text.strip() == "":
        return None
    
    try:
        data = json.loads(response_text)
        # Ensure we return a dict (Napper API always returns objects, not arrays)
        if isinstance(data, dict):
            return data
        else:
            _LOGGER.debug("Response is not a JSON object: %s", type(data).__name__)
            return None
    except (json.JSONDecodeError, ValueError) as err:
        _LOGGER.error(
            "Could not parse API response as JSON (%d bytes): %s",
            len(response_text),
            err,
        )
        raise aiohttp.ClientError(f"Invalid JSON response: {err}")


async def make_api_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    json_data: dict[str, Any] | None = None,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """Make an API request and parse the JSON response.
    
    This is a unified helper for making HTTP requests to the Napper API
    with consistent error handling and JSON parsing.
    
    Args:
        session: The aiohttp ClientSession to use
        method: HTTP method (GET, POST, PUT, DELETE)
        url: The full URL to request
        headers: Optional headers dict
        json_data: Optional JSON body for POST/PUT requests
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response as dict, or None for empty responses
        
    Raises:
        aiohttp.ClientError: If request fails or response is invalid JSON
        asyncio.TimeoutError: If request times out
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    
    _LOGGER.debug("Making %s request to %s", method, url)
    
    if method == "GET":
        async with session.get(url, headers=headers, timeout=client_timeout) as response:
            response.raise_for_status()
            return await parse_json_response(response)
    elif method == "POST":
        async with session.post(url, headers=headers, json=json_data, timeout=client_timeout) as response:
            response.raise_for_status()
            return await parse_json_response(response)
    elif method == "PUT":
        async with session.put(url, headers=headers, json=json_data, timeout=client_timeout) as response:
            response.raise_for_status()
            return await parse_json_response(response)
    elif method == "DELETE":
        async with session.delete(url, headers=headers, timeout=client_timeout) as response:
            response.raise_for_status()
            return await parse_json_response(response)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
