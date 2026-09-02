"""Compare moderation runs: how fast they converge, what they break, what they copy.

Four things per run, all read from the round snapshots and the prompts that were
actually sent, so no re-annotation is needed:

  rounds, F1      where the loop stopped and why.

  fixed / broke   gold mentions gained and lost at each round, and how many of
                  the losses had been annotated correctly in an earlier round.
                  Every loss observed so far has been of that kind, so the two
                  numbers usually coincide; they are printed separately because
                  the day they diverge is worth seeing.

  copied A        of the lines a round adds to the guideline, how many quote,
                  verbatim, one of the mentions listed in the DO NOT BREAK block.
                  Denominator is added lines, so it compares across conditions
                  that supply no protected examples at all.

  copied B        of the mentions listed in that block, how many end up written
                  into the guideline. Denominator is the block, so it says what
                  share of the material meant only to prevent regression became
                  rules instead. Undefined when the block is empty.

A and B point in opposite directions and neither has a tunable threshold, which
is why they replace the n-gram overlap measure used earlier: that one moved
between 15% and 73% on the same round depending on how long a shared sequence
had to be before it counted.

    python reproduction/compare_topk.py outputs/<run> [outputs/<run> ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BLOCK_START = "DO NOT BREAK THESE EXAMPLES"
BLOCK_END = "**INSTRUCTIONS:**"
LISTED = re.compile(r'^- \w+ \[\d+, \d+\] "(.+)"$', re.M)


def mention_sets(diagnostics):
    """Gold mentions, the ones matched exactly, and predictions with no gold."""
    gold, matched, spurious = set(), set(), set()
    for f in diagnostics["files"]:
        doc = f["filename"]
        g = {(doc, d["start"], d["end"], d["label"]) for d in f["reference_denotations"]}
        p = {(doc, d["start"], d["end"], d["label"]) for d in f["study_denotations"]}
        gold |= g
        matched |= g & p
        spurious |= p - g
    return gold, matched, spurious


def protected_strings(run: Path, iteration: int) -> set[str]:
    path = run / f"rounds/iteration_{iteration:02d}/refine_guidelines.txt"
    if not path.exists():
        return set()
    prompt = path.read_text(encoding="utf-8")
    start = prompt.find(BLOCK_START)
    if start < 0:
        return set()
    block = prompt[start:prompt.find(BLOCK_END)]
    return {m for m in LISTED.findall(block) if len(m) >= 4}


def added_lines(snapshot) -> list[str]:
    before = {line.strip() for line in snapshot["guidelines_before"].splitlines() if line.strip()}
    text = snapshot.get("guidelines_candidate") or snapshot["guidelines_after"]
    return [line for line in (x.strip() for x in text.splitlines()) if line and line not in before]


def report(run: Path) -> None:
    snapshots = [json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(run.glob("rounds/iteration_*/snapshot.json"))]
    if not snapshots:
        print(f"=== {run.name}: no rounds yet")
        return
    status = json.loads((run / "status.json").read_text(encoding="utf-8"))

    states = [mention_sets(snapshots[0]["diagnostics_before"])]
    states += [mention_sets(s["diagnostics_after"]) for s in snapshots]
    gold_total = len(states[0][0])

    print(f"=== {run.name}")
    print(f"    {status.get('status')} after {len(snapshots)} round(s), "
          f"{status.get('stop_reason', '-')}, F1 "
          f"{status.get('initial_f1', 0):.4f} -> {status.get('final_f1', 0):.4f}")
    print(f"    correct mentions of {gold_total}: " +
          " -> ".join(str(len(m)) for _, m, _ in states))

    ever = set(states[0][1])
    totals = [0, 0, 0, 0]
    print(f"    {'round':<7}{'fixed':>7}{'broke':>7}{'was correct':>13}"
          f"{'copied A':>12}{'copied B':>12}")
    for index, snapshot in enumerate(snapshots):
        _, before_matched, _ = states[index]
        _, after_matched, _ = states[index + 1]
        broke = before_matched - after_matched
        regressed = broke & ever
        ever |= after_matched

        lines = added_lines(snapshot)
        strings = protected_strings(run, snapshot["iteration"])
        text = snapshot.get("guidelines_candidate") or snapshot["guidelines_after"]
        quoting = [l for l in lines if any(m in l for m in strings)]
        written = {m for m in strings if m in text}

        a = f"{len(quoting)}/{len(lines)}" if lines else "-"
        b = f"{len(written)}/{len(strings)}" if strings else "-"
        print(f"    {snapshot['iteration']:<7}{len(after_matched - before_matched):>7}"
              f"{len(broke):>7}{len(regressed):>13}{a:>12}{b:>12}")
        totals[0] += len(after_matched - before_matched)
        totals[1] += len(broke)
        totals[2] += len(regressed)
        totals[3] += len(lines)

    print(f"    {'total':<7}{totals[0]:>7}{totals[1]:>7}{totals[2]:>13}"
          f"{totals[3]:>12} lines added")
    print()


def main() -> None:
    runs = [Path(arg) for arg in sys.argv[1:]]
    if not runs:
        sys.exit(__doc__.strip().splitlines()[-1].strip())
    for run in runs:
        report(run)


if __name__ == "__main__":
    main()
