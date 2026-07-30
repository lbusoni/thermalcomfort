# Data sampling, interpolation, and provenance

This project uses **hourly, UTC-indexed time series** throughout the pipeline.

## Temporal sampling

### What comes from the provider

- `OpenMeteoProvider` returns hourly weather variables for each requested time range.
- The archive endpoint is used for historical/reanalysis data.
- The forecast endpoint is used for recent/future forecast data and for forecast-vs-actual comparisons.

### What the application does

- We do **not** perform custom temporal interpolation when fetching weather data.
- The returned data are kept at hourly resolution.
- Climatology methods aggregate hourly samples into monthly or hour-of-day statistics.
- The interactive notebook and map views may select the **nearest available hour** when a user provides an arbitrary timestamp.

## Spatial sampling

### What comes from the provider

- Data are requested pointwise at a latitude/longitude pair.
- Open-Meteo internally selects the highest-resolution applicable weather model for the location.
- The returned values are therefore model/reanalysis values for that point, not a local station trace.

### What the application does

- We do **not** perform custom spatial interpolation across our own grid.
- Each location is fetched independently.
- Comparison plots and maps combine independent point queries.

## Which data source is used when

### Historical climate and past events

- Historical runs use the **Open-Meteo archive / reanalysis** endpoint.
- In the current pipeline this is the historical source used as the reference (“actual”) field for forecast verification.

### Forecast and near-real-time

- Recent and future periods use the **Open-Meteo forecast** endpoint.
- This is also the source used for `forecast-vs-actual` when the past forecast model output is needed.

### Measurements vs model data

- The current version does **not** ingest local weather-station measurements directly.
- All comfort calculations are based on gridded model/reanalysis data returned by Open-Meteo.
- If station observations are added later, they should be exposed through a dedicated provider so they can be distinguished from model data.

## Practical implications

- Hourly precision is the native temporal scale of the application.
- Spatial comparisons are pointwise, not interpolated surfaces.
- Any difference between “actual” and “forecast” in this project should be interpreted as:
  - forecast model output
  - versus reanalysis/archive data
