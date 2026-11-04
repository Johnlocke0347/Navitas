# Navitas — AI-Powered Energy Optimization for Textile Manufacturing

**Same production. Lower electricity costs. Verified schedules.**

Navitas is an AI-powered factory energy optimization system that helps manufacturers make better decisions about when and how their machines operate.

Operators describe production constraints in natural language or provide an electricity-bill image. Meta Muse Spark interprets the request, a constraint-based optimization engine generates a production schedule, and an independent verifier checks the result before it is presented.

**Built for the Meta Global AI Developer Hackathon 2026 · Push the Frontier**

---

## The problem

Electricity is a major operating expense for energy-intensive manufacturing. Yet production schedules are often created around deadlines and machine availability without fully accounting for time-varying electricity prices.

Factories cannot always control electricity tariffs. They can, however, make better decisions about when eligible production tasks run, which machine modes are selected, and how production is distributed across available time.

Navitas explores that opportunity through constrained energy-aware scheduling.

## How Navitas works

1. **Describe the production situation.** An operator enters a natural-language instruction, such as "MAQ119 is unavailable on day 3" or "No machines can operate between 18:30 and 22:30."
2. **Interpret the request with Meta Muse Spark.** The model converts the operator's request into structured constraints. The application also supports electricity-bill image interpretation.
3. **Optimize the schedule.** OR-Tools CP-SAT searches for a lower-cost schedule while respecting the modeled production constraints.
4. **Verify independently.** A separate verification implementation checks the resulting schedule and recomputes its energy cost.
5. **Explain the result.** Muse Spark presents the verified outcome in understandable language.

The LLM does not independently decide whether a schedule is valid. The optimization engine generates the schedule, and the independent checker evaluates it.

## Architecture

```text
Factory operator
      |
      v
Natural-language request / bill image
      |
      v
Meta Muse Spark Open
      |
      v
Structured constraints
      |
      v
OR-Tools CP-SAT optimizer
      |
      v
Candidate production schedule
      |
      v
Independent schedule verifier
      |
      v
Verified cost, energy and schedule
      |
      v
Muse Spark explanation
```

### Technology

| Component | Technology |
|---|---|
| AI model | Meta Muse Spark Open |
| Primary inference | Baseten |
| Model fallback | Fireworks |
| Optimization | Google OR-Tools CP-SAT |
| Backend | Python |
| Web application | Python standard-library server |
| Frontend | HTML, CSS and JavaScript |
| Verification | Independent Python implementation |

Model routing, provider configuration, model restrictions and call-provenance logging are implemented in `llm.py`. See [MODEL_PROVENANCE.md](MODEL_PROVENANCE.md).

## Benchmark results

Navitas was evaluated on a real production-line scheduling and energy dataset from GECAD / Polytechnic of Porto, published on Zenodo.

**Two results, with different assumptions.**

**A. Scheduling only, no machine or mode changes: about 5% lower modeled electricity cost** (Rs 33,632 to Rs 31,989, 4.89%) against a tariff-blind, fastest-mode baseline. Every task keeps its baseline machine and mode; only start times move. This needs no assumption about product quality.

**B. With lower-energy modes allowed: about 30% lower** (median 30.1% at the 1060 machine-capacity setting; 23-34% across settings), same baseline, same illustrative Pakistan tariff. Most of this saving (about 94% of the energy saved in the representative run) comes from running two process steps, Harden[1] and Harden[0.5], in their lower-energy machine modes. The dataset contains no product-quality measurements, so we assume those modes make an equivalent product. That is an assumption, not a finding; it needs to be confirmed by the plant that would use them.

### Pakistan tariff experiment

| Machine capacity | Saving range across 3 seeds | Median saving |
|---:|---:|---:|
| 1000 | 23.4–24.1% | 23.6% |
| 1060 | 29.2–30.8% | **30.1%** |
| 1100 | 33.7–33.9% | 33.9% |
### Scheduling-only experiment (modes frozen)

| | Baseline | Scheduling only | Modes + scheduling |
|---|---:|---:|---:|
| Cost (Rs, 6 days) | 33,632 | 31,989 | 23,522 (median) |
| Saving | - | 4.89% | 30.06% (29.2-30.8%) |
| Energy (kWh) | 1,315.7 | 1,315.7 | 923.9 |

Method: every operation keeps its baseline machine and mode (verified: 0 mode changes); only start times change, using a constraint-preserving local search. A CP-SAT run of this variant ran out of memory on our test machine, so 4.89% is a verified feasible result, not a proven optimum, and should be read as a floor. The two savings are not additive: timing is worth more or less depending on which modes are used. Demand response is a separate experiment and is not included here. Files: `results/quality_validation/`.
### MIBEL dataset tariff experiment

| Machine capacity | Saving range across 3 seeds | Median saving |
|---:|---:|---:|
| 1000 | 23.1–23.2% | 23.2% |
| 1060 | 29.5–29.7% | 29.6% |
| 1100 | 33.1–33.3% | 33.2% |

### Independent verification

- 32 solver attempts recorded in the append-only experiment log.
- 18 successful configurations out of 18.
- **18/18 schedules independently rechecked successfully.**
- Schedule hashes, constraint violations and recomputed costs were checked against the recorded experiment results.

### Comparison with published work

Against the dataset authors' published genetic-algorithm solution, Navitas's schedules produced a median 19.6% lower grid-import-only cost across nine comparisons, with results ranging from 7.9% to 25.6%.

This comparison uses the dataset's MIBEL prices and solar data. Navitas's schedules were not optimized for solar generation.

Full experimental methodology, run records and calculations:

[Read the complete savings proof](results/SAVINGS_PROOF_v2.md)

## Demonstration scenarios

The repository includes three precomputed scenarios with independently verified schedules.

| Scenario | Navitas result | Baseline comparison |
|---|---:|---:|
| No additional constraints | Rs 23,075 | Rs 33,632 |
| MAQ119 unavailable on day 3 | Rs 25,603 | Rs 35,817 |
| No operation between 18:30–22:30 | Rs 30,564 | Baseline cannot meet the deadline |

The first two scenarios represent 31.4% and 28.5% lower modeled cost respectively.

The application distinguishes between `LIVE`, `RECORDED` and `TEMPLATE` responses. Recorded responses are genuine earlier model outputs; they are not silently presented as live inference.

See [DEMO_README.md](DEMO_README.md) for the demonstration instructions.

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/Johnlocke0347/Navitas.git
cd Navitas
```

### 2. Install dependencies

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
source .venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

### 3. Obtain the benchmark data

The raw GECAD dataset is not redistributed in this repository because its Zenodo record does not state a redistribution license.

Download the dataset from:

https://zenodo.org/records/4106746

Place the following files in `data/gecad/`:

```text
data/
└── gecad/
    ├── Input_JSON_Schedule_Optimization.json
    └── Output_JSON_Schedule_Optimization.json
```

The input JSON is required for the core solver and independent verification. The output JSON is used for comparison with the dataset authors' published solution.

See [DATA_SOURCES.md](DATA_SOURCES.md) for dataset provenance and licensing information.

### 4. Configure model access

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Add your API credentials to `.env`:

```env
BASETEN_API_KEY=your_key
FIREWORKS_API_KEY=your_key
```

Never commit your `.env` file.

### 5. Run the tests

```bash
python -m pytest tests -q
```

The project includes 19 tests. Model API credentials are not required for the test suite.

### 6. Launch Navitas

For live model interaction, configure your provider credentials and run:

```bash
python scripts/record_demo_answers.py
python app/server.py
```

Open:

http://127.0.0.1:8000

The application also supports recorded-answer replay for demonstrations where live inference is unavailable.

See [DEMO_README.md](DEMO_README.md) for replay settings and additional details.

## Reproduce the optimization experiment

With the GECAD input dataset downloaded and dependencies installed:

```bash
python engine/solve2.py pk 1060 120
```

Arguments:

- `pk`: illustrative Pakistan time-of-use tariff.
- `1060`: machine-capacity setting.
- `120`: solver time limit in seconds.

The solver writes its result and schedule JSON files to the repository root.

The experiment log and generated proof are documented in `results/`. To regenerate the proof from the experiment records:

```bash
python scripts/regen_proof.py
```

The proof-generation script requires the benchmark input data and recorded experiment artifacts.

## Assumptions and limitations

We believe transparent limitations are essential when evaluating optimization results.

- **Benchmark scope:** The evaluation uses a three-machine, six-day hang-tag textile production benchmark. It is not a live Pakistani dyeing or finishing mill.
- **Production quality:** The benchmark assumes that lower-energy machine/task modes produce equivalent output quality. This assumption has not yet been independently confirmed with the dataset authors.
- **Pakistan tariff:** The Pakistan time-of-use experiment uses illustrative rates of Rs 35.68/kWh peak and Rs 22.83/kWh off-peak. The modeled peak window of 18:30–22:30 and export price of Rs 8.13/kWh remain unverified assumptions.
- **Baseline:** The comparison baseline is the project's tariff-blind, fastest-mode, earliest-deadline-first schedule.
- **Optimality:** A feasible schedule is not necessarily a proven global optimum. The reported experiments include non-zero optimality gaps; the proof document provides the relevant solver details.
- **Deployment:** Results are benchmark results, not a claim of verified savings at a commercial factory.
- **Bill-image reading:** Vision has been tested on the synthetic sample tariff sheet in `app/static/sample_bill.png`, not on real electricity bills. Values the model reads are range-checked before they can affect any cost figure, and an unreadable image is reported as unreadable rather than guessed.
The current system is a decision-support and scheduling prototype. It does not directly control industrial machinery.
- **Production quality:** The dataset contains no product-quality measurements. The GECAD authors confirmed by email that no constraints exist beyond those in the dataset, but that does not show that alternative machine/task modes give equivalent output. Equivalence is assumed. If a plant approves fewer modes, savings fall toward the scheduling-only figure (about 5%).
  
## Commercial direction

Navitas is initially designed around multi-machine textile dyeing and finishing operations, where production can be scheduled across machines and time periods.

The intended business model is a per-factory setup combined with a share of independently verified savings.

The longer-term objective is to make industrial energy optimization accessible to manufacturers that cannot afford dedicated optimization and energy-management teams.

No factory pilot has been run yet; the first step is a pilot with a mill that can provide a week of schedule and meter data and a list of approved modes.
## Project structure

```text
Navitas/
├── app/                 # Agent, replay system and web application
├── engine/              # Scheduling, optimization and verification
├── results/             # Experiment logs and benchmark proof
├── scripts/             # Experiment and demonstration utilities
├── tests/               # Automated tests
├── logs/                # Model-call provenance records
├── DATA_SOURCES.md      # Dataset provenance and licensing
├── MODEL_PROVENANCE.md  # Meta model and inference details
├── DEMO_README.md       # Demo and replay instructions
├── llm.py               # Model routing and call logging
└── requirements.txt     # Python dependencies
```

## Built with

- [Meta Muse Models](https://ai.meta.com/)
- [Baseten](https://www.baseten.co/)
- [Fireworks AI](https://fireworks.ai/)
- [Google OR-Tools](https://developers.google.com/optimization)
- [GECAD production scheduling benchmark](https://zenodo.org/records/4106746)

Development involved AI coding assistance. Meta model usage within the application is routed and logged through the project's model-provenance layer.

---

**Navitas — Making factory energy decisions smarter, one production schedule at a time.**
