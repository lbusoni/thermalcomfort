# Python API reference

## `ThermalComfortSystem`

Import:

```python
from thermalcomfort import ThermalComfortSystem, Location, ComfortParams
```

### `Location`

Alias di `LocationInfo(lat, lon, name="")`.

Esempio:

```python
firenze = Location(43.7696, 11.2558, "Firenze")
```

### `ComfortParams`

```python
ComfortParams(
    activity="walking",     # oppure MET float
    sun_exposure=0.5,       # 0..1
    posture="standing",     # "standing"|"sitting"
)
```

### `get(...)`

```python
df = tcs.get(
    location=firenze,
    start="2024-07-01",
    end="2024-07-03 23:00",
    params=ComfortParams(activity="walking", sun_exposure=0.5),
    raw=False,
)
```

Parametri:

- `location`: `Location`
- `start`, `end`: `str | pd.Timestamp`
- `params`: `ComfortParams | None`
- `raw`: `bool` (se `True`, niente indici di comfort)

Output (`raw=False`): DataFrame con colonne meteo +:

- `mrt`
- `utci`
- `utci_category`
- `heat_index`
- `wind_chill`
- `wbgt_outdoor`

### `compare(...)`

```python
tcs.compare(
    [firenze, livorno],
    start="2024-07-01",
    end="2024-07-03 23:00",
    variable="utci",
    params=ComfortParams(),
    local_tz="Europe/Rome",
    show=True,
)
```

### `plot(...)`

Dashboard serie temporale singola località.

### `plot_summary(...)`

Distribuzione categorie UTCI.

### `plot_forecast_vs_actual(...)`

Confronta output modello forecast con reanalisi storica.

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

Ritorna DataFrame indicizzato per mese con:

- `utci_mean`, `utci_std`
- `temp_mean`, `temp_std`
- `no_stress_frac`, `heat_stress_frac`, `cold_stress_frac`

Esempio:

```python
stats = ca.monthly_stats(
    location=firenze,
    params=ComfortParams(activity="walking", sun_exposure=0.5),
    daytime_only=True,
)
print(stats)
```

### `hourly_profile(location, month, params=None, progress_callback=None)`

Ritorna DataFrame (ore 0..23) con:

- `utci_mean`, `utci_p25`, `utci_p75`
- `temp_mean`, `rh_mean`, `wind_mean`

Esempio:

```python
profile = ca.hourly_profile(firenze, month=7, params=ComfortParams())
print(profile.head())
```

### `rank_locations(locations, month=None, params=None, daytime_only=True, progress_callback=None)`

Ritorna DataFrame con ranking per comfort:

- `location`
- `utci_mean`, `utci_std`
- `no_stress_frac`
- `heat_stress_frac`, `cold_stress_frac`

Esempio:

```python
ranking = ca.rank_locations(
    [firenze, livorno, roma],
    month=4,
    params=ComfortParams(activity="walking"),
)
print(ranking)
```

### Plot climatologici

- `plot_monthly(location, params=None, show=True, progress_callback=None)`
- `plot_hourly_profile(location, month, params=None, show=True, progress_callback=None)`
- `plot_rank(locations, month=None, params=None, show=True)`

---

## Variabili plottabili consigliate

- `utci`
- `temperature_2m`
- `relative_humidity_2m`
- `wind_speed_10m`
- `mrt`
- `heat_index`
- `wind_chill`
- `wbgt_outdoor`
- `apparent_temperature`
