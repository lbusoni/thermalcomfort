# Installation

## Requirements

- Python 3.11+ (3.12 recommended)

## Standard installation

From the repository root:

```bash
pip install -r requirements.txt
```

This installs runtime dependencies and the local `thermalcomfort` package.

## Alternative installation commands

```bash
pip install -e .
```

or:

```bash
pip install .
```

## Verify installation

```bash
python -c "from thermalcomfort import ThermalComfortSystem; print('ok')"
```

## Notebook

Recommended notebook:

- `examples/interactive.ipynb`

## Build docs locally

```bash
pip install -r docs/requirements.txt
mkdocs serve
```
