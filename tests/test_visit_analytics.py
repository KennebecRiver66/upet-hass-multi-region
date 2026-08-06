from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ubpet"
    / "visit_analytics.py"
)
SPEC = importlib.util.spec_from_file_location("ubpet_visit_analytics", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VISIT_ANALYTICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VISIT_ANALYTICS)

VisitAnalyticsTracker = VISIT_ANALYTICS.VisitAnalyticsTracker


class VisitAnalyticsTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 4, 22, 45, tzinfo=UTC)
        self.cat = {"catInfoId": 42, "nickname": "Cat A", "number": 1}

    def record(
        self,
        record_id: int,
        duration: int,
        at: datetime,
        *,
        cat_id: int = 42,
    ) -> dict:
        return {
            "recordId": record_id,
            "catInfoId": cat_id,
            "eventTime": int(at.timestamp() * 1000),
            "eventType": 3,
            "costTime": duration,
        }

    def test_history_backfill_matches_official_app_example(self) -> None:
        tracker = VisitAnalyticsTracker()
        records = [
            self.record(1, 62, datetime(2026, 8, 4, 20, 30, tzinfo=UTC)),
            self.record(2, 177, datetime(2026, 8, 4, 7, 41, tzinfo=UTC)),
            self.record(3, 77, datetime(2026, 8, 4, 7, 17, tzinfo=UTC)),
            self.record(4, 76, datetime(2026, 8, 4, 7, 6, tzinfo=UTC)),
        ]

        changed = tracker.process([self.cat], records=records, now=self.now)

        analytics = self.cat["visit_analytics"]
        self.assertTrue(changed)
        self.assertEqual(analytics["pee_visits_24h"], 3)
        self.assertEqual(analytics["poo_visits_24h"], 1)
        self.assertEqual(
            analytics["last_pee"],
            datetime(2026, 8, 4, 20, 30, tzinfo=UTC),
        )
        self.assertEqual(
            analytics["last_poo"],
            datetime(2026, 8, 4, 7, 41, tzinfo=UTC),
        )

    def test_latest_visit_duration_ignores_vendor_daily_average(self) -> None:
        tracker = VisitAnalyticsTracker()
        self.cat.update({"number": 3, "costTime": 93.3})
        records = [
            self.record(3, 56, self.now - timedelta(hours=7)),
            self.record(1, 135, self.now - timedelta(minutes=12)),
            self.record(2, 89, self.now - timedelta(minutes=43)),
        ]

        tracker.process([self.cat], records=records, now=self.now)

        analytics = self.cat["visit_analytics"]
        self.assertEqual(analytics["last_visit_duration_seconds"], 135)
        self.assertEqual(analytics["poo_visits_24h"], 1)
        self.assertEqual(analytics["pee_visits_24h"], 2)
        self.assertEqual(self.cat["costTime"], 93.3)

    def test_repeated_record_id_is_not_counted_twice(self) -> None:
        tracker = VisitAnalyticsTracker()
        record = self.record(1, 80, self.now - timedelta(minutes=5))
        tracker.process([self.cat], records=[record], now=self.now)

        changed = tracker.process([self.cat], records=[record], now=self.now)

        self.assertFalse(changed)
        self.assertEqual(self.cat["visit_analytics"]["pee_visits_24h"], 1)

    def test_visits_counter_reset_does_not_create_an_event(self) -> None:
        tracker = VisitAnalyticsTracker()
        tracker.process(
            [self.cat],
            records=[self.record(1, 80, self.now - timedelta(minutes=5))],
            now=self.now,
        )
        reset_cat = {**self.cat, "number": 0, "costTime": 80}

        changed = tracker.process(
            [reset_cat],
            records=[],
            now=self.now + timedelta(minutes=5),
        )

        self.assertFalse(changed)
        self.assertEqual(reset_cat["visit_analytics"]["pee_visits_24h"], 1)

    def test_duration_equal_to_threshold_is_poo(self) -> None:
        tracker = VisitAnalyticsTracker()

        tracker.process(
            [self.cat],
            records=[self.record(1, 100, self.now)],
            now=self.now,
        )

        self.assertEqual(self.cat["visit_analytics"]["poo_visits_24h"], 1)

    def test_changing_threshold_reclassifies_stored_visits(self) -> None:
        tracker = VisitAnalyticsTracker()
        tracker.process(
            [self.cat],
            records=[
                self.record(1, 90, self.now - timedelta(minutes=6)),
                self.record(2, 110, self.now - timedelta(minutes=3)),
            ],
            now=self.now,
        )

        changed = tracker.set_threshold("42", 120)
        tracker.attach_analytics([self.cat], now=self.now)

        self.assertTrue(changed)
        self.assertEqual(self.cat["visit_analytics"]["pee_visits_24h"], 2)
        self.assertEqual(self.cat["visit_analytics"]["poo_visits_24h"], 0)
        self.assertIsNone(self.cat["visit_analytics"]["last_poo"])

    def test_rolling_count_expires_but_last_timestamp_remains(self) -> None:
        tracker = VisitAnalyticsTracker()
        event_time = self.now - timedelta(minutes=3)
        tracker.process(
            [self.cat],
            records=[self.record(1, 100, event_time)],
            now=self.now,
        )

        tracker.attach_analytics(
            [self.cat],
            now=event_time + timedelta(hours=24, seconds=1),
        )

        self.assertEqual(self.cat["visit_analytics"]["poo_visits_24h"], 0)
        self.assertEqual(self.cat["visit_analytics"]["last_poo"], event_time)

    def test_each_cat_has_independent_events_and_threshold(self) -> None:
        tracker = VisitAnalyticsTracker()
        other_cat = {"catInfoId": 84, "nickname": "Cat B", "number": 0}
        tracker.set_threshold("42", 80)
        tracker.set_threshold("84", 120)

        tracker.process(
            [self.cat, other_cat],
            records=[
                self.record(1, 100, self.now, cat_id=42),
                self.record(2, 100, self.now, cat_id=84),
            ],
            now=self.now,
        )

        self.assertEqual(self.cat["visit_analytics"]["poo_visits_24h"], 1)
        self.assertEqual(other_cat["visit_analytics"]["pee_visits_24h"], 1)

    def test_storage_round_trip_preserves_events_without_duplicates(self) -> None:
        tracker = VisitAnalyticsTracker()
        record = self.record(1, 120, self.now - timedelta(minutes=3))
        tracker.process([self.cat], records=[record], now=self.now)
        tracker.set_threshold("42", 130)

        restored = VisitAnalyticsTracker(tracker.to_storage())
        unchanged = {**self.cat}
        changed = restored.process([unchanged], records=[record], now=self.now)

        self.assertFalse(changed)
        self.assertEqual(restored.threshold("42"), 130)
        self.assertEqual(unchanged["visit_analytics"]["pee_visits_24h"], 1)

    def test_vendor_time_string_fallback_is_interpreted_as_utc_plus_8(self) -> None:
        tracker = VisitAnalyticsTracker()
        record = {
            "recordId": 1,
            "catInfoId": 42,
            "eventType": 3,
            "costTime": 62,
            "timeStr": "2026-08-05 04:30:24",
        }

        tracker.process([self.cat], records=[record], now=self.now)

        self.assertEqual(
            self.cat["visit_analytics"]["last_pee"],
            datetime(2026, 8, 4, 20, 30, 24, tzinfo=UTC),
        )

    def test_non_visit_and_zero_duration_records_are_ignored(self) -> None:
        tracker = VisitAnalyticsTracker()
        non_visit = self.record(1, 80, self.now)
        non_visit["eventType"] = 31
        zero_duration = self.record(2, 0, self.now)

        changed = tracker.process(
            [self.cat],
            records=[non_visit, zero_duration],
            now=self.now,
        )

        self.assertFalse(changed)
        self.assertEqual(self.cat["visit_analytics"]["pee_visits_24h"], 0)
        self.assertEqual(self.cat["visit_analytics"]["poo_visits_24h"], 0)
        self.assertIsNone(
            self.cat["visit_analytics"]["last_visit_duration_seconds"]
        )

    def test_threshold_rejects_non_finite_and_out_of_range_values(self) -> None:
        tracker = VisitAnalyticsTracker()

        for value in (float("nan"), float("inf"), 9, 151):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tracker.set_threshold("42", value)

    def test_threshold_accepts_inclusive_range_boundaries(self) -> None:
        tracker = VisitAnalyticsTracker()

        self.assertTrue(tracker.set_threshold("42", 10))
        self.assertEqual(tracker.threshold("42"), 10)
        self.assertTrue(tracker.set_threshold("42", 150))
        self.assertEqual(tracker.threshold("42"), 150)


if __name__ == "__main__":
    unittest.main()
