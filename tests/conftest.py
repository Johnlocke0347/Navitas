import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "app")):
    if p not in sys.path: sys.path.insert(0, p)
