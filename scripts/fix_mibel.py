"""Re-run 9 MIBEL configs with 150s, retry 240s on UNKNOWN, append only."""
import subprocess, sys, json, pathlib, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs.jsonl"

caps = [1000,1060,1100]
seeds = [7,11,23]

def last_run_status(cap, seed, tariff, timelimit):
    # read last line for this cap/seed/tariff/timelimit
    if not RUNS.exists():
        return None
    for line in reversed(open(RUNS, encoding="utf-8").read().splitlines()):
        if not line.strip():
            continue
        j=json.loads(line)
        if j['params']['cap']==cap and j['params']['seed_assign']==seed and j['params']['tariff']==tariff and j['params']['time_limit']==timelimit:
            return j
    return None

def run_one(cap, seed, tariff, timelimit):
    print(f"\n=== RE-RUN cap={cap} seed={seed} tariff={tariff} timelimit={timelimit} ===", flush=True)
    subprocess.run([sys.executable, "scripts/prove_savings.py", "--cap", str(cap), "--seed", str(seed), "--tariff", tariff, "--timelimit", str(timelimit)], cwd=ROOT, check=False)

success_count=0
for cap in caps:
    for seed in seeds:
        tariff="mibel"
        # first attempt 150
        run_one(cap, seed, tariff, 150)
        # check last run
        j=last_run_status(cap, seed, tariff, 150)
        if j:
            status=j.get('stage2_info',{}).get('status')
            print(f" -> cap={cap} seed={seed} mibel 150s status={status} success={j.get('success')}")
            if j.get('success'):
                success_count+=1
            # if UNKNOWN, retry 240
            if status=="UNKNOWN" or not j.get('success'):
                print(f"    UNKNOWN -> retrying with 240s")
                run_one(cap, seed, tariff, 240)
                j2=last_run_status(cap, seed, tariff, 240)
                if j2:
                    print(f"    retry 240s status={j2.get('stage2_info',{}).get('status')} success={j2.get('success')}")
                    if j2.get('success'):
                        success_count+=1
                else:
                    print("    retry did not log?")
        else:
            print(f"no manifest found for cap={cap} seed={seed} mibel 150")

print(f"\nMIBEL re-run complete: {success_count} successes out of 9 initial + retries (see runs.jsonl, append only)")
# also show total runs now
if RUNS.exists():
    total=len([l for l in open(RUNS) if l.strip()])
    print(f"Total runs in runs.jsonl now: {total} (original 18 + {total-18} new)")
