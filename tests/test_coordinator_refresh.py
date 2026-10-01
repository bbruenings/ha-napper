"""Tests for permanent vs. transient token-refresh classification."""

import pytest

from custom_components.napper.coordinator import is_permanent_refresh_error


@pytest.mark.parametrize(
    ("status", "data", "expected"),
    [
        (401, None, True),
        (403, {}, True),
        (400, {"message": "Invalid or expired refresh token provided: token-mismatch"}, True),
        (400, {"message": "Some refresh token problem"}, True),
        (400, {"message": "MISSING_BODY_PROPERTIES: refreshToken"}, False),
        (400, {"message": "Something else entirely"}, False),
        (500, None, False),
        (502, {"message": "refresh token"}, False),
        (200, {"message": "refresh token"}, False),
    ],
)
def test_is_permanent_refresh_error(status, data, expected):
    """400 with a refresh-token message is permanent; other statuses are not."""
    assert is_permanent_refresh_error(status, data) is expected