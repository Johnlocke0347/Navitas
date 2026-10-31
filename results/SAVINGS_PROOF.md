# SAVINGS_PROOF — Audit Trail for Savings Claim
> Generated from `results\runs.jsonl` — 18 runs (append-only, failures included). Do not edit manually.
> Input SHA256: `5cecb2eb95437d6b789726f302860cefb446731af9eadba2a8379af5644ed169`
> Git commit at generation: `bd4c2fe7d42a5ef7d8b71fdc3471d89c6abb018d` dirty=True
> Python 3.12.10, ortools 9.15.6755, CPU 8

## 1. Table of ALL runs
| # | cap | seed | tariff | baseline cost | optimized cost | saving % | baseline kWh | optimized kWh | viol base/opt | status | wall (s) | bound | schedule |
|---|-----|------|--------|---------------|----------------|----------|--------------|---------------|---------------|--------|----------|-------|----------|
| 1 | 1000 | 7 | pk | 33631.65 | 25537.89 | 24.07% | 1315.709 | 1007.471 | 0/0 | FEASIBLE | 90.5 | 23000.6 | results\sched2_pk_1000_seed7.json |
| 2 | 1000 | 7 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.9 | - | stage2 infeasible |
| 3 | 1000 | 11 | pk | 33631.65 | 25750.62 | 23.43% | 1315.709 | 1007.471 | 0/0 | FEASIBLE | 90.6 | 23000.6 | results\sched2_pk_1000_seed11.json |
| 4 | 1000 | 11 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.5 | - | stage2 infeasible |
| 5 | 1000 | 23 | pk | 33631.65 | 25693.36 | 23.60% | 1315.709 | 1007.471 | 0/0 | FEASIBLE | 90.6 | 23000.6 | results\sched2_pk_1000_seed23.json |
| 6 | 1000 | 23 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 88.8 | - | stage2 infeasible |
| 7 | 1060 | 7 | pk | 33631.65 | 23521.63 | 30.06% | 1315.709 | 923.891 | 0/0 | FEASIBLE | 91.8 | 21092.5 | results\sched2_pk_1060_seed7.json |
| 8 | 1060 | 7 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 89.2 | - | stage2 infeasible |
| 9 | 1060 | 11 | pk | 33631.65 | 23809.64 | 29.20% | 1315.709 | 923.891 | 0/0 | FEASIBLE | 91.3 | 21092.5 | results\sched2_pk_1060_seed11.json |
| 10 | 1060 | 11 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 90.8 | - | stage2 infeasible |
| 11 | 1060 | 23 | pk | 33631.65 | 23265.56 | 30.82% | 1315.709 | 923.891 | 0/0 | FEASIBLE | 91.2 | 21092.5 | results\sched2_pk_1060_seed23.json |
| 12 | 1060 | 23 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.6 | - | stage2 infeasible |
| 13 | 1100 | 7 | pk | 33631.65 | 22231.25 | 33.90% | 1315.709 | 877.227 | 0/0 | FEASIBLE | 91.7 | 20027.1 | results\sched2_pk_1100_seed7.json |
| 14 | 1100 | 7 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.4 | - | stage2 infeasible |
| 15 | 1100 | 11 | pk | 33631.65 | 22304.68 | 33.68% | 1315.709 | 877.227 | 0/0 | FEASIBLE | 90.7 | 20027.1 | results\sched2_pk_1100_seed11.json |
| 16 | 1100 | 11 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.9 | - | stage2 infeasible |
| 17 | 1100 | 23 | pk | 33631.65 | 22223.20 | 33.92% | 1315.709 | 877.227 | 0/0 | FEASIBLE | 90.8 | 20027.1 | results\sched2_pk_1100_seed23.json |
| 18 | 1100 | 23 | mibel | 87.68362445 | - | - | 1315.709 | - | 0/- | UNKNOWN | 92.3 | - | stage2 infeasible |

## 2. Min/Median/Max saving per cap (pk successes only)
| cap | n success | min % | median % | max % | mean % |
|-----|-----------|-------|----------|-------|--------|
| 1000 | 3 | 23.43% | 23.60% | 24.07% | 23.70% |
| 1060 | 3 | 29.20% | 30.06% | 30.82% | 30.03% |
| 1100 | 3 | 33.68% | 33.90% | 33.92% | 33.83% |

> Do not pick the best — all runs are shown above.

## 3. Independent verifier output (representative schedule)
Representative: `results/sched2_pk_1060_seed7.json` (cap 1060, seed 7, pk) — also baseline verified.
```
Verifying schedule: D:\Navitas-new\results\sched2_pk_1060_seed7.json  tariff=pk  tasks=275/275
PASS: machine/mode eligibility - 0 fails
PASS: day boundary (time leap) - 0 fails
PASS: deadline - 0 fails
PASS: overlap (no machine overlap) - 0 fails
PASS: unit sequence - 0 fails
PASS: collision Sublimation vs Harden[2] - 0 fails
PASS: order H1.5-before-H2 (paired) - 0 fails
PASS: missing-tasks - 0 fails
PASS: cost/kWh recomputed - 0 fails
Recomputed cost=23521.63 kWh=923.891
Overall: PASS

--- baseline ---

=== Baseline verification ===
PASS: machine/mode eligibility
PASS: day boundary (time leap)
PASS: deadline
PASS: overlap (no machine overlap)
PASS: unit sequence
PASS: collision Sublimation vs Harden[2]
PASS: order H1.5-before-H2 (paired)
PASS: missing-tasks
PASS: cost/kWh recomputed
Baseline cost=33631.65 kWh=1315.709 tasks=275
Baseline Overall: PASS
```

## 4. By-task kWh breakdown (baseline vs optimized) — where saving comes from
Pk tariff, cap 1060, seed 7 representative. Saving comes almost entirely from lower-energy modes (Harden[1] and Harden[0.5]).
| task | baseline kWh | optimized kWh | delta kWh | delta % |
|------|--------------|---------------|-----------|---------|
| Anti-Shrinkage | 102.419 | 102.419 | +0.000 | +0.0% |
| Harden[0.5] | 92.632 | 41.028 | -51.604 | -55.7% |
| Harden[1.5] | 140.432 | 140.432 | +0.000 | +0.0% |
| Harden[1] | 526.934 | 159.588 | -367.346 | -69.7% |
| Harden[2] | 55.815 | 55.815 | +0.000 | +0.0% |
| Ironing | 323.037 | 350.169 | +27.132 | +8.4% |
| Sublimation | 74.440 | 74.440 | +0.000 | +0.0% |
| **TOTAL** | **1315.709** | **923.891** | **-391.818** | **-29.8%** |

## 5. Assumptions and limits
- **Mode substitution quality unconfirmed:** Paper defines a task mode as "a combination of energy and time profiles" and GA swaps modes freely; nothing about product quality. Saving via lower-energy modes (Harden[1] TM1, Harden[0.5] TM4) is unconfirmed for quality.
- **Baseline definition:** Tariff-blind earliest-deadline schedule, each task on the machine/mode that finishes earliest (my definition). Not the paper's GA baseline, but independent 0-violation baseline.
- **Extra restriction:** Tasks of one unit run in listed product order (except Harden pair). Paper says product-task-order was NOT used, so our model is stricter than theirs.
- **Tariff:** B2 rates Rs35.68/22.83 confirmed via news only (Dawn 1973828, NEPRA Feb 2026). Peak window 18:30-22:30 and export price Rs8.13 are **UNVERIFIED** assumptions in `engine/engine.py` → `pk_tariff()`; do not change without verification.
- **Solar:** Dataset solar availability used only for shape; absolute scale ILLUSTRATIVE, not Pakistan yield. PVGIS not used for absolute.
- **Solver gap not closed:** Stage2 CP-SAT 90s wall, 1 core, bound 21092 vs obj 23105 (gap ~8%), not proven optimal. Saving is feasible, not optimal.
- **MIBEL failures:** 9/18 runs (all mibel) were infeasible/UNKNOWN within 90s timelimit; pk successes are robust across caps/seeds (9/9 pk success). Do not generalize to mibel without longer timelimit.
- **Data:** `data/` gitignored, SHA256 logged per run. See `DATA_SOURCES.md` for URLs/licenses. German/Irish/Kaggle India solar not used for absolute kW, only shape evidence.

---
Generated D:\Navitas-new\scripts\generate_proof.py at UTC 2026-10-31T21:52:09.496185Z
