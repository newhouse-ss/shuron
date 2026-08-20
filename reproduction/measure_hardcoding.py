"""How much of a refined guideline is copied from the development set?

Two things get quoted into a guideline during refinement and they mean opposite
things:

  * A *discrepancy* mention is a case the round is moderating. Section 3.4.2 puts
    those in the prompt on purpose and Section 3.4.4 expects the rewritten
    guideline to address them, so quoting one is the method working.

  * A *true positive* is a case the model already got right. It reaches the
    prompt only through the CONSTRAINT block, whose stated job is to stop the
    rewrite from breaking cases that already pass. Writing one into the guideline
    turns a constraint into an answer key: the mention is then scored on the same
    documents it was copied from.

So the quantity of interest is not "how much text was quoted" but "how much of
what was quoted is the answer key". Two measurements:

  A. absorption   of the distinct gold mention strings in the development split,
                  how many appear verbatim in the final guideline without having
                  been in the initial one. A recall-style view: how much of the
                  set leaked in.

  B. added-line   of the lines the refinement *added*, how many quote a baseline
     hardcoding  true positive verbatim. A precision-style view: how much of the
                  new content is answer key. The same count restricted to
                  discrepancy mentions is reported beside it as the contrast.

Both ignore strings already present in the initial guideline, otherwise the
shipped guideline's own examples would be counted as leakage.

    python reproduction/measure_hardcoding.py
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

RUNS = [
    ("dev10  withTP", "20260802_ncbi_gpt54-high_moderation"),
    ("dev20  withTP", "20260813_ncbi_gpt54-high_moderation-withTP_dev20"),
    ("dev30  withTP", "20260812_ncbi_gpt54-high_moderation-withTP_dev30"),
    ("dev10  noTP r2", "20260806_ncbi_gpt54-high_moderation-noTP_run2"),
    ("dev10  noTP r4", "20260806_ncbi_gpt54-high_moderation-noTP_run4"),
    ("dev10  noTP r5", "20260806_ncbi_gpt54-high_moderation-noTP_run5"),
    # Experiment 2: the block stays, one instruction forbids transcribing it.
    ("dev10  abstr r1", "20260814_ncbi_gpt54-high_moderation-abstraction_run1"),
    ("dev10  abstr r2", "20260814_ncbi_gpt54-high_moderation-abstraction_run2"),
]

# Mentions this short match inside ordinary words ("DM" inside "ADMIT"), so a
# verbatim hit carries no evidence that the string was copied.
MIN_LENGTH = 4


def mention_sets(diagnostics: dict) -> tuple[set[str], set[str]]:
    """(true positives, gold mentions) as raw strings, from a scored annotation."""
    true_positives: set[str] = set()
    gold: set[str] = set()
    for entry in diagnostics["files"]:
        for pair in entry["matched_pairs"]:
            true_positives.add(pair["reference_text"])
        for denotation in entry["reference_denotations"]:
            gold.add(denotation["text"])
    keep = lambda s: len(s) >= MIN_LENGTH
    return {s for s in true_positives if keep(s)}, {s for s in gold if keep(s)}


def added_lines(before: str, after: str) -> list[str]:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), n=0)
    return [line[1:] for line in diff
            if line.startswith("+") and not line.startswith("+++") and line[1:].strip()]


def measure(run_directory: Path) -> dict:
    run = json.loads((run_directory / "final" / "iterative_refinement_run.json")
                     .read_text(encoding="utf-8"))
    initial, final = run["initial_guidelines"], run["final_guidelines"]
    true_positives, gold = mention_sets(run["initial_diagnostics"])

    # Anything the shipped guideline already said is not something refinement copied.
    true_positives = {s for s in true_positives if s not in initial}
    discrepancies = {s for s in gold - true_positives if s not in initial}
    absorbable = {s for s in gold if s not in initial}

    absorbed = {s for s in absorbable if s in final}

    lines = added_lines(initial, final)
    quoting_tp = [l for l in lines if any(s in l for s in true_positives)]
    quoting_discrepancy = [l for l in lines
                           if any(s in l for s in discrepancies)
                           and not any(s in l for s in true_positives)]

    characters = sum(len(l) for l in lines) or 1
    return {
        "run": run_directory.name,
        "documents": len(run["sampled_documents"]),
        "rounds": len(run["iterations"]),
        "dev_f1": [run["initial_summary"]["overall_f1"], run["final_summary"]["overall_f1"]],
        "guideline_chars": [len(initial), len(final)],
        "absorption": {
            "absorbed": len(absorbed), "absorbable": len(absorbable),
            "rate": len(absorbed) / len(absorbable) if absorbable else 0.0,
            "strings": sorted(absorbed),
        },
        "added_lines": {
            "total": len(lines),
            "quoting_true_positive": len(quoting_tp),
            "quoting_discrepancy": len(quoting_discrepancy),
            "rate_lines": len(quoting_tp) / len(lines) if lines else 0.0,
            "rate_characters": sum(len(l) for l in quoting_tp) / characters,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default="reproduction/results/hardcoding.json")
    parser.add_argument("--show-strings", action="store_true",
                        help="list the absorbed mentions for each run")
    args = parser.parse_args()

    results = []
    for label, directory in RUNS:
        path = REPO_ROOT / "outputs" / directory
        if not (path / "final" / "iterative_refinement_run.json").exists():
            print(f"{label:<16} (no final run file, skipped)")
            continue
        record = measure(path)
        record["label"] = label
        results.append(record)

    print(f"{'run':<16}{'docs':>5}{'rnd':>5}{'dev F1':>16}{'chars':>16}"
          f"{'absorbed':>11}{'added':>7}{'  TP-quoting':>14}{'disc':>6}")
    print("-" * 96)
    for r in results:
        a, l = r["absorption"], r["added_lines"]
        f1 = f"{r['dev_f1'][0]:.4f}->{r['dev_f1'][1]:.4f}"
        chars = f"{r['guideline_chars'][0]}->{r['guideline_chars'][1]}"
        print(f"{r['label']:<16}{r['documents']:>5}{r['rounds']:>5}{f1:>16}{chars:>16}"
              f"{a['absorbed']:>4}/{a['absorbable']:<3}{a['rate']:>4.0%}"
              f"{l['total']:>7}{l['quoting_true_positive']:>7}{l['rate_lines']:>7.0%}"
              f"{l['quoting_discrepancy']:>6}")

    if args.show_strings:
        for r in results:
            print(f"\n{r['label']} absorbed: {', '.join(r['absorption']['strings']) or '(none)'}")

    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
