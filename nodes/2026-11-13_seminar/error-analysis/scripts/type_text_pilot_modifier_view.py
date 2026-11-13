"""Review view of the type-text pilot: units judged to affect Modifier in original, top-4 loop08, top-4 loop04. Offline, 2026-11-10.
Marks per unit whether the other Codex run (commit df42249) also judged it Modifier, and whether its line is quoted in the
loop08/loop04 pair file (outputs/overall_view/pair_loop08_loop04_modifier.md). Lists pair-file lines with no Modifier unit.
Usage: python -I type_text_pilot_modifier_view.py  (writes outputs/type_text/pilot_modifier_units.md)
"""
import csv, io, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
D = ROOT / "nodes/2026-11-13_seminar/error-analysis/outputs" / "type_text"
PAIR = ROOT / "nodes/2026-11-13_seminar/error-analysis/outputs" / "overall_view" / "pair_loop08_loop04_modifier.md"
pair_lines = {"top4_loop08": set(), "top4_loop04": set()}
for row in PAIR.read_text(encoding="utf-8").splitlines():
    if not re.match(r"\| \d+ \|", row):
        continue
    cells = row.split(" | ")
    for name, cell in (("top4_loop08", cells[1]), ("top4_loop04", cells[2])):
        pair_lines[name] |= {int(x) for x in re.findall(r"\bL(\d+):", cell)}
is_mod = lambda r: r["judgement"] == "types" and "Modifier" in r["types"].split(";")
out = ["# Type-text pilot: units judged to affect Modifier (run in working tree; other run = commit df42249)", ""]
for n in ["original", "top4_loop08", "top4_loop04"]:
    a = list(csv.DictReader(open(D / f"units_{n}.csv", encoding="utf-8")))
    b = list(csv.DictReader(io.StringIO(subprocess.run(["git", "-C", str(ROOT), "show", f"df42249:todo-temp/error-analysis/outputs/type_text/units_{n}.csv"],
                                                       capture_output=True, encoding="utf-8", check=True).stdout)))
    out += [f"## {n}", "", "| line | other run | in pair file | types | text | reason |", "| --- | --- | --- | --- | --- | --- |"]
    for ra, rb in zip(a, b):
        if is_mod(ra) or is_mod(rb):
            inpair = ("yes" if int(ra["line_start"]) in pair_lines[n] else "no") if n in pair_lines else ""
            other = "yes" if is_mod(ra) and is_mod(rb) else ("only other run" if is_mod(rb) else "no")
            out.append(f"| {ra['line_start']} | {other} | {inpair} | {ra['types'] or ra['judgement']} | {ra['text'].replace('|', '/')} | {ra['reason']} |")
    if n in pair_lines:
        mod_lines = {int(r["line_start"]) for r in a if is_mod(r)}
        missing = sorted(pair_lines[n] - mod_lines)
        out += ["", f"Pair-file lines with no unit judged Modifier in this run: {missing}"]
        for r in a:
            if int(r["line_start"]) in missing:
                out.append(f"- L{r['line_start']} ({r['judgement']} {r['types']}): {r['text'][:200]}")
    out.append("")
(D / "pilot_modifier_units.md").write_text("\n".join(out), encoding="utf-8")
