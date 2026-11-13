"""Sensitivity check, not the planned metric: rescore the 100-call run with spaces removed from labels.

DeepSeek sometimes writes "Specific Disease" / "Disease Class" / "Composite Mention" (the guideline's prose
spelling) instead of the schema names. The planned scorer counts those as errors. This shows how much of
each arm's F1 and SD comes from that spelling alone. No API calls.
"""
import collections
import copy

import run_stability as rs


def main() -> None:
    _, documents, _ = rs.load_inputs()
    units = rs.load_units(rs.UNIT_DIRS["run"])
    spaced = collections.Counter()
    fixed = copy.deepcopy(units)
    for u in fixed:
        for a in u.get("annotations") or []:
            if " " in a["entity"]:
                spaced[(u["arm"], a["entity"])] += 1
                a["entity"] = a["entity"].replace(" ", "")
    print("spaced labels per arm:", dict(spaced))
    runaway = [(u["unit"], len(u["annotations"])) for u in units if len(u.get("annotations") or []) > 50]
    print("units with more than 50 predictions:", runaway)
    print("\n== rescored with spaces removed from labels ==")
    rs.score_run(fixed, documents)


if __name__ == "__main__":
    main()
