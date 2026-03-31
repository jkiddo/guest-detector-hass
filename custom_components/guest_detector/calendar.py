"""Calendar entity for Guest Detector - shows detected visits as events."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyWindowCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Guest Detector calendar from a config entry."""
    coordinator: EnergyWindowCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GuestDetectorCalendar(coordinator, entry)])


class GuestDetectorCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar showing detected guest visits based on energy anomalies."""

    _attr_has_entity_name = True
    _attr_name = "Guest Visits"

    def __init__(
        self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        visits = self.coordinator.data.get("visits", [])
        if not visits:
            return None

        # If currently in a visit, return it; otherwise return the most recent
        now = datetime.now(tz=visits[-1]["start"].tzinfo)
        today = now.date()

        for visit in reversed(visits):
            if visit["start"].date() <= today <= visit["end"].date():
                return self._visit_to_event(visit)

        # No active visit — return the most recent past visit
        return self._visit_to_event(visits[-1])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within the given time range."""
        visits = self.coordinator.data.get("visits", [])
        events = []

        for visit in visits:
            visit_start = visit["start"].date()
            # end is exclusive in HA calendar, so add 1 day
            visit_end = visit["end"].date() + timedelta(days=1)

            if visit_end >= start_date.date() and visit_start <= end_date.date():
                events.append(self._visit_to_event(visit))

        return events

    def _visit_to_event(self, visit: dict) -> CalendarEvent:
        """Convert a visit dict to a CalendarEvent."""
        duration = visit["duration_days"]
        total = visit["total_energy_kwh"]
        excess = visit["excess_energy_kwh"]
        avg_ratio = visit["avg_ratio"]

        summary = f"Guest Visit — {total:.1f} kWh ({duration}d)"

        lines = [
            f"Total energy: {total:.1f} kWh",
            f"Excess above baseline: {excess:.1f} kWh",
            f"Avg baseline: {visit['avg_baseline_kwh']:.1f} kWh/day",
            f"Avg ratio: {avg_ratio:.1f}x",
            f"Flagged days: {visit['flagged_days']}",
            "",
            "Daily breakdown:",
        ]
        for day in visit["days"]:
            date_str = day["date"].strftime("%a %b %d")
            lines.append(
                f"  {date_str}: {day['energy']:.1f} kWh "
                f"(+{day['excess']:.1f} over {day['baseline']:.1f} baseline, "
                f"{day['ratio']:.1f}x)"
            )

        return CalendarEvent(
            summary=summary,
            description="\n".join(lines),
            start=visit["start"].date(),
            # HA calendar end date is exclusive for all-day events
            end=visit["end"].date() + timedelta(days=1),
        )
