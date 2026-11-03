"""Result cache so the demo is instant: key = canonical JSON of (constraints, tariff, cap)."""
import json, hashlib, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "app" / "cache"

def key(constraints, tariff=None, cap=1060):
    from engine.constrained import normalize, DEFAULT_TARIFF
    clean, _, _, errs = normalize(constraints)
    if errs: raise ValueError('; '.join(errs))
    t = {**DEFAULT_TARIFF, **(tariff or {})}
    canon = json.dumps({"c": sorted(json.dumps(c, sort_keys=True) for c in clean), "t": t, "cap": cap}, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]

def load(constraints, tariff=None, cap=1060):
    p = CACHE / f"{key(constraints, tariff, cap)}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def save(result, constraints, tariff=None, cap=1060, label=""):
    CACHE.mkdir(parents=True, exist_ok=True)
    result = dict(result); result["cache_label"] = label
    (CACHE / f"{key(constraints, tariff, cap)}.json").write_text(json.dumps(result), encoding="utf-8")
