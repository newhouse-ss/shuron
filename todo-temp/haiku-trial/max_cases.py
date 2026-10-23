"""Followed cases over every finished reply, per arm (the report counts complete repeats only). Offline."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402


def main() -> None:
    _, documents, entities = rs.load_inputs()
    units = [u for u in rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities) if u["arm"] == "B_on"]
    units += rs.fix_labels(rs.load_units(rh.UNITS), entities)
    for name, (doc, start, end) in rs.CASES.items():
        gold = next(a.entity for a in documents[doc].gold_annotations if (a.start, a.end) == (start, end))
        cells = []
        for arm in ["B_on", *rh.ARMS]:
            states = [rs.case_state(u["annotations"], start, end) for u in units
                      if u["arm"] == arm and u["doc"] == doc and u["status"] == "ok"]
            cells.append(f"{arm} {dict(Counter(states))} of {len(states)}")
        print(f"{name} (gold {gold}): " + "; ".join(cells))


if __name__ == "__main__":
    main()
