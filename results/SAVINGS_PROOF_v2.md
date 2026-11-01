# SAVINGS_PROOF v2 (regenerated from results/runs.jsonl)

Log lines: 32 (append-only; failures included). Configs with a successful run: 18 of 18.
Independent re-check of every schedule file (SHA256 vs log, my own constraint check, cost recomputed): 18 of 18 pass.

## 1. Headline (saving vs tariff-blind fastest-mode baseline, no solar)

| tariff | cap | machine load (cap/1152) | saving range over 3 seeds | median | optimized kWh (baseline 1315.7) |
|---|---|---|---|---|---|
| Pakistan TOU (illustrative) | 1000 | 87% | 23.4% to 24.1% | 23.6% | 1007.5 |
| Pakistan TOU (illustrative) | 1060 | 92% | 29.2% to 30.8% | 30.1% | 923.9 |
| Pakistan TOU (illustrative) | 1100 | 95% | 33.7% to 33.9% | 33.9% | 877.2 |
| MIBEL (dataset prices) | 1000 | 87% | 23.1% to 23.2% | 23.2% | 1007.5 |
| MIBEL (dataset prices) | 1060 | 92% | 29.5% to 29.7% | 29.6% | 923.9 |
| MIBEL (dataset prices) | 1100 | 95% | 33.1% to 33.3% | 33.2% | 877.2 |

The capacity cap is a modelling choice (how busy a machine may get). Every number is conditional on lower-energy modes giving the same product (UNCONFIRMED).

## 2. Against the dataset authors' published GA solution (MIBEL prices, dataset solar, grid-import-only cost)

Authors' reported cost: 36.42 EUR. Baseline (ours): 44.74 EUR. Our schedules were NOT optimized for solar.

| cap | seed | our cost with solar (EUR) | below authors |
|---|---|---|---|
| 1000 | 7 | 30.38 | 16.6% |
| 1000 | 11 | 33.55 | 7.9% |
| 1000 | 23 | 32.41 | 11.0% |
| 1060 | 7 | 28.34 | 22.2% |
| 1060 | 11 | 29.32 | 19.5% |
| 1060 | 23 | 28.04 | 23.0% |
| 1100 | 7 | 29.28 | 19.6% |
| 1100 | 11 | 28.15 | 22.7% |
| 1100 | 23 | 27.09 | 25.6% |

Across 9 runs: min 7.9%, median 19.6%, max 25.6%. Quote the range, not one run.

## 3. All runs in the log

| # | UTC | tariff | cap | seed | time limit | status | success | optimized cost | git dirty |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-31T21:18:04 | pk | 1000 | 7 | 90 | FEASIBLE | True | 25537.88538 | True |
| 2 | 2026-10-31T21:19:42 | mibel | 1000 | 7 | 90 | UNKNOWN | False | - | True |
| 3 | 2026-10-31T21:21:22 | pk | 1000 | 11 | 90 | FEASIBLE | True | 25750.617129999995 | True |
| 4 | 2026-10-31T21:23:01 | mibel | 1000 | 11 | 90 | UNKNOWN | False | - | True |
| 5 | 2026-10-31T21:24:41 | pk | 1000 | 23 | 90 | FEASIBLE | True | 25693.357529999997 | True |
| 6 | 2026-10-31T21:26:19 | mibel | 1000 | 23 | 90 | UNKNOWN | False | - | True |
| 7 | 2026-10-31T21:27:56 | pk | 1060 | 7 | 90 | FEASIBLE | True | 23521.63408 | True |
| 8 | 2026-10-31T21:29:36 | mibel | 1060 | 7 | 90 | UNKNOWN | False | - | True |
| 9 | 2026-10-31T21:31:15 | pk | 1060 | 11 | 90 | FEASIBLE | True | 23809.641129999996 | True |
| 10 | 2026-10-31T21:32:54 | mibel | 1060 | 11 | 90 | UNKNOWN | False | - | True |
| 11 | 2026-10-31T21:34:34 | pk | 1060 | 23 | 90 | FEASIBLE | True | 23265.55928 | True |
| 12 | 2026-10-31T21:36:13 | mibel | 1060 | 23 | 90 | UNKNOWN | False | - | True |
| 13 | 2026-10-31T21:37:56 | pk | 1100 | 7 | 90 | FEASIBLE | True | 22231.25291 | True |
| 14 | 2026-10-31T21:39:35 | mibel | 1100 | 7 | 90 | UNKNOWN | False | - | True |
| 15 | 2026-10-31T21:41:16 | pk | 1100 | 11 | 90 | FEASIBLE | True | 22304.67781 | True |
| 16 | 2026-10-31T21:42:54 | mibel | 1100 | 11 | 90 | UNKNOWN | False | - | True |
| 17 | 2026-10-31T21:44:34 | pk | 1100 | 23 | 90 | FEASIBLE | True | 22223.19596 | True |
| 18 | 2026-10-31T21:46:13 | mibel | 1100 | 23 | 90 | UNKNOWN | False | - | True |
| 19 | 2026-10-31T21:57:45 | mibel | 1000 | 7 | 150 | FEASIBLE | True | 67.33596241 | False |
| 20 | 2026-10-31T22:03:07 | mibel | 1000 | 11 | 150 | FEASIBLE | True | 67.32333154 | True |
| 21 | 2026-10-31T22:05:46 | mibel | 1000 | 23 | 150 | FEASIBLE | True | 67.42040146 | True |
| 22 | 2026-11-01T13:15:54 | mibel | 1060 | 7 | 150 | UNKNOWN | False | - | False |
| 23 | 2026-11-01T13:18:35 | mibel | 1060 | 7 | 240 | FEASIBLE | True | 61.68329582 | True |
| 24 | 2026-11-01T13:22:44 | mibel | 1060 | 11 | 150 | UNKNOWN | False | - | True |
| 25 | 2026-11-01T13:25:22 | mibel | 1060 | 11 | 240 | FEASIBLE | True | 61.83026708999999 | True |
| 26 | 2026-11-01T13:29:30 | mibel | 1060 | 23 | 150 | FEASIBLE | True | 61.739923440000005 | True |
| 27 | 2026-11-01T13:32:09 | mibel | 1100 | 7 | 150 | UNKNOWN | False | - | True |
| 28 | 2026-11-01T13:34:48 | mibel | 1100 | 7 | 240 | FEASIBLE | True | 58.534163840000005 | True |
| 29 | 2026-11-01T13:38:56 | mibel | 1100 | 11 | 150 | UNKNOWN | False | - | True |
| 30 | 2026-11-01T13:41:35 | mibel | 1100 | 11 | 240 | FEASIBLE | True | 58.495225139999995 | True |
| 31 | 2026-11-01T13:45:43 | mibel | 1100 | 23 | 150 | UNKNOWN | False | - | True |
| 32 | 2026-11-01T13:48:22 | mibel | 1100 | 23 | 240 | FEASIBLE | True | 58.62361916 | True |

(modes_only is NOT reported anywhere: that intermediate schedule can violate constraints.)

## 4. Assumptions and limits
- Lower-energy mode substitution: product quality unconfirmed (ask GECAD authors).
- Baseline is our own definition (tariff-blind earliest-deadline, fastest-finishing mode).
- Tariff: B2 35.68/22.83 Rs/kWh via news reports only; peak window 18:30-22:30 and export Rs8.13 UNVERIFIED.
- Solar array size in the dataset is unresolved (paper says 3 kW; file looks ~10x larger).
- Solver: CP-SAT, 1 core, 90-240 s; gap to bound not closed.
- Many runs show git_dirty=True because results/ and logs/ change during runs; code hashes are in runs.jsonl.
- Data is a hang-tag textile line (3 machines, 6 days), not a Pakistani mill.