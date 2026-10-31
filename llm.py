"""Navitas model router. Every model call in the project goes through here.

Roles -> ordered provider chains (first available wins, errors fall through):
  agent      Baseten Spark Open -> Fireworks Spark Open     (tool calling, reasoning, vision)
  extractor  Fireworks Glimmer  -> Baseten Spark Open       (cheap constraint parsing, summaries)
  private    Modal Glimmer      -> Fireworks Glimmer        (on-site / private deployment variant)

Safety: only Meta model IDs are allowed. Anything else is blocked before the request is sent.
Every attempt (success or failure) is appended to logs/calls.jsonl as a provenance record.
"""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import openai
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

ALLOWED_PREFIXES = ("meta-models/", "meta/muse-", "accounts/fireworks/models/muse-")
LOG_PATH = Path("logs/calls.jsonl")

ROLES = {
    "agent": ["baseten", "fireworks_spark"],
    "extractor": ["fireworks_glimmer", "baseten"],
    "private": ["modal_glimmer", "fireworks_glimmer"],
}


def _env(*names, default=None):
    for n in names:
        v = os.getenv(n)
        if v and v.strip():
            return v.strip()
    return default


def providers():
    """Read config at call time so .env edits take effect without code changes."""
    fw_base = _env("FIREWORKS_BASE_URL", default="https://api.fireworks.ai/inference/v1")
    return {
        "baseten": {
            "base_url": _env("BASETEN_BASE_URL", "LLM_BASE_URL", default="https://inference.baseten.co/v1"),
            "model": _env("BASETEN_MODEL", "LLM_MODEL", default="meta-models/muse-spark-open-1026"),
            "api_key": _env("BASETEN_API_KEY", "LLM_API_KEY"),
        },
        "fireworks_spark": {
            "base_url": fw_base,
            "model": _env("FIREWORKS_SPARK_MODEL", default="accounts/fireworks/models/muse-spark-open"),
            "api_key": _env("FIREWORKS_API_KEY"),
        },
        "fireworks_glimmer": {
            "base_url": fw_base,
            "model": _env("FIREWORKS_GLIMMER_MODEL", default="accounts/fireworks/models/muse-glimmer-30b"),
            "api_key": _env("FIREWORKS_API_KEY"),
        },
        "modal_glimmer": {
            # Only available after you deploy Glimmer on Modal and set MODAL_BASE_URL.
            "base_url": _env("MODAL_BASE_URL"),
            "model": _env("MODAL_MODEL", default="meta-models/Muse-Glimmer-30B"),
            "api_key": _env("MODAL_API_KEY", default="not-needed"),
        },
    }


def is_available(name):
    cfg = providers()[name]
    return bool(cfg["base_url"] and cfg["api_key"])


def check_model(model):
    if not model.startswith(ALLOWED_PREFIXES):
        raise ValueError(f"Blocked non-Meta model id: {model!r}")


def _client_for(cfg):
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=180, max_retries=1)


def _log(record):
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def ask(provider, messages, role=None, **kwargs):
    """Call ONE specific provider (no fallback). Raises on failure."""
    cfg = providers()[provider]
    check_model(cfg["model"])
    if not is_available(provider):
        raise RuntimeError(f"Provider {provider!r} is not configured in .env")
    start = time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "role": role,
        "provider": provider,
        "host": urlparse(cfg["base_url"]).netloc,
        "requested_model": cfg["model"],
    }
    try:
        resp = _client_for(cfg).chat.completions.create(model=cfg["model"], messages=messages, **kwargs)
    except Exception as e:
        record.update(ok=False, error=f"{type(e).__name__}: {str(e)[:200]}",
                      latency_s=round(time.time() - start, 2))
        _log(record)
        raise
    usage = resp.usage.model_dump() if getattr(resp, "usage", None) else {}
    record.update(ok=True, returned_model=getattr(resp, "model", None),
                  latency_s=round(time.time() - start, 2), usage=usage)
    _log(record)
    return resp


def chat(messages, role="agent", **kwargs):
    """Call the first working provider for a role; fall through on API errors."""
    last_err = None
    tried = 0
    for name in ROLES[role]:
        if not is_available(name):
            continue
        tried += 1
        try:
            return ask(name, messages, role=role, **kwargs)
        except ValueError:
            raise  # blocked non-Meta model: never fall through silently
        except openai.OpenAIError as e:
            last_err = e
            print(f"[llm] {name} failed for role '{role}': {type(e).__name__}. Trying next provider.")
    if tried == 0:
        raise RuntimeError(f"No configured provider for role {role!r}. Check your .env keys.")
    raise last_err
