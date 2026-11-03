# Navitas — AI Energy Optimizer for Textile Mills

**Same work. Smaller electricity bill.** Navitas re-plans factory production to cut
electricity cost, understands plain-English constraints and photos of electricity
bills, and proves every plan with an independent checker.

**Headline result (real production data): ~30% lower energy cost** vs a
fastest-mode, tariff-blind schedule (24–34% depending on allowed machine load),
**0 rule violations**, reproducible from an append-only run log. Measured on a
real 3-machine, 6-day production benchmark from GECAD/Polytechnic of Porto
(Zenodo 4106746). Full proof: [`results/SAVINGS_PROOF_v2.md`](results/SAVINGS_PROOF_v2.md).

---

## Why

In Faisalabad, around 40% of power-loom units have reportedly closed, with
electricity costs among the main pressures (per industry representatives,
reported by Pakistani press, Oct 2026). Taxes, imports and yarn prices a mill
cannot control — **when and how its machines run, it can.** Navitas targets
exactly that.

## What it does (demo flow)

1. **You describe a problem in plain words** — "MAQ119 is down on day 3" or
   "nothing runs 18:30–22:30" — or **upload a photo of an electricity bill**.
2. **Muse Spark Open (Meta, via Baseten)** parses it into structured
   constraints (tool calling), or reads the tariff from the photo (vision).
   Every model call is routed through `llm.py` and logged to
   `logs/calls.jsonl` with model name, host, latency and token usage.
3. **An exact CP-SAT solver** re-plans machine modes and start times.
4. **An independent verifier** (`engine/verify_schedule.py`, shares no code
   with the solver) re-checks every rule from scratch: machine/mode
   eligibility, no overlaps, day boundaries, deadline, task order, collision
   rules — and recomputes cost and kWh.
5. **Spark explains the result** in plain language, quoting only numbers the
   checker verified.

Three pre-solved scenarios ship with the repo (0 violations each):

| Scenario | Navitas | Plain plan under same constraint |
|---|---|---|
| No extra constraints | Rs 23,075 (31.4% cheaper) | Rs 33,632 |
| MAQ119 down all of day 3 | Rs 25,603 (28.5% cheaper) | Rs 35,817 |
| Nothing runs 18:30–22:30 | Rs 30,564 — valid plan found | plain plan **cannot meet the deadline** |

If the network or API fails mid-demo, the UI replays the last **real** model
answers, always badged `RECORDED` vs `LIVE` — never silently.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # add your Baseten/Fireworks keys
python -m pytest tests -q       # 19 tests, no keys needed
python scripts/record_demo_answers.py   # makes live model calls, saves replay
python app/server.py            # open http://127.0.0.1:8000
```

Reproduce the core result: `python engine/solve2.py pk 1060 120`
(expected: ~31% saving, 0 violations; raw output also lands in `results/`).

## Built during the hackathon (Meta Global AI Developer Hackathon, Oct 27 – Nov 4 2026)

- **Oct 27–29** — CP-SAT solver and independent checker for the real GECAD
  benchmark; model provenance router `llm.py` with call logging.
- **Nov 1** — fresh repo: proof pipeline (append-only `results/runs.jsonl`,
  18-config matrix, `SAVINGS_PROOF_v2.md`), independent verifier tests.
- **Nov 2–3** — **Muse Spark agent layer**: tool-calling constraint parser,
  bill-photo vision, replay store, demo web app. 21 live Spark calls logged
  on Nov 3 (`logs/calls.jsonl`).

Pre-existing public components we built on: the GECAD benchmark dataset
(cited, not redistributed), CP-SAT (OR-Tools), and open datasets listed in
`DATA_SOURCES.md`. No third-party code is embedded.

**AI tooling disclosure:** code was written with AI assistance (Claude and
Muse Spark via coding agents); all components are owned and verified by the
author, and every model call in the product is logged.

## How it's scored / verified

- **Reproducible results:** every solver run is one append-only JSON line in
  `results/runs.jsonl` (params, code+data SHA256, tariff flags, costs, bound,
  schedule hash). Regenerate the proof: `python scripts/regen_proof.py`.
- **Independent check:** my re-verification of all 18 committed schedules —
  constraint compliance and cost recomputation — passes 18/18.
- **Against published work:** on the dataset authors' own MIBEL prices and
  their published solution, our median cost is **19.6% lower** (range 8–26%
  across 9 runs; our solver was not even solar-aware).

## Assumptions & limits (read before quoting any number)

- The benchmark is a small **hang-tag textile production cell**, not a
  Pakistani dye house; savings on other plants will differ.
- Sample tariff (peak Rs 35.68 / off-peak Rs 22.83, window 18:30–22:30) is
  from Feb-2026 news reports of the NEPRA notification; **peak window and
  export price (Rs 8.13) are unverified assumptions**.
- The ~30% saving assumes the lower-energy machine/task **modes are
  interchangeable at equal product quality** — true inside the benchmark's
  own model, **not yet confirmed with the dataset authors**.
- "Plain plan" baseline is our definition: tariff-blind, fastest-mode,
  earliest-deadline-first.
- Solver gap not closed (~8% bound); solves are 1-core, 2–4 minutes.

## Stack

- **Muse Spark Open** (`meta-models/muse-spark-open-1026`, Meta open-weight
  model) on **Baseten**, Fireworks fallback — tool calling + vision, logged
  via `llm.py`. See `MODEL_PROVENANCE.md`.
- OR-Tools CP-SAT (exact solver), Python stdlib web server, vanilla JS front end.
- Datasets & licenses: `DATA_SOURCES.md` (GECAD license not stated → cited and
  linked only; Irish factory CC BY 4.0; others listed there).

## Business model (startup track)

Per-mill setup + a percentage of *verified* savings (checker-signed), sold
first to multi-machine dyeing/finishing mills in Faisalabad — plants with
real scheduling freedom, unlike single-job power looms.
