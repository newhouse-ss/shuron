"""Derived numbers for evidence_notes.md, section 3. Inputs are copied from cited sources; nothing is measured here.

NCBI corpus (Dogan and Lu 2012, Section 3.2 and Table 4):
    3295 pre-annotated mentions, 1750 found unchanged in the final corpus, 1545 modified or deleted, 3605 new.
    Final corpus mentions: train 5148 + dev 791 + test 961.
This study, top-4 guideline on valid100 (nodes/2026-10-20_meeting/plan-v3/error_breakdown_output.txt):
    strict TP 629 FP 148 FN 162; span-only TP 670 FP 107 FN 121.

    python nodes/2026-10-20_meeting/plan-v3/preannot_derived.py
"""
from pathlib import Path

pre, kept, changed, new = 3295, 1750, 1545, 3605
final = 5148 + 791 + 961
p, r = kept / pre, kept / final
lines = [
    f"NCBI final mentions {final}; kept + changed + new = {kept + changed + new}",
    f"NCBI pre-annotation kept unchanged: precision-like {p:.3f}, recall-like {r:.3f}, F1-like {2 * p * r / (p + r):.3f}",
]
for name, (tp, fp, fn) in {"top-4 strict": (629, 148, 162), "top-4 span-only": (670, 107, 121)}.items():
    f1 = 2 * tp / (2 * tp + fp + fn)
    lines.append(f"{name}: P {tp / (tp + fp):.3f} R {tp / (tp + fn):.3f} F1 {f1:.4f} Jaccard {tp / (tp + fp + fn):.3f}")
out = "\n".join(lines)
(Path(__file__).resolve().parent / "preannot_derived_output.txt").write_text(out + "\n", encoding="utf-8")
print(out)
