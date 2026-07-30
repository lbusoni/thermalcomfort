# Thermal Comfort Visualization System

Toolkit Python per analizzare il **comfort termico percepito outdoor** nel tempo e nello spazio:

- serie temporali orarie
- confronto tra località
- mappe geografiche
- analisi climatologica multi-anno
- confronto previsioni vs reanalisi

Il pacchetto principale è [`thermalcomfort/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort).

---

## Installazione corretta (risolve `ModuleNotFoundError: thermalcomfort`)

Da root repository:

```bash
pip install -r requirements.txt
```

`requirements.txt` include `-e .`, quindi installa anche il package locale
`thermalcomfort` in modalità editable.

Alternative equivalenti:

```bash
pip install -e .
```

oppure:

```bash
pip install .
```

---

## Uso rapido

### Python API

```python
from thermalcomfort import ThermalComfortSystem, Location, ComfortParams

tcs = ThermalComfortSystem()
loc = Location(43.7696, 11.2558, "Firenze")
params = ComfortParams(activity="walking", sun_exposure=0.5)

df = tcs.get(loc, "2024-07-01", "2024-07-03 23:00", params=params)
tcs.plot(df, title="Firenze")
```

### CLI

```bash
python -m thermalcomfort show "Firenze:43.7696,11.2558" --start 2024-07-01 --end 2024-07-03
```

---

## Documentazione completa

È disponibile in [`docs/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/docs):

- panoramica e modello fisico-climatologico
- database/sorgenti dati usate
- riferimento completo comandi CLI e parametri
- riferimento API Python (`ThermalComfortSystem`, `ClimateAnalysis`)
- valori validi di `--variable` per ogni comando
- esempi dettagliati di `monthly_stats()`, `hourly_profile()`, `rank_locations()`

### Build locale docs (MkDocs)

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

### Read the Docs

Repo predisposto con [`.readthedocs.yaml`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/.readthedocs.yaml)
e [`mkdocs.yml`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/mkdocs.yml).

---

## Notebook

Notebook principale: [`examples/interactive.ipynb`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/interactive.ipynb)

La prima cella ora:

- prova `%matplotlib widget` con `ipympl`
- fa fallback a `%matplotlib inline` se backend widget non disponibile
- aggiunge automaticamente il root progetto a `sys.path` quando eseguito da `examples/`

---

## Esempi aggiuntivi

- [`examples/basic_usage.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/basic_usage.py)
- [`examples/compare_locations.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/compare_locations.py)
