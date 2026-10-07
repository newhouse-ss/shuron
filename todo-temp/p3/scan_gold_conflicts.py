"""P3-A3: does the top-4 final guideline contradict gold on the dev10 documents?

Two directions, both offline (no LLM calls), run against
outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/iterative_refinement_run.json:

  1. example audit   every Annotate / Do-not-annotate example quoted in the final
                     guideline is looked up in the dev10 gold. An example
                     "contradicts gold" when gold annotates the quoted string with
                     a different label (positive examples) or annotates it at all
                     while the example bans annotating it (exclusion examples).
                     Label-scoped rules ("X is not a Specific Disease" while gold
                     says DiseaseClass) are reported as consistent label rules.

  2. error coverage  of the mentions the final model still gets wrong (FN/FP),
                     how many are strings the guideline itself quotes, and in
                     which kind of example. This tells whether remaining errors
                     are guideline-discussed cases or new ground.

    python todo-temp/p3/scan_gold_conflicts.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10"
OUT = Path(__file__).resolve().parent

EXCLUSION_HINT = re.compile(
    r"do \*\*not\*\*|do not|not annotate|not annotated|not treated? as|are \*\*not\*\*", re.I)
POSITIVE_HINT = re.compile(r"\bAnnotate\b", re.I)
QUOTE = re.compile(r"[“\"]([^”\"]{3,})[”\"]")
LABEL_OF = re.compile(r"as \*\*([A-Za-z ]+)\*\*")
LABELS = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"]


def key(a):
    return (a["start"], a["end"], a["label"])


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def main() -> None:
    run = json.loads((RUN / "final" / "iterative_refinement_run.json").read_text(encoding="utf-8"))
    guideline = run["final_guidelines"]
    initial_guideline_norm = norm(run["initial_guidelines"])
    lines = guideline.splitlines()

    files_init = {f["filename"]: f for f in run["initial_diagnostics"]["files"]}
    files_fin = {f["filename"]: f for f in run["final_diagnostics"]["files"]}
    names = sorted(files_init)

    gold_by_text: dict[str, list[tuple[str, str, tuple]]] = {}
    gold_keys: dict[str, set] = {}
    init_keys: dict[str, set] = {}
    fin_keys: dict[str, set] = {}
    for name in names:
        gold = files_init[name]["reference_denotations"]
        gold_keys[name] = {key(a) for a in gold}
        init_keys[name] = {key(a) for a in files_init[name]["study_denotations"]}
        fin_keys[name] = {key(a) for a in files_fin[name]["study_denotations"]}
        for a in gold:
            gold_by_text.setdefault(norm(a["text"]), []).append((name, a["label"], key(a)))

    def lookup(text: str) -> list[tuple[str, str, tuple]]:
        n = norm(text)
        hits = gold_by_text.get(n)
        if hits:
            return hits
        # relaxed: substring only across word boundaries, so "Neisseria" does
        # not match "neisserial"
        out = []
        pat = re.compile(r"\b" + re.escape(n) + r"\b")
        for gtext, rows in gold_by_text.items():
            if pat.search(gtext):
                out.extend(rows)
            elif len(gtext) > len(n) and re.search(r"\b" + re.escape(gtext) + r"\b", n):
                out.extend(rows)
        return out

    # ---- 1. example audit -------------------------------------------------
    audited = []
    for lineno, line in enumerate(lines, 1):
        is_excl = bool(EXCLUSION_HINT.search(line))
        is_pos = bool(POSITIVE_HINT.search(line))
        if is_excl:
            kind = "exclusion"          # negation wins over the word "annotate"
        elif is_pos:
            kind = "positive"
        else:
            continue
        quotes = QUOTE.findall(line)
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
                        and all(norm(l) != "specificdisease" for l in gold_labels)):
                    verdict = "consistent_label_rule"
                else:
                    verdict = "CONTRADICTS_GOLD"
            elif stated_label and norm(stated_label) not in {norm(l) for l in gold_labels}:
                verdict = "CONTRADICTS_GOLD"
            else:
                verdict = "consistent"
            per_doc = [{"doc": name, "gold_label": lbl,
                        "initial": "TP" if k in init_keys[name] else "miss",
                        "final": "TP" if k in fin_keys[name] else "miss"}
                       for name, lbl, k in hits]
            audited.append({
                "line": lineno, "kind": kind, "quote": q,
                "stated_label": stated_label, "gold_labels": gold_labels,
                "gold_occurrences": len(hits), "verdict": verdict,
                "provenance": "inherited" if norm(q) in initial_guideline_norm else "added",
                "per_doc": per_doc, "line_text": line.strip(),
            })

    contradictions = [a for a in audited if a["verdict"] == "CONTRADICTS_GOLD"]

    # ---- 2. error coverage ------------------------------------------------
    def totals(pred):
        tp = sum(len(gold_keys[n] & pred[n]) for n in names)
        fp = sum(len(pred[n] - gold_keys[n]) for n in names)
        fn = sum(len(gold_keys[n] - pred[n]) for n in names)
        return {"tp": tp, "fp": fp, "fn": fn, "f1": round(2 * tp / (2 * tp + fp + fn), 4)}

    def label_stats(pred):
        out = {}
        for lab in LABELS:
            tp = fp = fn = 0
            for n in names:
                g = {k for k in gold_keys[n] if k[2] == lab}
                p = {k for k in pred[n] if k[2] == lab}
                tp += len(g & p)
                fp += len(p - g)
                fn += len(g - p)
            denom = 2 * tp + fp + fn
            out[lab] = {"tp": tp, "fp": fp, "fn": fn,
                        "f1": round(2 * tp / denom, 4) if denom else None}
        return out

    def text_of(name, k):
        for a in files_init[name]["reference_denotations"]:
            if key(a) == k:
                return a["text"]
        for a in files_fin[name]["study_denotations"]:
            if key(a) == k:
                return a["text"]
        return "?"

    guideline_norm = norm(guideline)
    excl_lines_norm = [norm(l) for l in lines if EXCLUSION_HINT.search(l)]

    fn_final = []
    for n in names:
        for k in sorted(gold_keys[n] - fin_keys[n]):
            t = text_of(n, k)
            fn_final.append({
                "doc": n, "label": k[2], "text": t,
                "in_guideline": norm(t) in guideline_norm,
                "in_exclusion_line": any(norm(t) in l for l in excl_lines_norm),
                "initial_was": "TP" if k in init_keys[n] else "miss",
            })

    fp_final = []
    for n in names:
        for k in sorted(fin_keys[n] - gold_keys[n]):
            t = text_of(n, k)
            fp_final.append({
                "doc": n, "label": k[2], "text": t,
                "in_guideline": norm(t) in guideline_norm,
                "initial_also_fp": k in (init_keys[n] - gold_keys[n]),
            })

    result = {
        "run": RUN.name,
        "dev_f1": {"initial": totals(init_keys), "final": totals(fin_keys)},
        "by_label": {"initial": label_stats(init_keys), "final": label_stats(fin_keys)},
        "examples_with_gold_overlap": audited,
        "contradictions": contradictions,
        "fn_final": fn_final,
        "fp_final": fp_final,
        "fn_covered_by_guideline": sum(1 for r in fn_final if r["in_guideline"]),
        "fn_covered_by_exclusion_line": sum(1 for r in fn_final if r["in_exclusion_line"]),
        "fp_covered_by_guideline": sum(1 for r in fp_final if r["in_guideline"]),
    }
    (OUT / "a3_gold_conflicts.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"run {RUN.name}")
    print(f"dev F1 initial {result['dev_f1']['initial']} final {result['dev_f1']['final']}")
    print("by-label F1 (initial -> final):")
    for lab in LABELS:
        print(f"  {lab:<17} {result['by_label']['initial'][lab]} -> {result['by_label']['final'][lab]}")
    print(f"\nexamples overlapping gold: {len(audited)}, contradictions: {len(contradictions)}")
    for a in audited:
        print(f"  L{a['line']:<4} [{a['kind']}/{a['verdict']}/{a['provenance']}] \"{a['quote']}\" "
              f"stated={a['stated_label']} gold={a['gold_labels']} x{a['gold_occurrences']}")
        for d in a["per_doc"]:
            print(f"        {d['doc']:<12} gold={d['gold_label']:<17} "
                  f"initial={d['initial']:<5} final={d['final']}")
    print(f"\nfinal-model FN: {len(fn_final)} "
          f"(guideline quotes {result['fn_covered_by_guideline']}, "
          f"exclusion lines cover {result['fn_covered_by_exclusion_line']})")
    for r in fn_final:
        flag = "[exclusion-line]" if r["in_exclusion_line"] else (
            "[in-guideline]" if r["in_guideline"] else "")
        print(f"  FN {r['doc']:<12} {r['label']:<17} \"{r['text']}\" {flag} initial={r['initial_was']}")
    print(f"\nfinal-model FP: {len(fp_final)} (guideline quotes {result['fp_covered_by_guideline']})")
    for r in fp_final:
        flag = "[in-guideline]" if r["in_guideline"] else ""
        print(f"  FP {r['doc']:<12} {r['label']:<17} \"{r['text']}\" {flag} "
              f"initial_also_fp={r['initial_also_fp']}")


if __name__ == "__main__":
    main()
