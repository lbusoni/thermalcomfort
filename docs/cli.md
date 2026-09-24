# CLI reference

After `pip install`, the `thermalcomfort` command is available directly:

```bash
thermalcomfort <subcommand> [options]
```

Alternatively, the package can be invoked as a module:

```bash
python -m thermalcomfort <subcommand> [options]
```

## Location format

- `"Name:lat,lon"` (recommended)
- `"lat,lon"`
- `"NameInDict"` (for example `Firenze`, `Roma`, `Tokyo`)

Known locations can be listed with:

```bash
thermalcomfort locations
```

## Common options

- `--sun` = float in `0..1` (0 = full shade, 1 = full sun)
- `--surface-type` = `asphalt|grass`
- `--tz` = IANA timezone (for example `Europe/Rome`)
- `--output|-o` = save plot to file
- `--verbose|-v` = verbose logging

---

## `show`

Single-location time-series analysis.

```bash
thermalcomfort show "Florence:43.7696,11.2558" --start 2024-07-01 --end 2024-07-03
```

Options:

- `--start`, `--end`
- common options
- `--no-display` (force non-interactive plotting backend)

---

## `compare`

Multi-location comparison.

```bash
thermalcomfort compare "Florence:43.7696,11.2558" "Livorno:43.5485,10.3106" --variable utci
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
thermalcomfort summary "Rome:41.9028,12.4964" --start 2024-07-01 --end 2024-07-31
```

Options:

- `location`
- `--start`, `--end`
- common options

---

## `climate`

Multi-year climatological profile.

```bash
thermalcomfort climate "Florence:43.7696,11.2558" --start-year 2010 --end-year 2023
```

Hourly profile for a specific month:

```bash
thermalcomfort climate "Florence:43.7696,11.2558" --start-year 2010 --end-year 2023 --month 7
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
thermalcomfort rank "Florence:43.7696,11.2558" "London:51.5074,-0.1278" --month 4
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
thermalcomfort map "Florence:43.7696,11.2558" "Rome:41.9028,12.4964" --datetime "2024-07-14 12:00"
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
thermalcomfort forecast "Florence:43.7696,11.2558" --start 2026-07-15 --end 2026-07-25 --variable utci
```

Options:

- `location`
- `--start`, `--end`
- `--variable` uses the same valid values as `compare`
- common options

---

## `calc`

Calculate all comfort indices from directly supplied meteorological values —
no internet access or database required.

```bash
thermalcomfort calc --temp 25 --rh 60 --wind 2
```

With explicit Mean Radiant Temperature:

```bash
thermalcomfort calc --temp 25 --rh 60 --wind 2 --mrt 45
```

With solar irradiance (MRT estimated automatically via the radiative flux
balance, see [concepts.md](concepts.md#mrt-estimation)):

```bash
thermalcomfort calc --temp 25 --rh 60 --wind 2 --ghi 850 --dni 800 --dhi 100 --solar-elevation 60
```

Options:

| Option | Short | Required | Description |
|---|---|---|---|
| `--temp` | `-T` | yes | Air temperature (°C) |
| `--rh` | `-H` | yes | Relative humidity (%) |
| `--wind` | `-W` | yes | Wind speed at 10 m height (m/s) |
| `--mrt` | | no | Mean Radiant Temperature (°C), provided directly. Overrides the radiative estimate below |
| `--ghi` | | no | Global horizontal irradiance, W/m² (default: 0) |
| `--dni` | | no | Direct normal irradiance, W/m² (default: 0) |
| `--dhi` | | no | Diffuse horizontal irradiance, W/m² (default: 0) |
| `--solar-elevation` | | no | Solar elevation angle in degrees, used with `--dni`/`--ghi` (default: 45) |
| `--cloud` | | no | Cloud cover, percent (default: 0, clear sky) |
| `--surface-type` | | no | Ground surface: `asphalt` or `grass` (default: `asphalt`) |
| `--sun` | | no | Sun exposure fraction 0–1 (default: 0.5) |

MRT is determined in this priority order:

1. `--mrt` if provided
2. Otherwise, the radiative flux balance from `--ghi`/`--dni`/`--dhi`/`--solar-elevation`/`--cloud`/`--surface-type` (all optional — omitting the radiation flags gives a clear-sky, no-solar-gain estimate, not a flat MRT = Ta)

Indices reported: UTCI (+ stress category), Heat Index (NOAA Rothfusz, valid only for T ≥ 27 °C and RH ≥ 40 %), Wind Chill (NWS, valid only for T ≤ 10 °C and wind ≥ 1.3 m/s), WBGT outdoor, wet-bulb temperature (Stull 2011).

---

## `cache`

Inspect or clear the local weather-data cache (`~/.thermalcomfort_cache`).

List cached files:

```bash
thermalcomfort cache
```

Clear everything (asks for confirmation):

```bash
thermalcomfort cache --clear
```

Clear specific locations only:

```bash
thermalcomfort cache --clear "Florence:43.7696,11.2558" Roma
```

Options:

- `locations` (optional; with `--clear`, restricts it to these locations)
- `--clear` — delete instead of listing
- `--yes`, `-y` — skip the confirmation prompt
