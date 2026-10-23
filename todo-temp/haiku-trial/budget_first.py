"""What fits in a USD 2.15 balance first: one top-1 loop, one top-4 loop, and E1 runs. No API calls.

Same inputs as cost_default10.py: Haiku xhigh price per annotation call (measured, Batch), calls per round from
the code, analysis calls priced like annotation calls (estimate) or at a 100,000-token prompt plus the
64,000-token output cap (bound). Yen at the runner's rate.
"""
import contextlib
import io
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

BALANCE_USD = 2.15
ANALYSIS = {"top-1": 3, "top-4": 9}


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == "H_xhigh"]
    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    bound = rh.cost_jpy({"input_tokens": rh.PROMPT_CARD_LIMIT, "output_tokens": rh.MAX_TOKENS}, True)
    balance = BALANCE_USD * rs.JPY_PER_USD
    print(f"balance USD {BALANCE_USD} = JPY {balance:.0f}; annotation call JPY {price:.3f} = USD "
          f"{price / rs.JPY_PER_USD:.4f}; analysis call bound JPY {bound:.2f}")
    print(f"E1 run (100 valid100 calls): JPY {100 * price:.0f} = USD {100 * price / rs.JPY_PER_USD:.2f}")
    for method, per_round in ANALYSIS.items():
        for rounds in (1, 2, 3, 20):
            a, n = rounds * per_round, 10 + rounds * 10 + 100
            est, top = (a + n) * price, n * price + a * bound
            print(f"one {method} loop, {rounds} rounds: {a + n} calls, estimate JPY {est:.0f} (USD "
                  f"{est / rs.JPY_PER_USD:.2f}), at most JPY {top:.0f} (USD {top / rs.JPY_PER_USD:.2f})")
    for rounds in (1, 3):
        est = sum((rounds * k + 10 + rounds * 10 + 100) * price for k in ANALYSIS.values())
        top = sum((10 + rounds * 10 + 100) * price + rounds * k * bound for k in ANALYSIS.values())
        for label, loops in (("estimate", est), ("at most", top)):
            runs = int((balance - loops) // (100 * price))
            print(f"both loops at {rounds} rounds, {label} JPY {loops:.0f}: room left for {runs} E1 runs "
                  f"(total JPY {loops + runs * 100 * price:.0f} = USD {(loops + runs * 100 * price) / rs.JPY_PER_USD:.2f})")


if __name__ == "__main__":
    main()
