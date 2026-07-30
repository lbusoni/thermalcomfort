# Thermal Comfort Visualization System

Sistema Python per analizzare e visualizzare il **comfort termico percepito outdoor**
nel tempo e nello spazio, con supporto a:

- serie temporali orarie per una località
- confronto tra località diverse
- mappe geografiche
- climatologia multi-anno (medie mensili / profili orari)
- confronto **previsione vs reanalisi**

---

## 1) Modello fisico-climatologico

### 1.1 Indice principale: UTCI

Il sistema usa come indice principale **UTCI (Universal Thermal Climate Index)**,
ampiamente usato in biometeorologia perché combina in un unico valore:

- temperatura aria (`temperature_2m`)
- umidità relativa (`relative_humidity_2m`)
- vento a 10m (`wind_speed_10m`)
- temperatura radiante media (**MRT**)

Output UTCI:

- valore in °C equivalente fisiologico
- categoria di stress termico (cold/heat stress)

### 1.2 Altri indici calcolati

- **Heat Index** (Rothfusz/NOAA), valido in condizioni caldo-umide
- **Wind Chill** per condizioni fredde e ventose
- **WBGT outdoor** (stima semplificata)

### 1.3 Ombra/sole e attività fisica

Il comfort percepito dipende da:

- **esposizione solare** (`sun_exposure`, 0..1)
- **attività metabolica** (`activity`, preset o valore MET)

Questi parametri vengono passati al motore di calcolo tramite `ComfortParams`.

### 1.4 Stima della MRT

La MRT viene stimata da:

- geometria solare (via `pvlib`)
- radiazione diretta/diffusa (Open-Meteo)
- modello `solar_gain` di `pythermalcomfort`

In assenza di radiazione disponibile, viene usata una stima conservativa in ombra
(MRT ≈ temperatura aria).

---

## 2) Sorgenti dati meteo

### 2.1 Open-Meteo Archive API (storico/reanalisi)

Endpoint usato per lo storico:

- `https://archive-api.open-meteo.com/v1/archive`

Nel sistema è trattato come “actual/ground truth” (reanalisi ERA5 disponibile via Open-Meteo).

### 2.2 Open-Meteo Forecast API (previsioni e forecast model passato)

Endpoint usato per previsioni e storico del modello previsionale:

- `https://api.open-meteo.com/v1/forecast`

Usato anche per il confronto forecast-vs-actual (con `past_days`, limite pratico ~92 giorni).

### 2.3 Variabili orarie usate

- `temperature_2m`
- `relative_humidity_2m`
- `wind_speed_10m`
- `shortwave_radiation`
- `direct_normal_irradiance`
- `diffuse_radiation`
- `cloud_cover`
- `precipitation`
- `apparent_temperature`

---

## 3) Architettura software

Package principale: [`thermalcomfort/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort)

- [`providers/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/providers): astrazione sorgenti dati
- [`cache.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/cache.py): cache parquet incrementale
- [`comfort/indices.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/comfort/indices.py): calcolo indici
- [`viz.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/viz.py): grafici serie temporali / confronto
- [`climate.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/climate.py): analisi climatologica
- [`mapview.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/mapview.py): mappe statiche/interattive
- [`__main__.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort/__main__.py): CLI

---

## 4) Installazione

### 4.1 Requisiti

- Python 3.11+ (consigliato 3.12)

### 4.2 Install dipendenze

```bash
pip install -r requirements.txt
```

---

## 5) Uso rapido da Python API

```python
from thermalcomfort import ThermalComfortSystem, Location, ComfortParams

tcs = ThermalComfortSystem()
loc = Location(43.7696, 11.2558, "Firenze")
params = ComfortParams(activity="walking", sun_exposure=0.5)

df = tcs.get(loc, "2024-07-01", "2024-07-07 23:00", params=params)
tcs.plot(df, title="Firenze")
```

---

## 6) CLI: comandi e parametri

Entry point:

```bash
python -m thermalcomfort <subcommand> [args]
```

### 6.1 `show`

Serie temporale singola località.

```bash
python -m thermalcomfort show "Firenze:43.7696,11.2558" \
  --start 2024-07-01 --end 2024-07-03 --tz Europe/Rome
```

### 6.2 `compare`

Confronto multizona.

```bash
python -m thermalcomfort compare \
  "Firenze:43.7696,11.2558" "Livorno:43.5485,10.3106" \
  --start 2024-07-01 --end 2024-07-03 --hour 17
```

### 6.3 `summary`

Distribuzione categorie UTCI.

```bash
python -m thermalcomfort summary "Roma:41.9028,12.4964" \
  --start 2024-07-01 --end 2024-07-31
```

### 6.4 `climate`

Profilo climatologico multi-anno.

```bash
python -m thermalcomfort climate "Firenze:43.7696,11.2558" \
  --start-year 2010 --end-year 2023
```

Profilo orario per mese specifico:

```bash
python -m thermalcomfort climate "Firenze:43.7696,11.2558" \
  --start-year 2010 --end-year 2023 --month 7
```

### 6.5 `rank`

Classifica località per comfort.

```bash
python -m thermalcomfort rank \
  "Firenze:43.7696,11.2558" "Roma:41.9028,12.4964" "Londra:51.5074,-0.1278" \
  --start-year 2010 --end-year 2023 --month 4
```

### 6.6 `map`

Mappa comfort a timestamp specifico.

```bash
python -m thermalcomfort map \
  "Firenze:43.7696,11.2558" "Livorno:43.5485,10.3106" "Roma:41.9028,12.4964" \
  --datetime "2024-07-14 12:00" --variable utci
```

Mappa statica:

```bash
python -m thermalcomfort map ... --static --output map.png
```

### 6.7 `forecast`

Confronto forecast vs actual (ultimi ~92 giorni).

```bash
python -m thermalcomfort forecast "Firenze:43.7696,11.2558" \
  --start 2026-07-15 --end 2026-07-25 --variable utci
```

### 6.8 Parametri comuni CLI

- `--activity`: `resting|seated|standing|walking|walking_fast|hiking|cycling`
- `--sun`: esposizione sole `0..1`
- `--tz`: timezone display (es. `Europe/Rome`)
- `--output`: salva immagine su file invece di mostrare a video
- `--verbose`: log più dettagliato

Formato località:

- `"Nome:lat,lon"` (consigliato)
- `"lat,lon"`

---

## 7) Cache e performance

La cache file-based viene salvata in:

- `~/.thermalcomfort_cache/`

Caratteristiche:

- scarica solo gli intervalli mancanti
- persiste in parquet
- riuso trasparente in chiamate successive

Il comando `climate` può richiedere tempo al primo run (molti anni di dati), ma
ora mostra avanzamento anno-per-anno.

---

## 8) Esempi pronti

Cartella esempi: [`examples/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples)

- [`basic_usage.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/basic_usage.py)
- [`compare_locations.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/compare_locations.py)
- [`interactive.ipynb`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/interactive.ipynb)
