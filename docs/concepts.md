# Physical model and data sources

## Primary index: UTCI

UTCI (Universal Thermal Climate Index) is the main comfort metric.
It combines:

- air temperature (`temperature_2m`)
- relative humidity (`relative_humidity_2m`)
- wind speed (`wind_speed_10m`)
- mean radiant temperature (MRT)

Outputs:

- `utci` (equivalent temperature in °C)
- `utci_category` (thermal stress category)

## Secondary indices

- `heat_index` (Rothfusz/NOAA, hot-humid conditions)
- `wind_chill` (cold-windy conditions)
- `wbgt_outdoor` (simplified outdoor approximation)

## Scenario parameters (`ComfortParams`)

- `activity`: preset or custom MET value  
  Valid presets: `resting`, `seated`, `standing`, `walking`, `walking_fast`, `hiking`, `cycling`
- `sun_exposure`: float in `[0, 1]` (0 = full shade, 1 = full sun)
- `posture`: `standing` or `sitting`

## MRT estimation

MRT is estimated from:

- solar geometry (`pvlib`)
- direct and diffuse radiation from Open-Meteo
- `solar_gain` model from `pythermalcomfort`

## Weather data sources

### Open-Meteo Archive API

- Endpoint: `https://archive-api.open-meteo.com/v1/archive`
- Used for historical/reanalysis data

### Open-Meteo Forecast API

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Used for forecast data and forecast-vs-actual analysis

## Hourly weather variables used

- `temperature_2m`
- `relative_humidity_2m`
- `wind_speed_10m`
- `shortwave_radiation`
- `direct_normal_irradiance`
- `diffuse_radiation`
- `cloud_cover`
- `precipitation`
- `apparent_temperature`

## Caching model

Weather data is cached as Parquet files under:

- `~/.thermalcomfort_cache`

Caching is incremental by time range: only missing hours are downloaded and merged.
