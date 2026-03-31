# Guest Detector

A Home Assistant (HACS) integration that detects guest visits by analyzing energy consumption patterns. It uses a sliding window algorithm over long-term energy statistics to identify periods where usage significantly exceeds the baseline — indicating the property is occupied.

Built for vacation homes, holiday rentals, or any property where occupancy correlates with energy spikes.

## How it works

The algorithm runs hourly and analyzes up to 365 days of daily energy data from the Home Assistant recorder:

1. **Baseline calculation** — Uses the **25th percentile** of a configurable sliding window (default 30 days). The 25th percentile is robust against visit spikes inflating the baseline, unlike a simple average.

2. **Seasonal heating floor** — During the heating season (October through February), a minimum baseline floor is enforced (default 3.0 kWh) to account for frost protection energy that keeps pipes from freezing even when unoccupied.

3. **Dual-threshold detection** — A day is flagged as occupied when **both** conditions are met:
   - Energy exceeds the baseline by a configurable multiplier (default 1.5x)
   - Absolute excess exceeds a minimum (default 2.0 kWh), preventing false positives when the baseline is very low

4. **Visit grouping** — Consecutive flagged days are grouped into visits with a maximum duration cap of 7 days (14 days in July/August) to match typical stay patterns. Gaps of up to 2 days within a visit are tolerated.

## Entities

The integration creates the following entities:

| Entity | Type | Description |
|---|---|---|
| Guest Detected | `binary_sensor` | ON when today's energy suggests guest presence |
| Guest Visits | `calendar` | Calendar of all detected visits over the past year |
| Energy Baseline | `sensor` | Current sliding window baseline (kWh) |
| Energy Current Day | `sensor` | Most recent day's energy consumption (kWh) |
| Energy Ratio | `sensor` | Ratio of current energy to baseline |
| Energy Std Dev | `sensor` | Standard deviation within the sliding window (kWh) |

### Calendar events

Each detected visit appears as an all-day calendar event with:
- **Summary**: `Guest Visit — 303.5 kWh (7d)`
- **Description**: Total energy, excess above baseline, average ratio, and a per-day breakdown

The calendar renders natively in HA's calendar card in month, week, or day view.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add `https://github.com/jkiddo/guest-detector` with category **Integration**
4. Search for "Guest Detector" and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/guest_detector` folder into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

Add the integration via **Settings → Devices & Services → Add Integration → Guest Detector**.

| Parameter | Default | Description |
|---|---|---|
| Energy sensor entity | `sensor.eloverblik_energy_statistic` | Any sensor with long-term statistics (cumulative energy) |
| Sliding window size | 30 days | Number of days used to compute the baseline |
| Detection threshold | 1.5x | Energy must exceed baseline by this factor |
| Minimum excess | 2.0 kWh | Minimum absolute kWh above baseline to trigger |
| Heating season floor | 3.0 kWh | Minimum baseline during Oct–Feb |

The energy sensor can be any HA sensor that records long-term statistics with a cumulative sum — Eloverblik, Shelly, P1, Tibber, etc.

## Requirements

- Home Assistant 2023.1 or newer
- An energy sensor with long-term statistics enabled in the recorder
- Sufficient history (at least `window_size + 1` days of data)
