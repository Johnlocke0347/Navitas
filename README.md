# Navitas-new — Energy-Optimization Engine (Real Data)

Fresh start from `navitas-old` / `navitas_real_data`. No numbers tuned, solver logic unchanged.

## Structure

```
engine/       # solver logic (load.py, engine.py, solve2.py, run3.py)
data/         # gitignored, see DATA_SOURCES.md — contains GECAD JSONs in data/gecad/
results/      # solver outputs (sched*.json, res*.json)
tests/        # checker tests
scripts/      # helper scripts
app/          # empty (future UI)
```

## Quick Start

```bash
pip install -r requirements.txt  # if present
python engine/solve2.py pk 1060 120
python engine/run3.py pk 120
pytest tests/test_checker.py -v
```

## Data

See `DATA_SOURCES.md` for URLs, licenses, and usage per dataset.
`data/` is gitignored; download per instructions there.

## Model Provenance

See `MODEL_PROVENANCE.md` — Muse Spark Open via Baseten/Fireworks, routed through `llm.py`.

## Results

See `engine/RESULTS.md` (copied verbatim from navitas_real_data) for baseline vs optimized costs.

## Constraints Modelled

- time leap (no crossing day boundary, DAY=192, 5-min periods)
- task order Harden[1.5] before Harden[2] (paired by count, per INPUT JSON)
- collision Sublimation vs Harden[2]
- deadline (one request, period 960)
- unit sequence (tasks of one unit in listed product order, except Harden pair)

Solver: stage 1 (mode choice, min energy, capacity 1060) + stage 2 (CP-SAT start times, 120s, 1 core).

