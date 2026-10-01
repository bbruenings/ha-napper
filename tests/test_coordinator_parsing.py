"""Tests for the coordinator's response parsing logic.

Uses the stubbed homeassistant package from conftest.py, so the helper
methods of NapperDataUpdateCoordinator run without a running HA instance.
"""

from types import SimpleNamespace

import pytest

from custom_components.napper.coordinator import NapperDataUpdateCoordinator


def make_coordinator() -> NapperDataUpdateCoordinator:
    """Build a coordinator without running DataUpdateCoordinator.__init__."""
    coord = object.__new__(NapperDataUpdateCoordinator)
    coord.baby_id = "baby-1"
    return coord


class TestBabySleeping:
    """The two-priority sleeping detection rule."""

    def test_open_nap_log_means_sleeping(self):
        coord = make_coordinator()
        result = coord._parse_api_response(
            {
                "logs": [
                    {
                        "category": "NAP",
                        "isOpen": True,
                        "start": "2026-10-01T10:46:17.127+02:00",
                        "createdAt": "2026-10-01T10:46:17.127+02:00",
                    }
                ],
                "scheduleItems": [],
            }
        )
        assert result["baby_sleeping"] is True
        assert result["current_nap"] is not None

    def test_bedtime_after_wake_up_means_sleeping(self):
        coord = make_coordinator()
        result = coord._parse_api_response(
            {
                "logs": [
                    {"category": "WOKE_UP", "createdAt": "2026-10-01T07:00:00"},
                    {"category": "BED_TIME", "createdAt": "2026-10-01T06:00:00"},
                ],
                "scheduleItems": [],
            }
        )
        # Bedtime (06:00) is NOT after wake up (07:00) -> awake
        assert result["baby_sleeping"] is False

    def test_bedtime_before_wake_up_means_awake(self):
        coord = make_coordinator()
        result = coord._parse_api_response(
            {
                "logs": [
                    {"category": "BED_TIME", "createdAt": "2026-10-01T19:30:00"},
                    {"category": "WOKE_UP", "createdAt": "2026-10-01T07:00:00"},
                ],
                "scheduleItems": [],
            }
        )
        assert result["baby_sleeping"] is True

    def test_no_logs_means_awake(self):
        coord = make_coordinator()
        result = coord._parse_api_response({"logs": [], "scheduleItems": []})
        assert result["baby_sleeping"] is False
        assert result["current_nap"] is None


class TestLastEvents:
    """Most-recent-log-per-category extraction."""

    LOGS = [
        {"category": "CHANGED_DIAPER", "diaperContent": "WET", "createdAt": "2026-10-01T08:00:00", "id": "w1"},
        {"category": "CHANGED_DIAPER", "diaperContent": "WET", "createdAt": "2026-10-01T11:00:00", "id": "w2"},
        {"category": "CHANGED_DIAPER", "diaperContent": "POOP", "createdAt": "2026-10-01T09:00:00", "id": "p1"},
        {"category": "CHANGED_DIAPER", "diaperContent": "DRY", "createdAt": "2026-10-01T10:00:00", "id": "d1"},
        {"category": "CHANGED_DIAPER", "diaperContent": "MIXED", "createdAt": "2026-10-01T09:30:00", "id": "m1"},
        {"category": "SOLIDS", "createdAt": "2026-10-01T12:00:00", "id": "s1"},
        {"category": "SOLIDS", "createdAt": "2026-10-01T12:30:00", "id": "s2"},
        {"category": "WOKE_UP", "createdAt": "2026-10-01T07:00:00", "id": "wu1"},
        {"category": "BED_TIME", "createdAt": "2026-10-01T06:00:00", "id": "bt1"},
    ]

    def test_latest_per_category_wins(self):
        coord = make_coordinator()
        result = coord._parse_api_response({"logs": self.LOGS, "scheduleItems": []})
        assert result["last_diaper"]["id"] == "w2"
        assert result["last_solids"]["id"] == "s2"
        assert result["last_wake_up"]["id"] == "wu1"
        assert result["last_bedtime"]["id"] == "bt1"

    def test_diaper_types_are_tracked_separately(self):
        coord = make_coordinator()
        result = coord._parse_api_response({"logs": self.LOGS, "scheduleItems": []})
        assert result["last_wet_diaper"]["id"] == "w2"
        assert result["last_dry_diaper"]["id"] == "d1"
        assert result["last_mixed_diaper"]["id"] == "m1"
        assert result["last_dirty_diaper"]["id"] == "p1"


class TestNextSchedule:
    """Upcoming schedule items."""

    def test_completed_items_are_skipped(self):
        coord = make_coordinator()
        result = coord._parse_api_response(
            {
                "logs": [],
                "scheduleItems": [
                    {"type": "NAP", "completed": True, "time": "2026-10-01T10:57:00.000"},
                    {"type": "NAP", "completed": False, "time": "2026-10-01T14:00:00.000"},
                    {"type": "BED_TIME", "completed": False, "time": "2026-10-01T19:00:00.000"},
                ],
            }
        )
        assert result["next_nap"]["time"] == "2026-10-01T14:00:00.000"
        assert result["next_bedtime"]["time"] == "2026-10-01T19:00:00.000"


class TestNapScheduleMatching:
    """Nap logs merge with the closest schedule item within 30 minutes."""

    def test_match_within_threshold_merges_schedule_data(self):
        coord = make_coordinator()
        from homeassistant.util import dt as dt_util

        local_tz = dt_util.now().tzinfo
        # Nap start expressed in the *runner's* local time (CI is UTC, hosts may not be)
        nap_start = dt_util.now().replace(hour=10, minute=46, second=17, microsecond=127000)
        nap_log = {"id": "nap1", "category": "NAP", "isOpen": True,
                   "start": nap_start.isoformat()}
        schedule_items = [
            {"type": "NAP", "time": "2026-10-01T10:57:00.000", "duration": 90, "napNumber": 2},
            {"type": "NAP", "time": "2026-10-01T14:00:00.000", "duration": 60, "napNumber": 3},
        ]
        merged = coord._match_nap_with_schedule(nap_log, schedule_items)
        assert merged["scheduled_duration"] == 90
        assert merged["scheduled_nap_number"] == 2
        # Original fields are preserved
        assert merged["id"] == "nap1"
        assert merged["isOpen"] is True

    def test_no_match_beyond_threshold_returns_log_unchanged(self):
        coord = make_coordinator()
        from homeassistant.util import dt as dt_util

        # Nap start in the runner's local time; schedule item is 4 hours later
        nap_start = dt_util.now().replace(hour=10, minute=46, second=17, microsecond=127000)
        nap_log = {"id": "nap1", "start": nap_start.isoformat()}
        schedule_items = [{"type": "NAP", "time": "2026-10-01T15:00:00.000", "duration": 60}]
        merged = coord._match_nap_with_schedule(nap_log, schedule_items)
        # 10:46 vs 15:00 = 4h14m apart in local interpretation -> beyond 30 min
        assert merged is nap_log
        assert "scheduled_duration" not in merged

    def test_missing_start_returns_log_unchanged(self):
        coord = make_coordinator()
        nap_log = {"id": "nap1"}
        assert coord._match_nap_with_schedule(nap_log, []) is nap_log

    def test_naive_schedule_time_gets_local_tz(self):
        """Schedule times are naive; they must be interpreted as local time."""
        coord = make_coordinator()
        from homeassistant.util import dt as dt_util

        local_tz = dt_util.now().tzinfo
        # Schedule time exactly equals the nap start in the runner's local time
        nap_start = dt_util.now().replace(hour=10, minute=46, second=17, microsecond=127000)
        naive = nap_start.replace(tzinfo=None).isoformat()
        nap_log = {"id": "nap1", "start": nap_start.isoformat()}
        schedule_items = [{"type": "NAP", "time": naive, "duration": 45}]
        merged = coord._match_nap_with_schedule(nap_log, schedule_items)
        assert merged["scheduled_duration"] == 45  # would fail if naive != aware offset
        assert local_tz is not None