# CLI reference

Entry point:

```bash
python -m thermalcomfort <subcommand> [options]
```

## Location format

- `"Name:lat,lon"` (recommended)
- `"lat,lon"`

## Common options

- `--activity` = `resting|seated|standing|walking|walking_fast|hiking|cycling`
- `--sun` = float in `0..1`
- `--tz` = IANA timezone (for example `Europe/Rome`)
- `--output|-o` = save plot to file
- `--verbose|-v` = verbose logging

---

## `show`

Single-location time-series analysis.

```bash
python -m thermalcomfort show "Florence:43.7696,11.2558" --start 2024-07-01 --end 2024-07-03
```

Options:

- `--start`, `--end`
- common options
- `--no-display` (force non-interactive plotting backend)

---

## `compare`

Multi-location comparison.

```bash
python -m thermalcomfort compare "Florence:43.7696,11.2558" "Livorno:43.5485,10.3106" --variable utci
```

Options:

- `locations` (1+)
- `--start`, `--end`
- `--hour` (0-23 UTC) for a quick tabular snapshot
- `--variable` valid values:
  - `utci`
  - `utci_category`
  - `temperature_2m`
  - `relative_humidity_2m`
  - `wind_speed_10m`
  - `mrt`
  - `heat_index`
  - `wind_chill`
  - `wbgt_outdoor`
  - `apparent_temperature`
  - `precipitation`
  - `cloud_cover`
  - `shortwave_radiation`
  - `direct_normal_irradiance`
  - `diffuse_radiation`

---

## `summary`

UTCI category distribution over a period.

```bash
python -m thermalcomfort summary "Rome:41.9028,12.4964" --start 2024-07-01 --end 2024-07-31
```

Options:

- `location`
- `--start`, `--end`
- common options

---

## `climate`

Multi-year climatological profile.

```bash
python -m thermalcomfort climate "Florence:43.7696,11.2558" --start-year 2010 --end-year 2023
```

Hourly profile for a specific month:

```bash
python -m thermalcomfort climate "Florence:43.7696,11.2558" --start-year 2010 --end-year 2023 --month 7
```

Options:

- `location`
- `--start-year`, `--end-year`
- `--month` (1-12, optional)
- common options

---

## `rank`

Rank locations by climatological comfort.

```bash
python -m thermalcomfort rank "Florence:43.7696,11.2558" "London:51.5074,-0.1278" --month 4
```

Options:

- `locations`
- `--start-year`, `--end-year`
- `--month` optional
- common options

---

## `map`

Map comfort at a given timestamp.

```bash
python -m thermalcomfort map "Florence:43.7696,11.2558" "Rome:41.9028,12.4964" --datetime "2024-07-14 12:00"
```

Options:

- `locations`
- `--datetime` (UTC)
- `--static` (matplotlib map instead of folium HTML)
- `--variable` valid values:
  - `utci`
  - `temperature_2m`
  - `mrt`
  - `heat_index`
  - `wind_chill`
  - `wbgt_outdoor`
  - `apparent_temperature`
- common options

---

## `forecast`

Forecast-vs-actual comparison (historical window, typically up to ~92 days).

```bash
python -m thermalcomfort forecast "Florence:43.7696,11.2558" --start 2026-07-15 --end 2026-07-25 --variable utci
```

Options:

- `location`
- `--start`, `--end`
- `--variable` uses the same valid values as `compare`
- common options
