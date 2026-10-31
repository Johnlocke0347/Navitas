"""prove_savings.py - audit trail manifest, APPEND ONLY to results/runs.jsonl
One JSON line per run, failures included. Do not overwrite earlier results.
Covers: UTC, git hash/dirty, python/ortools, CPU, SHA256 input & engine/*.py,
params (cap, time limit, workers, seeds), tariff verified flags, baseline/opt costs,
violations, solver status/bound/wall, schedule SHA.
"""
import hashlib, json, pathlib, sys, os, datetime, subprocess, platform, multiprocessing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RUNS = RESULTS / "runs.jsonl"
ENGINE_DIR = ROOT / "engine"
DATA_JSON = ROOT / "data" / "gecad" / "Input_JSON_Schedule_Optimization.json"
# ensure engine is importable when running as scripts/prove_savings.py
import sys as _sys
if str(ROOT) not in _sys.path:
    _sys.path.insert(0, str(ROOT))

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def git_info():
    try:
        commit = subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        commit = "unknown"
    try:
        dirty = subprocess.check_output(["git","status","--porcelain"], cwd=ROOT).decode().strip() != ""
    except Exception:
        dirty = None
    return commit, dirty

def py_and_ortools():
    py = platform.python_version()
    try:
        import ortools
        ort = ortools.__version__ if hasattr(ortools, "__version__") else "unknown"
    except Exception as e:
        ort = f"error:{e}"
    return py, ort

def cpu_count():
    return multiprocessing.cpu_count()

def engine_shas():
    out={}
    for name in ["load.py","engine.py","solve2.py","run3.py"]:
        p=ENGINE_DIR / name
        if p.exists():
            out[name]=sha256_file(p)
        else:
            out[name]=None
    return out

def tariff_config(which: str):
    if which == "pk":
        return {
            "tariff_name": {"value":"pk","verified":True,"note":"Pakistan TOU illustrative"},
            "B2_peak_Rs_per_kWh": {"value":35.68,"verified":"news_only","note":"Dawn 1973828, NEPRA Feb 2026"},
            "B2_offpeak_Rs_per_kWh": {"value":22.83,"verified":"news_only","note":"Dawn 1973828"},
            "peak_window": {"value":"18:30-22:30 (138-186 per day, DAY=192)","verified":False,"note":"UNVERIFIED"},
            "export_price_Rs_per_kWh": {"value":8.13,"verified":False,"note":"UNVERIFIED"},
            "demand_fixed_Rs_per_kW": {"value":1250,"verified":"news_only","note":"Dawn report"},
        }
    else:
        return {
            "tariff_name": {"value":"mibel","verified":True,"note":"dataset energy_sources[0].price EUR/Wh"},
            "price_source": {"value":"P_MIBEL from Input JSON (EUR per Wh)","verified":True,"note":"dataset file"},
            "peak_window": {"value":"none","verified":True,"note":"MIBEL uses dataset prices, no TOU window"},
            "export_price": {"value":"N/A","verified":True,"note":"MIBEL scenario no PV"},
        }

def _check_clean_or_die():
    # audit requires clean tree BEFORE any run: no staged or unstaged changes to tracked files
    # (untracked files in results/ are allowed as they are outputs)
    try:
        # check staged
        subprocess.check_call(["git","diff","--cached","--quiet"], cwd=ROOT)
        # check unstaged
        subprocess.check_call(["git","diff","--quiet"], cwd=ROOT)
    except subprocess.CalledProcessError:
        print("ERROR: git tree is dirty — commit everything before running prove_savings.py (audit requires clean status).", file=sys.stderr)
        print("Run `git status` and commit or stash changes.", file=sys.stderr)
        print("Hint: `git diff` or `git diff --cached` shows changes to tracked files.", file=sys.stderr)
        sys.exit(2)
    # also check for untracked files that are not in results/ or ignored
    try:
        out = subprocess.check_output(["git","status","--porcelain","--untracked-files=all"], cwd=ROOT).decode()
        # filter out ignored and expected untracked in results/ (new runs) and navitas_real_data/ etc are now ignored
        bad = []
        for line in out.splitlines():
            if line.startswith("??"):
                path = line[3:].strip()
                # allow untracked in results/ as they are outputs (but they should be committed after run, not before)
                # For pre-run check, we want clean, so even untracked in results/ should be considered dirty before run
                # So if there are untracked files in results/ before run, that's dirty (should have been committed)
                bad.append(path)
        if bad:
            print(f"ERROR: untracked files present: {bad} — commit or gitignore before run.", file=sys.stderr)
            sys.exit(2)
    except Exception:
        pass

def run_one(cap: int, seed: int, which: str, timelimit: float = 120.0, workers: int = 1):
    _check_clean_or_die()
    utc = datetime.datetime.utcnow().isoformat() + "Z"
    git_commit, git_dirty = git_info()
    py_ver, ort_ver = py_and_ortools()
    cpu = cpu_count()
    input_sha = sha256_file(DATA_JSON) if DATA_JSON.exists() else None
    eng_shas = engine_shas()
    params = {"cap": cap, "time_limit": timelimit, "workers": workers, "seed_assign": seed, "seed_solver": 3, "tariff": which}
    tconf = tariff_config(which)
    manifest = {
        "utc": utc,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "python_version": py_ver,
        "ortools_version": ort_ver,
        "cpu_count": cpu,
        "input_sha256": input_sha,
        "engine_shas": eng_shas,
        "params": params,
        "tariff_config": tconf,
    }
    try:
        import importlib, random
        import engine.load as ld
        import engine.engine as eng
        import engine.solve2 as s2
        orig_assign = s2.assign
        def patched_assign(counts, seed_inner=seed):
            import collections, random as rndmod
            pools={}
            for t in set(x["task"] for x in ld.instances):
                pool=[]
                for (mm,tm) in ld.eligible(t):
                    pool += [(mm,tm)]*counts[(t,tm)]
                pools[t]=pool
            idx={t:0 for t in pools}
            rnd=rndmod.Random(seed_inner)
            for t in pools:
                rnd.shuffle(pools[t])
            out={}
            for i,ins in enumerate(ld.instances):
                t=ins["task"]
                out[i]=pools[t][idx[t]]
                idx[t]+=1
            return out
        s2.assign = patched_assign
        price, scale = (eng.P_MIBEL, 10**6) if which=="mibel" else (eng.pk_tariff(), 10**3)
        base = eng.baseline_edf()
        baseline_cost = eng.cost(base, price)
        baseline_kwh = float(eng.load_profile(base).sum()/1000)
        baseline_viol = len(eng.check(base))
        manifest["baseline"] = {"cost": baseline_cost, "kwh": baseline_kwh, "viol": baseline_viol}
        cnts = s2.stage1(cap)
        if cnts is None:
            manifest.update({"success": False, "error": "stage1 infeasible", "stage1_counts": None})
            raise RuntimeError("stage1 infeasible")
        manifest["stage1_counts"] = {f"{k[1]}": v for k,v in cnts.items() if v}
        assg = patched_assign(cnts, seed_inner=seed)
        sched_a = s2.edf_place(assg)
        if sched_a is None:
            manifest.update({"success": False, "error": f"EDF placement infeasible at cap {cap}"})
            raise RuntimeError(f"EDF placement infeasible at cap {cap}")
        modes_cost = eng.cost(sched_a, price)
        modes_kwh = float(eng.load_profile(sched_a).sum()/1000)
        modes_viol = len(eng.check(sched_a))
        manifest["modes_only"] = {"cost": modes_cost, "kwh": modes_kwh, "viol": modes_viol}
        sched_b, info = s2.stage2(assg, price, scale, sched_a, timelimit)
        if sched_b is None:
            manifest.update({"success": False, "error": "stage2 infeasible", "stage2_info": info})
            raise RuntimeError("stage2 infeasible")
        full_cost = eng.cost(sched_b, price)
        full_kwh = float(eng.load_profile(sched_b).sum()/1000)
        full_viol = len(eng.check(sched_b))
        makespan = max(s+len(eng.TM[tm]) for i,m_,tm,s in sched_b)
        manifest.update({
            "success": True,
            "stage2_info": info,
            "full": {"cost": full_cost, "kwh": full_kwh, "viol": full_viol, "makespan": makespan},
        })
        sched_path = RESULTS / f"sched2_{which}_{cap}_seed{seed}.json"
        res_path = RESULTS / f"res2_{which}_{cap}_seed{seed}.json"
        sched_list = [list(x) for x in sched_b]
        with open(sched_path, "w") as f:
            json.dump(sched_list, f)
        out_detail = {
            "which": which, "cap": cap, "seed": seed,
            "baseline": manifest["baseline"],
            "stage1_counts": manifest["stage1_counts"],
            "modes_only": manifest["modes_only"],
            "stage2_info": info,
            "full": manifest["full"],
        }
        with open(res_path, "w") as f:
            json.dump(out_detail, f, indent=1)
        sched_sha = sha256_file(sched_path)
        manifest["schedule_path"] = str(sched_path.relative_to(ROOT))
        manifest["schedule_sha256"] = sched_sha
        manifest["res_path"] = str(res_path.relative_to(ROOT))
    except Exception as e:
        if "success" not in manifest:
            manifest["success"] = False
            manifest["error"] = str(e)
        if "stage2_info" not in manifest:
            manifest["stage2_info"] = {"status":"FAILED","wall":None, "bound":None, "obj":None}
        if "schedule_path" not in manifest:
            manifest["schedule_path"] = None
            manifest["schedule_sha256"] = None
        import traceback as tb
        manifest["traceback"] = tb.format_exc()
        print(f"FAIL cap={cap} seed={seed} tariff={which} error={e}", file=sys.stderr)
    finally:
        try:
            s2.assign = orig_assign
        except Exception:
            pass
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(manifest) + "\n")
    print(json.dumps(manifest, indent=2))
    return manifest

def main():
    import argparse
    ap=argparse.ArgumentParser(description="prove savings audit - append to results/runs.jsonl")
    ap.add_argument("--cap", type=int, help="single cap to run")
    ap.add_argument("--seed", type=int, help="single seed to run")
    ap.add_argument("--tariff", type=str, choices=["pk","mibel"], help="single tariff")
    ap.add_argument("--timelimit", type=float, default=120.0, help="solver time limit")
    ap.add_argument("--all", action="store_true", help="run full matrix cap {1000,1060,1100} x seeds {7,11,23} x tariffs {pk,mibel}")
    args=ap.parse_args()
    if args.all or (args.cap is None and args.seed is None and args.tariff is None):
        caps=[1000,1060,1100]
        seeds=[7,11,23]
        tariffs=["pk","mibel"]
        print(f"Running full matrix: caps={caps} seeds={seeds} tariffs={tariffs} timelimit={args.timelimit}")
        for cap in caps:
            for seed in seeds:
                for which in tariffs:
                    print(f"\n=== RUN cap={cap} seed={seed} tariff={which} ===", flush=True)
                    run_one(cap, seed, which, timelimit=args.timelimit)
    else:
        cap=args.cap if args.cap is not None else 1060
        seed=args.seed if args.seed is not None else 7
        which=args.tariff if args.tariff is not None else "pk"
        print(f"Single run cap={cap} seed={seed} tariff={which}")
        run_one(cap, seed, which, timelimit=args.timelimit)

if __name__ == "__main__":
    main()


