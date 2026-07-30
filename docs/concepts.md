# Modello fisico e sorgenti dati

## Indice principale: UTCI

UTCI (Universal Thermal Climate Index) usa:

- temperatura aria (`temperature_2m`)
- umidità relativa (`relative_humidity_2m`)
- velocità vento (`wind_speed_10m`)
- temperatura radiante media (MRT)

Output:

- `utci` (°C equivalente)
- `utci_category` (categoria di stress termico)

## Indici secondari

- `heat_index` (Rothfusz/NOAA, caldo-umido)
- `wind_chill` (freddo-ventoso)
- `wbgt_outdoor` (stima semplificata)

## Parametri fisiologici/scenario

Classe `ComfortParams`:

- `activity`: preset oppure valore MET
  - preset validi: `resting`, `seated`, `standing`, `walking`, `walking_fast`, `hiking`, `cycling`
- `sun_exposure`: frazione 0..1 (0=ombra piena, 1=pieno sole)
- `posture`: `standing` o `sitting`

## MRT

MRT stimata via:

- posizione solare (`pvlib`)
- radiazione diretta/diffusa (Open-Meteo)
- modello `solar_gain` di `pythermalcomfort`

## Sorgenti dati

### Open-Meteo Archive API

- endpoint: `https://archive-api.open-meteo.com/v1/archive`
- usata come base storica/reanalisi

### Open-Meteo Forecast API

- endpoint: `https://api.open-meteo.com/v1/forecast`
- usata per previsioni e forecast-vs-actual (storico modello via `past_days`)

## Variabili orarie ingestite

- `temperature_2m`
- `relative_humidity_2m`
- `wind_speed_10m`
- `shortwave_radiation`
- `direct_normal_irradiance`
- `diffuse_radiation`
- `cloud_cover`
- `precipitation`
- `apparent_temperature`

## Cache

Cache su parquet in `~/.thermalcomfort_cache`, con fetch incrementale (solo finestre mancanti).
