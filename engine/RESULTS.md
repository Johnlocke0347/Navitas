# Navitas on real data: GECAD hang-tag production line (Zenodo 4106746), v2 after Order-constraint fix
Input: Input_JSON_Schedule_Optimization.json (3 machines, 275 task instances, 132 units, 6 days x 192 five-minute periods).
Constraints modelled = the four the paper says the case study used: time leap, task order (Harden[1.5] before Harden[2], per the INPUT JSON direction, paired by count), task collision (Sublimation vs Harden[2]), deadline (one request, period 960).
Extra restriction we add: tasks of one unit run in listed product order (except the Harden pair). The paper says product-task-order was NOT used, so our model is stricter than theirs.
Baseline = tariff-blind earliest-deadline schedule, each task on the machine/mode that finishes first (MY definition).
Solver = stage 1 (machine+mode per task, min energy, machine capacity <= 1060 periods) + stage 2 (CP-SAT start times, 120 s, 1 core, gap to bound NOT closed). 0 violations by independent checker.

| Scenario (6 days) | Baseline | Optimized |
|---|---|---|
| Pakistan TOU illustrative (Rs), no PV | 33,632 | 23,008 (-31.6%) |
| Dataset MIBEL prices (EUR), no PV | 87.68 | 61.63 (-29.7%) |
| MIBEL + dataset solar, grid import only (authors' cost definition) | 44.74 | 27.85 (-37.8%); authors' published GA = 36.42, ours 23.5% lower |
Energy: 1,316 kWh -> 924 kWh.

## Correction history
First version put Harden[2] before Harden[1.5] (followed the paper's wording and product list order). The input JSON says Harden[1.5] first. That version broke the dataset's Order rule (3 violations); rerun after the fix gave the numbers above.

## Caveats
- Saving comes almost entirely from choosing lower-energy modes (Harden[1] and Harden[0.5]). The paper defines a task mode as "a combination of energy and time profiles" for executing a task and its GA swaps modes freely; it says nothing about product quality. Unconfirmed.
- Pakistan tariff (B2 35.68/22.83 reported Feb 2026) fine; 18:30-22:30 peak window and Rs8.13 export UNVERIFIED.
- Paper says a 3 kW PV array; file's availability peaks near 33 kW-equivalent (2,749 Wh/5 min). Unresolved.
