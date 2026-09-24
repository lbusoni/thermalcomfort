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

- `sun_exposure`: float in `[0, 1]` (0 = full shade, 1 = full sun)
- `surface_type`: `asphalt` or `grass` — ground surface under the person,
  used for reflected short-wave gain and ground long-wave emission

## MRT estimation

MRT is derived from a full short-wave + long-wave radiative flux balance,
inverted through the Stefan-Boltzmann law (Thorsson et al. 2007 / VDI 3787
style — see `thermalcomfort/comfort/mrt.py`), not from a flat "MRT = Ta"
shade fallback or from `pythermalcomfort`'s `solar_gain()` (an ASHRAE 55
*indoor* model for a person near a sunlit window, whose default indoor floor
reflectance used to inflate outdoor MRT to unrealistic values, e.g. ~85 °C
at summer noon).

Inputs:

- solar geometry (`pvlib`)
- direct, diffuse and global radiation from Open-Meteo
- cloud cover, for clear-sky vs. overcast long-wave balance (Prata 1996 +
  Crawford & Duchon 2001 cloud correction)
- air temperature and humidity, for both the long-wave balance and, in the
  absence of any radiation/cloud data, the sole determinant of MRT (which
  then sits slightly *below* Ta due to net radiative loss to a clear sky —
  not equal to Ta)

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

To delete cached data: `tcs.clear_cache()` (Python API) or
`thermalcomfort cache --clear` (CLI). See [cli.md](cli.md#cache).
