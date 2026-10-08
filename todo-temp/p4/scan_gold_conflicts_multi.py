"""P4: extend the gold-conflict example audit to the dev20/dev30 final guidelines.

Same method as todo-temp/p3/scan_gold_conflicts.py, but loops over the three
withTP scale runs (dev10/dev20/dev30) so the "same-kind gold check" the seminar
asked for is directly comparable: does a larger development set stop the loop
from writing exclusion examples that contradict gold?

Refinements over the p3 version:
  * label comparison is space-insensitive ("Specific Disease" == "SpecificDisease")
  * quoted fragments inside "(e.g., ...)" enumerations are skipped — they are
    rule head-noun lists, not examples

Only lines carrying an explicit exclusion/annotation cue are classified; quoted
items under bare "**Annotate**:" headers are not reached by line-level
heuristics. The script is a discovery aid: every flagged row is triaged manually
against the actual line text before it enters the report.

    python todo-temp/p4/scan_gold_conflicts_multi.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

RUNS = {
    "dev10": "20260802_gpt54-high_moderation",
    "dev20": "20260813_gpt54-high_moderation-withTP_dev20",
    "dev30": "20260812_gpt54-high_moderation-withTP_dev30",
}

EXCLUSION_HINT = re.compile(
    r"do \*\*not\*\*|do not|not annotate|not annotated|not treated? as|are \*\*not\*\*", re.I)
POSITIVE_HINT = re.compile(r"\bAnnotate\b", re.I)
QUOTE = re.compile(r"[“\"]([^”\"]{3,})[”\"]")
LABEL_OF = re.compile(r"as \*\*([A-Za-z ]+)\*\*")


def key(a):
    return (a["start"], a["end"], a["label"])


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def norm_label(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def example_quotes(line: str) -> list[str]:
    """Quoted strings on the line, minus fragments inside '(e.g., ...)' lists."""
    out = []
    for m in QUOTE.finditer(line):
        before = line[:m.start()]
        in_parens = before.rfind("(") > before.rfind(")")
        if in_parens and "e.g" in before[before.rfind("("):].lower():
            continue
        out.append(m.group(1))
    return out


def audit(run_dir: Path) -> dict:
    run = json.loads((run_dir / "final" / "iterative_refinement_run.json").read_text(encoding="utf-8"))
    guideline = run["final_guidelines"]
    initial_norm = norm(run["initial_guidelines"])
    lines = guideline.splitlines()

    files_init = {f["filename"]: f for f in run["initial_diagnostics"]["files"]}
    files_fin = {f["filename"]: f for f in run["final_diagnostics"]["files"]}
    names = sorted(files_init)

    gold_by_text: dict[str, list[tuple[str, str, tuple]]] = {}
    fin_keys: dict[str, set] = {}
    for name in names:
        fin_keys[name] = {key(a) for a in files_fin[name]["study_denotations"]}
        for a in files_init[name]["reference_denotations"]:
            gold_by_text.setdefault(norm(a["text"]), []).append((name, a["label"], key(a)))

    def lookup(text: str):
        n = norm(text)
        hits = gold_by_text.get(n)
        if hits:
            return hits
        out = []
        pat = re.compile(r"\b" + re.escape(n) + r"\b")
        for gtext, rows in gold_by_text.items():
            if pat.search(gtext):
                out.extend(rows)
            elif len(gtext) > len(n) and re.search(r"\b" + re.escape(gtext) + r"\b", n):
                out.extend(rows)
        return out

    audited = []
    for lineno, line in enumerate(lines, 1):
        if EXCLUSION_HINT.search(line):
            kind = "exclusion"
        elif POSITIVE_HINT.search(line):
            kind = "positive"
        else:
            continue
        quotes = example_quotes(line)
        if not quotes:
            continue
        stated = LABEL_OF.search(line)
        stated_label = stated.group(1).strip() if stated else None
        for q in quotes:
            hits = lookup(q)
            if not hits:
                continue
            gold_labels = sorted({lbl for _, lbl, _ in hits})
            if kind == "exclusion":
                if ("specific disease" in line.lower()
                        and all(norm_label(l) != "specificdisease" for l in gold_labels)):
                    verdict = "consistent_label_rule"
                else:
                    verdict = "CONTRADICTS_GOLD"
            elif stated_label and norm_label(stated_label) not in {norm_label(l) for l in gold_labels}:
                verdict = "CONTRADICTS_GOLD"
            else:
                verdict = "consistent"
            audited.append({
                "line": lineno, "kind": kind, "quote": q,
                "stated_label": stated_label, "gold_labels": gold_labels,
                "gold_occurrences": len(hits), "verdict": verdict,
                "provenance": "inherited" if norm(q) in initial_norm else "added",
                "per_doc": [{"doc": name, "gold_label": lbl,
                             "final": "TP" if k in fin_keys[name] else "miss"}
                            for name, lbl, k in hits],
            })
    return {
        "run": run_dir.name,
        "documents": len(names),
        "dev_f1": [run["initial_summary"]["overall_f1"], run["final_summary"]["overall_f1"]],
        "examples_with_gold_overlap": audited,
        "contradictions": [a for a in audited if a["verdict"] == "CONTRADICTS_GOLD"],
    }


def main() -> None:
    results = {}
    for label, dirname in RUNS.items():
        results[label] = audit(ROOT / "outputs" / "ncbi_disease" / dirname)
    (OUT / "gold_conflicts_multi.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for label, r in results.items():
        f1 = f"{r['dev_f1'][0]:.4f}->{r['dev_f1'][1]:.4f}"
        print(f"== {label} ({r['run']}, {r['documents']} docs, dev {f1})")
        print(f"   examples overlapping gold: {len(r['examples_with_gold_overlap'])}, "
              f"contradictions: {len(r['contradictions'])}")
        for a in r["examples_with_gold_overlap"]:
            print(f"   L{a['line']:<4} [{a['kind']}/{a['verdict']}/{a['provenance']}] "
                  f"\"{a['quote'][:60]}\" gold={a['gold_labels']} x{a['gold_occurrences']}")
    print("\nwritten to todo-temp/p4/gold_conflicts_multi.json")


if __name__ == "__main__":
    main()
