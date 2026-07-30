# Thermal Comfort Visualization System

Python toolkit for **outdoor perceived thermal comfort** analysis across time and geography.

Core capabilities:

- hourly time-series analysis for one location
- multi-location comparison
- geographic mapping (interactive and static)
- multi-year climatological analysis
- forecast-vs-actual comparison

Main package: [`thermalcomfort/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/thermalcomfort)

---

## Installation

From repository root:

```bash
pip install -r requirements.txt
```

Alternative:

```bash
pip install -e .
```

---

## Quick start

### Python API

```python
from thermalcomfort import ThermalComfortSystem, Location, ComfortParams

tcs = ThermalComfortSystem()
loc = Location(43.7696, 11.2558, "Florence")
params = ComfortParams(activity="walking", sun_exposure=0.5)

df = tcs.get(loc, "2024-07-01", "2024-07-03 23:00", params=params)
tcs.plot(df, title="Florence")
```

### CLI

```bash
python -m thermalcomfort show "Florence:43.7696,11.2558" --start 2024-07-01 --end 2024-07-03
```

---

## Documentation

Complete documentation is in [`docs/`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/docs):

- installation and project setup
- physical model and data sources
- sampling, interpolation, and data provenance
- complete CLI reference and parameters
- Python API reference (`ThermalComfortSystem`, `ClimateAnalysis`)
- valid `--variable` values by command
- usage examples for `monthly_stats()`, `hourly_profile()`, `rank_locations()`

### Build documentation locally

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

### Read the Docs configuration

- [`.readthedocs.yaml`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/.readthedocs.yaml)
- [`mkdocs.yml`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/mkdocs.yml)

---

## Notebook

Main notebook: [`examples/interactive.ipynb`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/interactive.ipynb)

---

## Additional examples

- [`examples/basic_usage.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/basic_usage.py)
- [`examples/compare_locations.py`](/Users/lbusoni/git/miscella.worktrees/thermal-comfort-visualization-system/examples/compare_locations.py)
