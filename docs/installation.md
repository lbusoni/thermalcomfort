# Installazione

## Requisiti

- Python 3.11+ (consigliato 3.12)

## Install standard

Da root del repository:

```bash
pip install -r requirements.txt
```

Questo comando installa:

1. dipendenze runtime
2. package locale `thermalcomfort` (`-e .`)

In questo modo il notebook non fallisce con `ModuleNotFoundError: thermalcomfort`.

## Alternative

```bash
pip install -e .
```

oppure:

```bash
pip install .
```

## Verifica installazione

```bash
python -c "from thermalcomfort import ThermalComfortSystem; print('ok')"
```

## Notebook

Notebook consigliato: `examples/interactive.ipynb`

La prima cella gestisce automaticamente:

- backend matplotlib widget con fallback inline
- aggiunta del root progetto a `sys.path` quando il notebook gira da `examples/`

## Documentazione locale (MkDocs)

```bash
pip install -r docs/requirements.txt
mkdocs serve
```
