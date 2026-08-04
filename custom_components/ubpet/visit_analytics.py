from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from math import isfinite
from typing import Any

DEFAULT_POO_DURATION_THRESHOLD_SECONDS = 100
MIN_POO_DURATION_THRESHOLD_SECONDS = 10
MAX_POO_DURATION_THRESHOLD_SECONDS = 150
VISIT_COUNT_WINDOW = timedelta(hours=24)
MAX_STORED_VISITS_PER_CAT = 10_000
VENDOR_SERVER_TIMEZONE = timezone(timedelta(hours=8))
LEGACY_EVENT_MATCH_TOLERANCE = timedelta(minutes=10)


class VisitAnalyticsTracker:
    """Track visits and calculate configurable analytics for every cat."""

    def __init__(self, stored: dict[str, Any] | None = None) -> None:
        cats = stored.get("cats") if isinstance(stored, dict) else None
        self._cats: dict[str, dict[str, Any]] = deepcopy(cats) if isinstance(cats, dict) else {}

    def process(
        self,
        cats: list[dict[str, Any]],
        *,
        records: list[dict[str, Any]] | None = None,
        now: datetime,
    ) -> bool:
        """Ingest individual usage records and attach analytics to cat payloads."""
        now = _as_utc(now)
        changed = False
        touched_cat_keys: set[str] = set()

        for record in records or []:
            cat_id = record.get("catInfoId")
            duration = _as_number(record.get("costTime"))
            event_time = _record_time(record)
            event_type = _as_number(record.get("eventType"))
            if (
                cat_id in (None, "")
                or duration is None
                or duration <= 0
                or event_time is None
                or event_time > now + timedelta(minutes=5)
                or (event_type is not None and int(event_type) != 3)
            ):
                continue

            cat_key = str(cat_id)
            state = self._state(cat_key)
            record_token = _record_token(
                record,
                cat_key=cat_key,
                event_time=event_time,
                duration=duration,
            )
            if any(
                event.get("record_id") == record_token
                for event in state["events"]
                if isinstance(event, dict)
            ):
                continue

            legacy_event = _matching_legacy_event(
                state["events"],
                event_time=event_time,
                duration=duration,
            )
            if legacy_event is not None:
                legacy_event.update(
                    {
                        "at": event_time.isoformat(),
                        "duration_seconds": duration,
                        "record_id": record_token,
                    }
                )
            else:
                state["events"].append(
                    {
                        "at": event_time.isoformat(),
                        "duration_seconds": duration,
                        "record_id": record_token,
                    }
                )
            touched_cat_keys.add(cat_key)
            changed = True

        for cat_key in touched_cat_keys:
            state = self._state(cat_key)
            state["events"] = sorted(
                (event for event in state["events"] if _valid_event(event)),
                key=_event_at,
            )[-MAX_STORED_VISITS_PER_CAT:]

        for cat in cats:
            cat_id = cat.get("catInfoId")
            if cat_id is None:
                continue
            cat_key = str(cat_id)
            cat["visit_analytics"] = self.analytics(cat_key, now=now)

        return changed

    def threshold(self, cat_id: str) -> int:
        """Return the configured Poo duration threshold for a cat."""
        return _threshold(self._state(str(cat_id)).get("poo_duration_threshold_seconds"))

    def set_threshold(self, cat_id: str, seconds: float) -> bool:
        """Set a cat's Poo duration threshold and report whether it changed."""
        parsed_seconds = _as_number(seconds)
        if parsed_seconds is None:
            raise ValueError("Poo duration threshold must be a finite number")
        threshold = int(round(parsed_seconds))
        if not MIN_POO_DURATION_THRESHOLD_SECONDS <= threshold <= MAX_POO_DURATION_THRESHOLD_SECONDS:
            raise ValueError(
                "Poo duration threshold must be between "
                f"{MIN_POO_DURATION_THRESHOLD_SECONDS} and "
                f"{MAX_POO_DURATION_THRESHOLD_SECONDS} seconds"
            )
        state = self._state(str(cat_id))
        if self.threshold(str(cat_id)) == threshold:
            return False
        state["poo_duration_threshold_seconds"] = threshold
        return True

    def attach_analytics(self, cats: list[dict[str, Any]], *, now: datetime) -> None:
        """Refresh derived values without recording a new visit."""
        now = _as_utc(now)
        for cat in cats:
            cat_id = cat.get("catInfoId")
            if cat_id is not None:
                cat["visit_analytics"] = self.analytics(str(cat_id), now=now)

    def analytics(self, cat_id: str, *, now: datetime) -> dict[str, Any]:
        """Calculate counters and last-event timestamps using the current threshold."""
        now = _as_utc(now)
        state = self._state(str(cat_id))
        threshold = self.threshold(str(cat_id))
        events = [event for event in state.get("events", []) if _valid_event(event)]
        cutoff = now - VISIT_COUNT_WINDOW
        recent_events = [event for event in events if _event_at(event) >= cutoff]
        poo_events = [event for event in events if _duration(event) >= threshold]
        pee_events = [event for event in events if _duration(event) < threshold]

        return {
            "poo_duration_threshold_seconds": threshold,
            "pee_visits_24h": sum(
                _duration(event) < threshold for event in recent_events
            ),
            "poo_visits_24h": sum(
                _duration(event) >= threshold for event in recent_events
            ),
            "last_pee": _latest_event_time(pee_events),
            "last_poo": _latest_event_time(poo_events),
        }

    def to_storage(self) -> dict[str, Any]:
        """Return JSON-serializable tracker state."""
        return {"cats": deepcopy(self._cats)}

    def _state(self, cat_id: str) -> dict[str, Any]:
        state = self._cats.get(cat_id)
        if not isinstance(state, dict):
            state = {}
            self._cats[cat_id] = state
        state["poo_duration_threshold_seconds"] = _threshold(
            state.get("poo_duration_threshold_seconds")
        )
        events = state.get("events")
        if not isinstance(events, list):
            events = []
        state["events"] = events[-MAX_STORED_VISITS_PER_CAT:]
        return state


def _threshold(value: Any) -> int:
    try:
        threshold = int(round(float(value)))
    except (OverflowError, TypeError, ValueError):
        return DEFAULT_POO_DURATION_THRESHOLD_SECONDS
    if not MIN_POO_DURATION_THRESHOLD_SECONDS <= threshold <= MAX_POO_DURATION_THRESHOLD_SECONDS:
        return DEFAULT_POO_DURATION_THRESHOLD_SECONDS
    return threshold


def _as_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _record_time(record: dict[str, Any]) -> datetime | None:
    event_time = record.get("eventTime")
    parsed = _parse_timestamp(event_time)
    if parsed is not None:
        return parsed

    time_str = record.get("timeStr")
    if not isinstance(time_str, str) or not time_str:
        return None
    try:
        parsed_time_str = datetime.fromisoformat(time_str)
    except ValueError:
        return None
    if parsed_time_str.tzinfo is None:
        parsed_time_str = parsed_time_str.replace(tzinfo=VENDOR_SERVER_TIMEZONE)
    return parsed_time_str.astimezone(UTC)


def _parse_timestamp(value: Any) -> datetime | None:
    numeric = _as_number(value)
    if numeric is not None:
        seconds = float(numeric)
        if abs(seconds) >= 100_000_000_000:
            seconds /= 1000
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _record_token(
    record: dict[str, Any],
    *,
    cat_key: str,
    event_time: datetime,
    duration: int | float,
) -> str:
    record_id = record.get("recordId")
    if record_id not in (None, ""):
        return str(record_id)
    return f"derived:{cat_key}:{event_time.isoformat()}:{duration}"


def _matching_legacy_event(
    events: list[Any],
    *,
    event_time: datetime,
    duration: int | float,
) -> dict[str, Any] | None:
    for event in events:
        if (
            not isinstance(event, dict)
            or event.get("record_id") not in (None, "")
            or not _valid_event(event)
            or abs(_duration(event) - float(duration)) > 0.001
        ):
            continue
        if abs(_event_at(event) - event_time) <= LEGACY_EVENT_MATCH_TOLERANCE:
            return event
    return None


def _valid_event(event: Any) -> bool:
    return (
        isinstance(event, dict)
        and _parse_datetime(event.get("at")) is not None
        and (duration := _as_number(event.get("duration_seconds"))) is not None
        and duration >= 0
    )


def _duration(event: dict[str, Any]) -> float:
    return float(_as_number(event.get("duration_seconds")) or 0)


def _event_at(event: dict[str, Any]) -> datetime:
    return _parse_datetime(event.get("at")) or datetime.min.replace(tzinfo=UTC)


def _latest_event_time(events: list[dict[str, Any]]) -> datetime | None:
    if not events:
        return None
    return max(_event_at(event) for event in events)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
