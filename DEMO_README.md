# Navitas demo layer (built during the hackathon)

What it does: you type a what-if in plain English ("MAQ119 is down on day 3"). Muse Spark (through llm.py, every call logged in logs/calls.jsonl)
turns it into constraints and calls the exact CP-SAT solver as a tool; an independent checker verifies the schedule; Spark explains the numbers it was given.
Spark can also read the tariff off a photographed bill (vision); the numbers it reads are sanity-checked before use.

## Run
1. `python -m pytest tests -q`            (19 tests, no network, no keys needed)
2. `python scripts/record_demo_answers.py` (needs .env keys + connection; makes REAL Muse Spark calls and saves them for replay)
3. `python app/server.py`                  then open http://127.0.0.1:8000

Answer labels in the UI: LIVE (model call just made) / RECORDED (a real earlier Muse Spark answer, replayed) / TEMPLATE (no model, fixed text). Never mixed up.
Env: NAVITAS_LIVE=0 (replay only), NAVITAS_CALL_TIMEOUT=45, NAVITAS_SOLVE_S=60.
New what-ifs not in app/cache are solved live (about a minute); `python scripts/precompute_scenarios.py 90 4` pre-solves the three examples with more workers.

## Honest limits
Real GECAD hang-tag benchmark, not a live mill. Lower-energy modes assumed equal quality (unconfirmed). Tariff peak window and export price unverified. The sample tariff sheet is synthetic.
