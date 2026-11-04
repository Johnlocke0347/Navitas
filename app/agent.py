"""Navitas scheduling agent: Muse Spark (through llm.py, so every call is logged) decides which solver tools to call.
The model never does the scheduling maths: it translates plain English into constraints, calls the verified solver,
reads the checker verdict, and explains the numbers it was given."""
import json, os, re, time, base64
import llm
from engine import cache, constrained

MAX_TURNS = 5
CALL_TIMEOUT_S = float(os.getenv("NAVITAS_CALL_TIMEOUT", "45"))
SOLVE_S = float(os.getenv("NAVITAS_SOLVE_S", "60"))

SYSTEM = """You are Navitas, a scheduling copilot for a textile production line (3 machines: MAQ118, MAQ119, MAQ120; 6 plant days, 07:00-23:00).
Rules:
0. Users may say "machine 119" or "the third machine"; the ids are MAQ118, MAQ119, MAQ120. Day numbers are 1-6.
1. For ANY what-if or constraint request, call solve_schedule. Never invent costs, kWh or savings; quote only numbers returned by tools.
2. Translate the user's words into constraints: machine_down {machine, day 1-6} or avoid_window {task or "*", start "HH:MM", end "HH:MM", days "all" or list}. Tasks: Ironing, Anti-Shrinkage, Sublimation, Harden[0.5], Harden[1], Harden[1.5], Harden[2]. If a tool returns an error, fix the arguments and retry once.
3. Report: cost (Rs, illustrative tariff), saving vs the plain schedule under the same constraints, kWh, and whether the checker found violations. Say what the constraint cost compared with the unconstrained plan.
4. Be honest about limits: lower-energy modes are assumed equal in quality (unconfirmed); tariff peak window is unverified.
5. Answer in 4-6 short sentences, plain language."""

TOOLS = [
  {"type": "function", "function": {
    "name": "solve_schedule",
    "description": "Re-optimise the 6-day schedule under the given constraints with the exact CP-SAT solver and verify it with the independent checker. Returns costs, energy, savings and violation counts.",
    "parameters": {"type": "object", "properties": {
      "constraints": {"type": "array", "description": "list of constraints (may be empty)", "items": {"type": "object", "properties": {
        "type": {"type": "string", "enum": ["machine_down", "avoid_window"]},
        "machine": {"type": "string", "enum": ["MAQ118", "MAQ119", "MAQ120"]},
        "day": {"type": "integer", "minimum": 1, "maximum": 6},
        "task": {"type": "string"},
        "start": {"type": "string"}, "end": {"type": "string"},
        "days": {"description": "'all' or a list of day numbers"}}, "required": ["type"]}},
      "tariff": {"type": "object", "description": "optional: {peak, off (Rs/kWh), window: [start,end]} e.g. read from a bill"}},
      "required": ["constraints"]}}},
  {"type": "function", "function": {
    "name": "inspect_schedule",
    "description": "List what the last optimised schedule runs on one machine on one day (task, mode, start time).",
    "parameters": {"type": "object", "properties": {"machine": {"type": "string"}, "day": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["machine", "day"]}}},
]


class AgentUnavailable(Exception):
    pass


class Session:
    """single-user demo state"""
    def __init__(self):
        self.last = None          # full result dict of the last solve
        self.trace = []

SESSION = Session()


def digest(res):
    base_opt = cache.load([])  # unconstrained optimum for comparison
    o, b = res["optimized"], res["baseline"]
    if b is None:
        d = {"ok": True, "constraints_applied": res["constraints"], "tariff_rs_per_kwh": res["tariff"], "optimized_cost_rs": o["cost"], "optimized_kwh": o["kwh"],
             "optimized_peak_kw": o["peak_kw"], "baseline": "NOT FEASIBLE: " + (res.get("baseline_note") or ""), "dataset_rule_violations": res["violations_dataset"],
             "user_constraint_violations": res["violations_user"], "mode_choices": res["mode_counts"], "machine_capacity_periods": res["caps"], "solver_status": res["solver"].get("status")}
        if base_opt and res["constraints"]:
            d["extra_cost_vs_unconstrained_optimum_rs"] = round(o["cost"] - base_opt["optimized"]["cost"], 2)
        return d
    d = {"ok": True, "constraints_applied": res["constraints"], "tariff_rs_per_kwh": res["tariff"],
         "baseline_cost_rs": b["cost"], "optimized_cost_rs": o["cost"], "saving_pct_vs_baseline_same_constraints": res["saving_pct"],
         "baseline_kwh": b["kwh"], "optimized_kwh": o["kwh"], "optimized_peak_kw": o["peak_kw"],
         "machine_capacity_periods": res["caps"], "mode_choices": res["mode_counts"],
         "dataset_rule_violations": res["violations_dataset"], "user_constraint_violations": res["violations_user"],
         "solver_status": res["solver"].get("status")}
    if base_opt and res["constraints"]:
        d["extra_cost_vs_unconstrained_optimum_rs"] = round(o["cost"] - base_opt["optimized"]["cost"], 2)
        d["unconstrained_optimum_cost_rs"] = base_opt["optimized"]["cost"]
    return d


def tool_solve_schedule(constraints=None, tariff=None, live=True):
    if isinstance(constraints, str):
        try: constraints = json.loads(constraints)
        except Exception: return {"ok": False, "error": "constraints must be a JSON array"}
    if isinstance(tariff, str):
        try: tariff = json.loads(tariff)
        except Exception: tariff = None
    constraints = constraints or []
    _, _, _, errs = constrained.normalize(constraints)
    if errs: return {"ok": False, "error": "; ".join(errs)}          # never silently drop an invalid constraint
    res = cache.load(constraints, tariff)
    src = "cache"
    if res is None:
        if not live: return {"ok": False, "error": "This scenario was not pre-solved and live solving is switched off."}
        res = constrained.solve_with_constraints(constraints, tariff, time_limit=SOLVE_S, workers=max(1, os.cpu_count() or 1))
        src = "live solve"
        if res.get("ok"): cache.save(res, constraints, tariff, label="live")
    if not res.get("ok"): return {"ok": False, "error": res.get("error", "infeasible")}
    SESSION.last = res
    out = digest(res); out["result_source"] = src
    return out


def tool_inspect_schedule(machine, day):
    res = SESSION.last
    if not res: return {"ok": False, "error": "no schedule yet; call solve_schedule first"}
    rows = []
    for (i, m, tm, s) in sorted(res["schedule"]["optimized"], key=lambda x: x[3]):
        if m != machine: continue
        d0 = (day - 1) * 192
        if d0 <= s < d0 + 192:
            from engine.load import instances
            rows.append(f"{constrained.k_to_hhmm(s - d0)} {instances[i]['task']} ({tm})")
    return {"ok": True, "machine": machine, "day": day, "count": len(rows), "tasks": rows[:40]}


def run_tool(name, args, live=True):
    try:
        if name == "solve_schedule": return tool_solve_schedule(args.get("constraints"), args.get("tariff"), live)
        if name == "inspect_schedule": return tool_inspect_schedule(args.get("machine"), int(args.get("day", 1)))
        return {"ok": False, "error": f"unknown tool {name}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def run_agent(user_text, extra_context=None, live_solve=True):
    """Returns dict(answer, trace, model, source='live'). Raises AgentUnavailable if the model cannot be reached."""
    messages = [{"role": "system", "content": SYSTEM}]
    if extra_context: messages.append({"role": "system", "content": extra_context})
    messages.append({"role": "user", "content": user_text})
    trace, model = [], None
    for turn in range(MAX_TURNS):
        try:
            resp = llm.chat(messages, role="agent", tools=TOOLS, tool_choice="auto", max_tokens=1500, temperature=0.2, timeout=CALL_TIMEOUT_S)
        except Exception as e:
            raise AgentUnavailable(f"{type(e).__name__}: {str(e)[:160]}")
        model = getattr(resp, "model", None) or model
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            return {"answer": (msg.content or "").strip(), "trace": trace, "model": model, "source": "live", "turns": turn + 1}
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]})
        for c in calls:
            try: args = json.loads(c.function.arguments or "{}")
            except Exception: args = {}
            result = run_tool(c.function.name, args, live_solve)
            trace.append({"tool": c.function.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result)})
    return {"answer": "I ran out of steps before finishing; the last tool results are shown above.", "trace": trace, "model": model, "source": "live", "turns": MAX_TURNS}


JSON_SYSTEM = ('You turn a user request about the textile line schedule into constraints. Reply with ONE JSON object only: {"constraints": [...], "tariff": null}. '
               'Constraint forms: {"type":"machine_down","machine":"MAQ118|MAQ119|MAQ120","day":1-6} and {"type":"avoid_window","task":"<task or *>","start":"HH:MM","end":"HH:MM","days":"all" or [1..6]}. '
               'Users may say "machine 119"; ids are MAQ118, MAQ119, MAQ120. Tasks: Ironing, Anti-Shrinkage, Sublimation, Harden[0.5], Harden[1], Harden[1.5], Harden[2]. Plant day is 07:00-23:00. If the request has no constraint, use an empty list.')


def run_agent_json(user_text, extra_context=None, live_solve=True):
    """Fallback when native tool calling is unavailable: Spark returns constraint JSON, the solver runs, Spark explains the returned numbers."""
    msgs = [{"role": "system", "content": JSON_SYSTEM}] + ([{"role": "system", "content": extra_context}] if extra_context else []) + [{"role": "user", "content": user_text}]
    try:
        r1 = llm.chat(msgs, role="agent", max_tokens=700, temperature=0.0, timeout=CALL_TIMEOUT_S)
    except Exception as e:
        raise AgentUnavailable(f"{type(e).__name__}: {str(e)[:160]}")
    raw = (r1.choices[0].message.content or "").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    try: spec = json.loads(m.group(0)) if m else {}
    except Exception: spec = {}
    args = {"constraints": spec.get("constraints") or [], "tariff": spec.get("tariff")}
    result = run_tool("solve_schedule", args, live_solve)
    trace = [{"tool": "solve_schedule", "args": args, "result": result}]
    msgs2 = [{"role": "system", "content": SYSTEM.split("Rules:")[0] + "Explain the solver result below in 4-6 short plain sentences. Quote only numbers present in it; mention the checker verdict and any assumptions."},
             {"role": "user", "content": f"Request: {user_text}\nSolver result: {json.dumps(result)}"}]
    try:
        r2 = llm.chat(msgs2, role="agent", max_tokens=900, temperature=0.2, timeout=CALL_TIMEOUT_S)
    except Exception as e:
        raise AgentUnavailable(f"{type(e).__name__}: {str(e)[:160]}")
    return {"answer": (r2.choices[0].message.content or "").strip(), "trace": trace, "model": getattr(r2, "model", None), "source": "live", "turns": 2, "mode": "json-fallback"}


# ---------- vision: read a tariff off a bill photo ----------
BILL_PROMPT = ("This is an electricity bill or tariff sheet. Extract ONLY what is printed on it. Reply with one JSON object and nothing else: "
               '{"peak_rate": number Rs/kWh or null, "offpeak_rate": number Rs/kWh or null, "peak_start": "HH:MM" or null, "peak_end": "HH:MM" or null, '
               '"fixed_charge_per_kw": number or null, "notes": short string}. Use null for anything you cannot read. Do not guess.')


def extract_tariff(image_bytes, mime="image/png"):
    b64 = base64.b64encode(image_bytes).decode()
    msgs = [{"role": "user", "content": [{"type": "text", "text": BILL_PROMPT}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]}]
    try:
        resp = llm.chat(msgs, role="agent", max_tokens=4000, temperature=0.0, timeout=CALL_TIMEOUT_S * 2)
    except Exception as e:
        raise AgentUnavailable(f"{type(e).__name__}: {str(e)[:160]}")
    raw = (resp.choices[0].message.content or "").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    try: data = json.loads(m.group(0)) if m else {}
    except Exception: data = {}
    return {"raw": raw[:600], "fields": data, "model": getattr(resp, "model", None), "tariff": tariff_from_fields(data)}


def tariff_from_fields(f):
    """sanity-check what the model read before it is allowed to drive any cost number"""
    try:
        peak, off = float(f.get("peak_rate")), float(f.get("offpeak_rate"))
    except (TypeError, ValueError):
        return None
    if not (5 <= off <= 150 and 5 <= peak <= 200 and peak >= off): return None
    t = {"peak": peak, "off": off}
    ps, pe = f.get("peak_start"), f.get("peak_end")
    if isinstance(ps, str) and isinstance(pe, str):
        try:
            if constrained.hhmm_to_k(pe) > constrained.hhmm_to_k(ps): t["window"] = [ps, pe]
        except Exception: pass
    return t
