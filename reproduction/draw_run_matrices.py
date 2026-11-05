"""One run's discrepancy matrices in a single row, in the style of Figure 2.

Same layout as docs/discrepancy_matrices.svg: a panel per state, titled
"(a) Iter 0 (G0)", with the Gold/Pred header above each matrix and booktabs
rules. Adds the round's discrepancy total under every panel.

Colour is scaled to a maximum of six so the shading is comparable with the
existing figure and between the runs drawn this way; pass --max to change it.

    python reproduction/draw_run_matrices.py outputs/<run> docs/<name>.svg
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from draw_discrepancy_matrices import CELL_H, CELL_W, LABELS, panel, states  # noqa: E402

LEFT = 63.5          # x of the first number column, as in the published figure
PITCH = 232.0
MARGIN = 39.5
TOP_RULE = 40.0
LETTERS = "abcdefghij"

KEY = re.compile(r"Gold: (\w+) vs LLM: (\w+)")
SELECTED = "#1f9be0"     # sky blue: the groups this round set out to repair
SIDE_EFFECT = "#1a7f37"  # forest green: groups that grew while it did so


def coordinates(key: str):
    found = KEY.search(key)
    if not found:
        return None
    gold, pred = found.groups()
    if gold not in LABELS or pred not in LABELS:
        return None
    return LABELS.index(gold), LABELS.index(pred)


def highlights(run: Path, k: int):
    """Cells to outline in panel 0 (selected) and panel 1 (grown)."""
    snapshot = sorted(run.glob("rounds/iteration_*/snapshot.json"))
    if not snapshot:
        return {}
    first = json.loads(snapshot[0].read_text(encoding="utf-8"))
    before = {c["key"]: c["count"] for c in first["summary_before"]["all_clusters"]}
    after = {c["key"]: c["count"] for c in first["summary_after"]["all_clusters"]}

    selected = [coordinates(c["key"])
                for c in first["summary_before"]["all_clusters"][:k]]
    grown = [coordinates(key) for key in sorted(set(before) | set(after))
             if after.get(key, 0) > before.get(key, 0)]
    return {0: [(cell, SELECTED) for cell in selected if cell],
            1: [(cell, SIDE_EFFECT) for cell in grown if cell]}


def outline(x: float, y: float, cells) -> list[str]:
    out = []
    for (row, column), colour in cells:
        out.append(f'<rect x="{x + column * CELL_W:g}" y="{y + 18 + row * CELL_H:g}" '
                   f'width="{CELL_W}" height="{CELL_H}" fill="none" stroke="{colour}" '
                   f'stroke-width="2"/>')
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("run")
    parser.add_argument("target")
    parser.add_argument("--max", type=int, default=6, help="Count that takes the deepest shade")
    parser.add_argument("--panels", type=int,
                        help="Draw only the first N states. The published figure stops at Iter 3, "
                             "which is the three rounds the abstract reports.")
    parser.add_argument("--mark", type=int, metavar="K",
                        help="Outline the K groups round 1 moderated in Iter 0, and the groups "
                             "that grew during it in Iter 1.")
    args = parser.parse_args()

    cells = states(Path(args.run))
    if not cells:
        raise SystemExit(f"no rounds in {args.run}")
    if args.panels:
        cells = cells[:args.panels]
    marks = highlights(Path(args.run), args.mark) if args.mark else {}

    width = LEFT + (len(cells) - 1) * PITCH + 135 + MARGIN
    height = 195

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height}" '
           f'width="{width:g}" height="{height}" font-family="Times New Roman, Times, serif">',
           f'<rect width="{width:g}" height="{height}" fill="#ffffff"/>']

    for index, (title, grid) in enumerate(cells):
        x = LEFT + index * PITCH
        centre = x + 55.5      # midpoint of the panel including its row-label column
        iteration = title.split()[-1]
        svg.append(f'<text x="{centre:g}" y="15" font-size="13" text-anchor="middle">'
                   f'({LETTERS[index]}) Iter {iteration} (G{iteration})</text>')
        svg.append(f'<text x="{centre:g}" y="32" font-size="11.5" text-anchor="middle">'
                   f'<tspan font-weight="bold">Gold</tspan> &#8595;'
                   f'<tspan dx="14" font-weight="bold">Pred</tspan> &#8594;</text>')
        svg.extend(panel(x, TOP_RULE, grid, args.max))
        svg.extend(outline(x, TOP_RULE, marks.get(index, [])))
        total = sum(sum(row) for row in grid)
        svg.append(f'<text x="{centre:g}" y="186" font-size="12" text-anchor="middle">'
                   f'total {total}</text>')

    svg.append("</svg>")
    Path(args.target).write_text("\n".join(svg), encoding="utf-8")
    print(f"{args.target}: {len(cells)} panels, totals "
          f"{[sum(sum(r) for r in g) for _, g in cells]}")


if __name__ == "__main__":
    main()
