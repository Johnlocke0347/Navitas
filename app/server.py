"""Navitas demo server (stdlib only). Run from the repo root:  python app/server.py   then open http://127.0.0.1:8000"""
import json, sys, pathlib, os, base64, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app")); os.chdir(ROOT)   # llm.py logs to ./logs/calls.jsonl
import numpy as np
from engine import cache, constrained
from engine.load import instances, TM
import agent, replay

STATIC = ROOT / "app" / "static"
PRESETS = {
    "base": {"text": "Show me the best plan with no problems.", "constraints": []},
    "maq119": {"text": "Machine 119 is down for all of day 3.", "constraints": [{"type": "machine_down", "machine": "MAQ119", "day": 3}]},
    "peak": {"text": "Don't run anything between 18:30 and 22:30, on any day.", "constraints": [{"type": "avoid_window", "task": "*", "start": "18:30", "end": "22:30", "days": "all"}]},
}
LIVE_ENABLED = os.getenv("NAVITAS_LIVE", "1") != "0"


def enrich(res):
    """add per-task energy + gantt rows for the UI"""
    out = {k: v for k, v in res.items() if k != "schedule"}
    by_task = {}
    for kind in ("baseline", "optimized"):
        d = {}
        for (i, m, tm, s) in res["schedule"][kind]:
            d[instances[i]["task"]] = d.get(instances[i]["task"], 0) + sum(TM[tm]) / 1000
        by_task[kind] = {k: round(v, 1) for k, v in sorted(d.items())}
    out["by_task_kwh"] = by_task
    out["gantt"] = {kind: [[m, instances[i]["task"], tm, s, len(TM[tm])] for (i, m, tm, s) in res["schedule"][kind]] for kind in ("baseline", "optimized")}
    return out


def provenance():
    p = ROOT / "logs" / "calls.jsonl"; n = ok = 0; last = None; hosts = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try: r = json.loads(line)
            except Exception: continue
            n += 1; ok += 1 if r.get("ok", True) else 0
            hosts[r.get("host")] = hosts.get(r.get("host"), 0) + 1
            if r.get("ok", True): last = r
    return {"calls_logged": n, "calls_ok": ok, "hosts": hosts, "last_ok": ({k: last.get(k) for k in ("ts", "host", "returned_model", "latency_s")} if last else None),
            "replay_recordings": replay.count()}


def ask(text, preset=None, extra_context=None):
    """live Muse Spark -> else recorded real answer -> else deterministic template (clearly labelled)."""
    live_err = None
    if LIVE_ENABLED:
        for fn in (agent.run_agent, agent.run_agent_json):
            try:
                run = fn(text, extra_context=extra_context)
                if run["answer"]:
                    replay.record(text, run)
                    return {**run, "source": "LIVE"}
            except agent.AgentUnavailable as e:
                live_err = str(e)
                if any(k in live_err for k in ("Timeout", "Connection", "No configured provider")): break   # network/keys problem: do not wait twice
    rec = replay.lookup(text)
    if rec:
        # re-run the cached tools so the screen state matches the recorded answer
        for t in rec["trace"]:
            if t["tool"] == "solve_schedule": agent.run_tool("solve_schedule", t["args"], live=False)
        return {"answer": rec["answer"], "trace": rec["trace"], "model": rec["model"], "source": "RECORDED", "recorded_at": rec["recorded_at"], "live_error": live_err}
    if preset in PRESETS:
        r = agent.tool_solve_schedule(PRESETS[preset]["constraints"], None, live=False)
        if r.get("ok"):
            cmp_ = (f"instead of Rs{r['baseline_cost_rs']:,.0f} for the usual schedule ({r['saving_pct_vs_baseline_same_constraints']:.0f}% lower)"
                    if 'baseline_cost_rs' in r else "(the usual fastest-setting schedule cannot meet the deadline here)")
            ok = r['dataset_rule_violations'] == 0 and r['user_constraint_violations'] == 0
            ans = (f"The new plan costs Rs{r['optimized_cost_rs']:,.0f} {cmp_} and uses {r['optimized_kwh']:,.0f} kWh. "
                   + ("It passed every check." if ok else "It FAILED a check."))
            return {"answer": ans, "trace": [{"tool": "solve_schedule", "args": {"constraints": PRESETS[preset]["constraints"]}, "result": r}], "model": None, "source": "TEMPLATE", "live_error": live_err}
    return {"answer": "The model is unreachable and this question was not recorded. Try one of the example buttons.", "trace": [], "model": None, "source": "UNAVAILABLE", "live_error": live_err}


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a): pass

    def do_GET(self):
        if self.path in ("/", "/index.html"): return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/sample_bill.png" and (STATIC / "sample_bill.png").exists(): return self._send(200, (STATIC / "sample_bill.png").read_bytes(), "image/png")
        if self.path == "/api/state":
            res = cache.load([])
            if not res: return self._send(200, {"ok": False, "error": "Run: python scripts/precompute_scenarios.py"})
            agent.SESSION.last = res
            return self._send(200, {"ok": True, "result": enrich(res), "presets": {k: v["text"] for k, v in PRESETS.items()}, "provenance": provenance(), "live": LIVE_ENABLED})
        if self.path == "/api/status": return self._send(200, provenance())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/ask":
                text = body.get("text", "").strip(); preset = body.get("preset")
                if preset in PRESETS and not text: text = PRESETS[preset]["text"]
                out = ask(text, preset, body.get("context"))
                out["result"] = enrich(agent.SESSION.last) if agent.SESSION.last else None
                out["provenance"] = provenance()
                return self._send(200, out)
            if self.path == "/api/bill":
                img = base64.b64decode(body["image_b64"])
                try: r = agent.extract_tariff(img, body.get("mime", "image/png"))
                except agent.AgentUnavailable as e: return self._send(200, {"ok": False, "error": str(e)})
                return self._send(200, {"ok": True, **r, "provenance": provenance()})
        except Exception as e:
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Navitas demo on http://127.0.0.1:{port}  (live model: {'on' if LIVE_ENABLED else 'off'})")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
