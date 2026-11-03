"""Record/replay of REAL Muse Spark answers so the demo survives a bad connection or expired credits.
A recording is only ever written from a live call (agent.run_agent success); the UI labels replays as RECORDED."""
import json, hashlib, pathlib, time, re
DIR = pathlib.Path(__file__).resolve().parent / "replay"

def _key(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text.strip().lower()).encode()).hexdigest()[:16]

def lookup(text):
    p = DIR / f"{_key(text)}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def record(text, run):
    DIR.mkdir(exist_ok=True)
    rec = {"user_text": text, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": run.get("model"),
           "answer": run["answer"], "trace": run["trace"]}
    (DIR / f"{_key(text)}.json").write_text(json.dumps(rec), encoding="utf-8")

def count():
    return len(list(DIR.glob("*.json"))) if DIR.exists() else 0
