"""DeepSeek stability-test spend at the price that applied to each call, from the saved units.

Offline. report_run_output.txt prints every arm twice, all off-peak and all peak; each unit also records whether it
started in the peak window ("peak"), so this sums each call at its own price (run_stability.cost_jpy, same JPY rate
as the Haiku scripts). Covers the main run and the top-up (units/) and the probe (units_probe/).
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_stability as rs  # noqa: E402

grand = 0.0
for folder in ("units", "units_probe"):
    arms: dict[str, list] = {}
    for p in sorted((HERE / folder).glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        if u.get("status") == "ok" and u.get("usage"):
            arms.setdefault(u["arm"], []).append(u)
    for arm, units in sorted(arms.items()):
        cost = [rs.cost_jpy(u["usage"], u["peak"]) for u in units]
        grand += sum(cost)
        print(f"{folder} {arm}: {len(units)} calls, {sum(u['peak'] for u in units)} at peak; JPY {sum(cost):.2f}, "
              f"per call mean {statistics.mean(cost):.3f}; seconds per call mean "
              f"{statistics.mean(u['seconds'] for u in units):.0f}")
print(f"total JPY {grand:.2f} = USD {grand / rs.JPY_PER_USD:.2f}")
