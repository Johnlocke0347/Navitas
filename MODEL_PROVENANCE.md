# Model Provenance

- **Models:** Muse Spark Open (Meta open-weights) on two providers
  - Baseten: `meta-models/muse-spark-open-1026` (primary)
  - Fireworks: `accounts/fireworks/models/muse-spark-open` (fallback)
- **Hosts:**
  - Baseten Model APIs — `https://inference.baseten.co/v1` (hackathon inference partner)
  - Fireworks AI — `https://api.fireworks.ai/inference/v1` (backup inference)
- **License:** Muse Model License (attribution required)
- **Access routes:**
  - Baseten via hackathon credits
  - Fireworks via separate API key
- **Why not the Meta Model API:** first-party credits were not accessible from the origin region
- **Routing:** `llm.py` routes by role with fallback chains:
  - `agent` → Baseten Spark → Fireworks Spark
  - `extractor` → Fireworks Spark → Baseten Spark
  - `private` → Modal Glimmer → Fireworks Glimmer (Modal not yet deployed)
- **Safety:** only Meta model IDs are allowed (`meta-models/`, `meta/muse-`, `accounts/fireworks/models/muse-`)
- **Evidence:** every model call is logged in `logs/calls.jsonl` (host, provider, requested model, returned model, latency, tokens)
- **Reproduce:** `python verify_model.py`

## Model availability (verified)
| Provider | Model | Status | Latency |
|----------|-------|--------|---------|
| Baseten | `meta-models/muse-spark-open-1026` | ✅ Working | ~1.5s |
| Fireworks | `accounts/fireworks/models/muse-spark-open` | ✅ Working | ~2.5s |
| Fireworks Glimmer | `accounts/fireworks/models/muse-glimmer-30b` | ❌ Not deployed (404) | — |
| Modal | `meta-models/Muse-Glimmer-30B` | ⚠️ Not configured | — |

## Non-Meta components (no other LLMs are used)
- (fill in as you add them, e.g. OR-Tools, scikit-learn/XGBoost)

## Log of changes
- 2026-10-27: project started, Baseten key configured.
- 2026-10-27: Fireworks API key added as backup provider for Spark Open.
- 2026-10-27: llm.py upgraded to multi-provider router with role-based fallback.
