import json, types
import pytest
import agent, replay
from engine import cache


def _resp(content=None, calls=None, model="fake-spark-for-tests"):
    msg = types.SimpleNamespace(content=content, tool_calls=calls)
    return types.SimpleNamespace(model=model, choices=[types.SimpleNamespace(message=msg)])


def _call(name, args, i="c1"):
    return types.SimpleNamespace(id=i, function=types.SimpleNamespace(name=name, arguments=json.dumps(args)))


needs_cache = pytest.mark.skipif(cache.load([]) is None, reason="run scripts/precompute_scenarios.py first")


@needs_cache
def test_tool_loop_runs_solver_tool_then_answers(monkeypatch):
    script = [_resp(calls=[_call("solve_schedule", {"constraints": []})]), _resp(content="Plan costs less; checker passed.")]
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: script.pop(0))
    out = agent.run_agent("show the plan", live_solve=False)
    assert out["answer"].startswith("Plan costs") and len(out["trace"]) == 1 and out["trace"][0]["result"]["ok"]
    assert out["trace"][0]["result"]["dataset_rule_violations"] == 0 and agent.SESSION.last is not None


def test_tool_returns_validation_error_for_bad_constraint():
    r = agent.tool_solve_schedule([{"type": "machine_down", "machine": "MAQ999", "day": 3}], None, live=False)
    assert not r["ok"] and "MAQ999" in r["error"]


def test_unreachable_model_raises(monkeypatch):
    def boom(*a, **k): raise RuntimeError("network down")
    monkeypatch.setattr(agent.llm, "chat", boom)
    with pytest.raises(agent.AgentUnavailable): agent.run_agent("hi")


def test_tariff_sanity_check():
    assert agent.tariff_from_fields({"peak_rate": 35.68, "offpeak_rate": 22.83, "peak_start": "18:30", "peak_end": "22:30"}) == {"peak": 35.68, "off": 22.83, "window": ["18:30", "22:30"]}
    assert agent.tariff_from_fields({"peak_rate": 2.0, "offpeak_rate": 22.83}) is None          # implausible
    assert agent.tariff_from_fields({"peak_rate": 20, "offpeak_rate": 30}) is None              # peak below off-peak
    assert agent.tariff_from_fields({"peak_rate": None, "offpeak_rate": 22}) is None


def test_extract_tariff_parses_json_reply(monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: _resp(content='```json\n{"peak_rate": 35.68, "offpeak_rate": 22.83, "peak_start": "18:30", "peak_end": "22:30", "fixed_charge_per_kw": 1250, "notes": "ok"}\n```'))
    r = agent.extract_tariff(b"\x89PNG fake", "image/png")
    assert r["tariff"]["peak"] == 35.68 and r["tariff"]["window"] == ["18:30", "22:30"]


def test_replay_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "DIR", tmp_path)
    replay.record("Machine down?", {"model": "m", "answer": "a", "trace": []})
    assert replay.lookup("  machine   DOWN? ")["answer"] == "a" and replay.lookup("other") is None


@needs_cache
def test_json_fallback_path(monkeypatch):
    script = [_resp(content='{"constraints": [{"type": "machine_down", "machine": "MAQ119", "day": 3}], "tariff": null}'), _resp(content="MAQ119 outage costs extra; checker passed.")]
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: script.pop(0))
    out = agent.run_agent_json("MAQ119 is down on day 3", live_solve=False)
    assert out["answer"].startswith("MAQ119") and out["trace"][0]["result"]["ok"] and out["mode"] == "json-fallback"
