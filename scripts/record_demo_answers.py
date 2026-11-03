"""Run ONCE with your real keys and a working connection. Makes live Muse Spark calls for the three example buttons,
checks vision on the sample sheet, and saves the real answers to app/replay/ so the demo still works later (labelled RECORDED).
Usage (repo root): python scripts/record_demo_answers.py"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app"))
import os; os.chdir(ROOT)
import server, agent
for key, p in server.PRESETS.items():
    t0 = __import__("time").time()
    out = server.ask(p["text"], key)
    print(f"[{key}] source={out['source']} model={out.get('model')} mode={out.get('mode','tools')} {round(__import__('time').time()-t0)}s")
    print("   ", (out["answer"] or "")[:300].replace("\n", " "))
    if out["source"] != "LIVE": print("    NOT LIVE -> live_error:", out.get("live_error"))
print("\nvision check on sample sheet:")
try:
    r = agent.extract_tariff((ROOT / "app/static/sample_bill.png").read_bytes())
    print("   fields:", r["fields"], "| accepted tariff:", r["tariff"], "| model:", r["model"])
except agent.AgentUnavailable as e:
    print("   vision call failed:", e)
print("\nrecordings saved:", server.replay.count(), "| now run: python app/server.py")
