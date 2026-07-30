# CLI reference

Entry point:

```bash
python -m thermalcomfort <subcommand> [opzioni]
```

## Formato località

- `"Nome:lat,lon"` (consigliato)
- `"lat,lon"`

## Parametri comuni

- `--activity` = `resting|seated|standing|walking|walking_fast|hiking|cycling`
- `--sun` = float `0..1`
- `--tz` = timezone IANA (es. `Europe/Rome`)
- `--output|-o` = file output immagine
- `--verbose|-v` = log verbosi

---

## `show`

Serie temporale singola località.

```bash
python -m thermalcomfort show "Firenze:43.7696,11.2558" --start 2024-07-01 --end 2024-07-03
```

Opzioni:

- `--start`, `--end`
- comuni
- `--no-display` (forza backend non interattivo)

---

## `compare`

Confronto multizona.

```bash
python -m thermalcomfort compare "Firenze:43.7696,11.2558" "Livorno:43.5485,10.3106" --variable utci
```

Opzioni:

- `locations` (1+)
- `--start`, `--end`
- `--hour` (0-23 UTC) per tabella rapida
- `--variable` con valori validi:
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

Distribuzione categorie UTCI.

```bash
python -m thermalcomfort summary "Roma:41.9028,12.4964" --start 2024-07-01 --end 2024-07-31
```

Opzioni:

- `location`
- `--start`, `--end`
- comuni

---

## `climate`

Profilo climatologico multi-anno.

```bash
python -m thermalcomfort climate "Firenze:43.7696,11.2558" --start-year 2010 --end-year 2023
```

Profilo orario mese specifico:

```bash
python -m thermalcomfort climate "Firenze:43.7696,11.2558" --start-year 2010 --end-year 2023 --month 7
```

Opzioni:

- `location`
- `--start-year`, `--end-year`
- `--month` (1-12, opzionale)
- comuni

---

## `rank`

Classifica località per comfort climatico.

```bash
python -m thermalcomfort rank "Firenze:43.7696,11.2558" "Londra:51.5074,-0.1278" --month 4
```

Opzioni:

- `locations`
- `--start-year`, `--end-year`
- `--month` opzionale
- comuni

---

## `map`

Mappa comfort a timestamp.

```bash
python -m thermalcomfort map "Firenze:43.7696,11.2558" "Roma:41.9028,12.4964" --datetime "2024-07-14 12:00"
```

Opzioni:

- `locations`
- `--datetime` (UTC)
- `--static` (matplotlib invece di HTML folium)
- `--variable` con valori validi:
  - `utci`
  - `temperature_2m`
  - `mrt`
  - `heat_index`
  - `wind_chill`
  - `wbgt_outdoor`
  - `apparent_temperature`
- comuni

---

## `forecast`

Confronto forecast vs actual (finestra storica breve, tipicamente ultimi ~92 giorni).

```bash
python -m thermalcomfort forecast "Firenze:43.7696,11.2558" --start 2026-07-15 --end 2026-07-25 --variable utci
```

Opzioni:

- `location`
- `--start`, `--end`
- `--variable` con stessi valori validi di `compare`
- comuni
