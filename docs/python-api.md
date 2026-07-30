# Python API reference

## `ThermalComfortSystem`

Import:

```python
from thermalcomfort import ThermalComfortSystem, Location, ComfortParams
```

### `Location`

Alias for `LocationInfo(lat, lon, name="")`.

Example:

```python
florence = Location(43.7696, 11.2558, "Florence")
```

### `ComfortParams`

```python
ComfortParams(
    activity="walking",     # or custom MET float
    sun_exposure=0.5,       # 0..1
    posture="standing",     # "standing"|"sitting"
)
```

### `get(...)`

```python
df = tcs.get(
    location=florence,
    start="2024-07-01",
    end="2024-07-03 23:00",
    params=ComfortParams(activity="walking", sun_exposure=0.5),
    raw=False,
)
```

Parameters:

- `location`: `Location`
- `start`, `end`: `str | pd.Timestamp`
- `params`: `ComfortParams | None`
- `raw`: `bool` (`True` returns weather variables only)

Output (`raw=False`): DataFrame with weather columns plus:

- `mrt`
- `utci`
- `utci_category`
- `heat_index`
- `wind_chill`
- `wbgt_outdoor`

The returned index is hourly and UTC-aware. No extra temporal interpolation is
performed by the application when fetching weather data.

### `compare(...)`

```python
tcs.compare(
    [florence, livorno],
    start="2024-07-01",
    end="2024-07-03 23:00",
    variable="utci",
    params=ComfortParams(),
    local_tz="Europe/Rome",
    show=True,
)
```

### `plot(...)`

Single-location time-series dashboard.

### `plot_summary(...)`

UTCI category distribution plot.

### `plot_forecast_vs_actual(...)`

Compares forecast model output against historical reanalysis.

---

## `ClimateAnalysis`

Import:

```python
from thermalcomfort.climate import ClimateAnalysis
```

Init:

```python
ca = ClimateAnalysis(start_year=2010, end_year=2023)
```

### `monthly_stats(location, params=None, daytime_only=True, progress_callback=None)`

Returns a month-indexed DataFrame with:

- `utci_mean`, `utci_std`
- `temp_mean`, `temp_std`
- `no_stress_frac`, `heat_stress_frac`, `cold_stress_frac`

Example:

```python
stats = ca.monthly_stats(
    location=florence,
    params=ComfortParams(activity="walking", sun_exposure=0.5),
    daytime_only=True,
)
print(stats)
```

### `hourly_profile(location, month, params=None, progress_callback=None)`

Returns a DataFrame (hours 0..23) with:

- `utci_mean`, `utci_p25`, `utci_p75`
- `temp_mean`, `rh_mean`, `wind_mean`

Example:

```python
profile = ca.hourly_profile(florence, month=7, params=ComfortParams())
print(profile.head())
```

### `rank_locations(locations, month=None, params=None, daytime_only=True, progress_callback=None)`

Returns a ranking DataFrame with:

- `location`
- `utci_mean`, `utci_std`
- `no_stress_frac`
- `heat_stress_frac`, `cold_stress_frac`

Example:

```python
ranking = ca.rank_locations(
    [florence, livorno, rome],
    month=4,
    params=ComfortParams(activity="walking"),
)
print(ranking)
```

Where `livorno` and `rome` are `Location(...)` objects, for example:

```python
livorno = Location(43.5485, 10.3106, "Livorno")
rome = Location(41.9028, 12.4964, "Rome")
```

### Climatology plotting helpers

- `plot_monthly(location, params=None, show=True, progress_callback=None)`
- `plot_hourly_profile(location, month, params=None, show=True, progress_callback=None)`
- `plot_rank(locations, month=None, params=None, show=True)`

---

## Recommended plottable variables

- `utci`
- `temperature_2m`
- `relative_humidity_2m`
- `wind_speed_10m`
- `mrt`
- `heat_index`
- `wind_chill`
- `wbgt_outdoor`
- `apparent_temperature`
