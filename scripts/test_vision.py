"""Vision check. Put this file in scripts/ and run from the repo root:
    python scripts/test_vision.py                 (tests app/static/sample_bill.png)
    python scripts/test_vision.py path\\to\\other_photo.jpg   (optional: test any other bill photo)

Makes ONE real Muse Spark call with the image, prints what the model read, and whether the app would accept it.
"""
import sys, os, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app")); os.chdir(ROOT)
import agent

path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "app/static/sample_bill.png"
mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
print("image:", path, f"({path.stat().st_size} bytes)")

try:
    r = agent.extract_tariff(path.read_bytes(), mime)
except agent.AgentUnavailable as e:
    print("\nFAIL: vision call did not return ->", e)
    sys.exit(1)

print("\nmodel returned by provider:", r["model"])
print("raw reply:", r["raw"])
print("parsed fields:", json.dumps(r["fields"]))
print("accepted tariff (what the app would use):", r["tariff"])

if path.name == "sample_bill.png":
    want = {"peak": 35.68, "off": 22.83, "window": ["18:30", "22:30"]}
    print("\nexpected for the sample sheet:", want)
    print("RESULT:", "PASS" if r["tariff"] == want else "MISMATCH (see raw reply above)")

# provenance: the last row of logs/calls.jsonl should be this call; an image adds prompt tokens
last = json.loads(pathlib.Path("logs/calls.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
u = last.get("usage") or {}
print("\nlast logged call: provider=%s ok=%s latency=%ss prompt_tokens=%s image_tokens=%s" % (
    last.get("provider"), last.get("ok"), last.get("latency_s"), u.get("prompt_tokens"),
    (u.get("prompt_tokens_details") or {}).get("image_tokens")))
