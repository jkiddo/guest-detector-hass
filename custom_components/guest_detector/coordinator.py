"""DataUpdateCoordinator for Guest Detector sliding window analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from statistics import mean, stdev

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=1)

# Visit grouping constraints
MAX_GAP_DAYS = 2
MAX_STAY_NORMAL = 7
MAX_STAY_SUMMER = 14


def _percentile_25(values: list[float]) -> float:
    """Compute 25th percentile of a list of values."""
    s = sorted(values)
    n = len(s)
    idx = (n - 1) * 0.25
    lo = int(idx)
    hi = lo + 1
    frac = idx - lo
    if hi >= n:
        return s[lo]
    return s[lo] * (1 - frac) + s[hi] * frac


def _is_heating_season(dt: datetime) -> bool:
    """Return True during heating season (October through February)."""
    return dt.month >= 10 or dt.month <= 2


def _max_stay_for_month(month: int) -> int:
    """Jul/Aug allow 14-day stays, otherwise 7."""
    return MAX_STAY_SUMMER if month in (7, 8) else MAX_STAY_NORMAL


def _compute_visits(
    daily_values: list[dict],
    window_size: int,
    threshold: float,
    min_excess: float,
    heating_floor: float,
) -> list[dict]:
    """Run the sliding window over all days and group flagged days into visits."""
    if len(daily_values) <= window_size:
        return []

    # Pass 1: flag each day
    detections: list[dict] = []
    for i in range(window_size, len(daily_values)):
        window = daily_values[max(0, i - window_size) : i]
        window_energies = [d["energy"] for d in window]

        baseline = _percentile_25(window_energies)
        if _is_heating_season(daily_values[i]["date"]):
            baseline = max(baseline, heating_floor)

        current = daily_values[i]["energy"]
        excess = current - baseline
        ratio = current / baseline if baseline > 0 else 0

        if ratio >= threshold and excess >= min_excess:
            detections.append(
                {
                    "date": daily_values[i]["date"],
                    "energy": round(current, 2),
                    "baseline": round(baseline, 2),
                    "ratio": round(ratio, 2),
                    "excess": round(excess, 2),
                }
            )

    if not detections:
        return []

    # Pass 2: group consecutive detections into visits
    visits: list[dict] = []
    current_visit = {
        "start": detections[0]["date"],
        "end": detections[0]["date"],
        "days": [detections[0]],
    }
    for det in detections[1:]:
        prev_end = current_visit["end"]
        gap = (det["date"] - prev_end).days
        visit_len = (det["date"] - current_visit["start"]).days + 1
        max_stay = _max_stay_for_month(current_visit["start"].month)

        if gap <= MAX_GAP_DAYS and visit_len <= max_stay:
            current_visit["end"] = det["date"]
            current_visit["days"].append(det)
        else:
            visits.append(current_visit)
            current_visit = {
                "start": det["date"],
                "end": det["date"],
                "days": [det],
            }
    visits.append(current_visit)

    # Pass 3: summarize each visit
    summarized: list[dict] = []
    for visit in visits:
        total_energy = round(sum(d["energy"] for d in visit["days"]), 2)
        total_excess = round(sum(d["excess"] for d in visit["days"]), 2)
        avg_baseline = round(mean(d["baseline"] for d in visit["days"]), 2)
        avg_ratio = round(mean(d["ratio"] for d in visit["days"]), 1)
        duration = (visit["end"] - visit["start"]).days + 1
        summarized.append(
            {
                "start": visit["start"],
                "end": visit["end"],
                "duration_days": duration,
                "flagged_days": len(visit["days"]),
                "total_energy_kwh": total_energy,
                "excess_energy_kwh": total_excess,
                "avg_baseline_kwh": avg_baseline,
                "avg_ratio": avg_ratio,
                "days": visit["days"],
            }
        )

    return summarized


class EnergyWindowCoordinator(DataUpdateCoordinator):
    """Fetches energy statistics from HA recorder and computes sliding window metrics.

    Tuned sliding window algorithm:
    1. Pulls up to 365 days of daily energy statistics from the recorder.
    2. Uses the 25th percentile of the window as baseline, which is robust
       against visit spikes inflating the average.
    3. Applies a seasonal heating floor (Oct-Feb) to account for frost
       protection energy that runs even when unoccupied.
    4. Flags guest presence when BOTH conditions are met:
       - ratio (current / baseline) >= threshold
       - absolute excess (current - baseline) >= min_excess kWh
    5. Groups flagged days into visits (max 7 days, 14 in Jul/Aug).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        energy_entity: str,
        window_size: int,
        threshold: float,
        min_excess: float,
        heating_floor: float,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.energy_entity = energy_entity
        self.window_size = window_size
        self.threshold = threshold
        self.min_excess = min_excess
        self.heating_floor = heating_floor

    async def _async_update_data(self) -> dict:
        """Fetch energy statistics and compute sliding window metrics."""
        now = dt_util.now()
        start_time = now - timedelta(days=365)

        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            now,
            {self.energy_entity},
            "day",
            None,
            {"sum", "change"},
        )

        entity_stats = stats.get(self.energy_entity, [])

        empty = {
            "daily_values": [],
            "visits": [],
            "baseline": None,
            "current": None,
            "ratio": None,
            "excess": None,
            "std_dev": None,
            "is_guest": False,
            "window_size": self.window_size,
            "threshold": self.threshold,
            "min_excess": self.min_excess,
            "heating_floor": self.heating_floor,
            "heating_season": False,
            "days_available": 0,
            "window_start": None,
            "window_end": None,
        }

        if not entity_stats:
            _LOGGER.warning(
                "No statistics found for %s. "
                "Ensure long-term statistics are enabled for this entity",
                self.energy_entity,
            )
            return empty

        # Extract daily energy values (change = consumption that day)
        daily_values: list[dict] = []
        for entry in entity_stats:
            day_value = entry.get("change")
            if day_value is not None and day_value > 0:
                raw_start = entry["start"]
                if isinstance(raw_start, datetime):
                    start_dt = raw_start
                elif isinstance(raw_start, (int, float)):
                    start_dt = dt_util.utc_from_timestamp(raw_start)
                else:
                    start_dt = dt_util.parse_datetime(raw_start)
                daily_values.append(
                    {"date": start_dt, "energy": round(day_value, 2)}
                )

        if len(daily_values) < self.window_size + 1:
            empty["daily_values"] = daily_values
            empty["days_available"] = len(daily_values)
            if daily_values:
                empty["current"] = daily_values[-1]["energy"]
            return empty

        daily_values.sort(key=lambda x: x["date"])

        # Compute full visit history
        visits = _compute_visits(
            daily_values,
            self.window_size,
            self.threshold,
            self.min_excess,
            self.heating_floor,
        )

        # Current-day metrics (for the real-time sensors)
        current_value = daily_values[-1]["energy"]
        current_date = daily_values[-1]["date"]

        window_entries = daily_values[-(self.window_size + 1) : -1]
        window_energies = [e["energy"] for e in window_entries]

        baseline = round(_percentile_25(window_energies), 2)
        heating_season = _is_heating_season(current_date)
        if heating_season:
            baseline = max(baseline, self.heating_floor)

        std = round(stdev(window_energies), 2) if len(window_energies) >= 2 else 0.0
        excess = round(current_value - baseline, 2)
        ratio = round(current_value / baseline, 2) if baseline > 0 else None

        is_guest = (
            ratio is not None
            and ratio >= self.threshold
            and excess >= self.min_excess
        )

        return {
            "daily_values": daily_values,
            "visits": visits,
            "baseline": baseline,
            "current": current_value,
            "ratio": ratio,
            "excess": excess,
            "std_dev": std,
            "is_guest": is_guest,
            "window_size": self.window_size,
            "threshold": self.threshold,
            "min_excess": self.min_excess,
            "heating_floor": self.heating_floor,
            "heating_season": heating_season,
            "days_available": len(daily_values),
            "window_start": window_entries[0]["date"].isoformat() if window_entries else None,
            "window_end": window_entries[-1]["date"].isoformat() if window_entries else None,
        }
