"""Discrepancy matrices for a set of runs, one row per run, one column per round.

Each cell is the (gold type, predicted type) matrix after that round, in the same
form as docs/discrepancy_matrices.svg: exact matches are discarded first, what is
left is paired by character overlap, and anything with no partner goes to O. The
diagonal therefore holds span boundary mismatches, not agreement.

The numbers come from `all_clusters` in each round snapshot, which the pipeline
builds with exactly that matcher, so nothing is recomputed here.

Colour is scaled against one maximum shared by every panel in the figure, so the
same shade means the same count wherever it appears. Panels for rounds a run did
not reach are left blank.

    python reproduction/draw_discrepancy_matrices.py out.svg outputs/<run> ...
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LABELS = ["CompositeMention", "DiseaseClass", "Modifier", "SpecificDisease", "O"]
SHORT = ["C", "D", "M", "S", "O"]
KEY = re.compile(r"Gold: (\w+) vs LLM: (\w+)")

CELL_W, CELL_H = 27, 22
GUTTER, PITCH_X, PITCH_Y = 168, 196, 166
TOP = 34
FULL = (237, 115, 115)


def matrix(clusters) -> list[list[int]]:
    grid = [[0] * 5 for _ in range(5)]
    for cluster in clusters:
        found = KEY.search(cluster["key"])
        if not found:
            continue
        gold, pred = found.groups()
        if gold not in LABELS or pred not in LABELS:
            continue
        grid[LABELS.index(gold)][LABELS.index(pred)] += cluster["count"]
    return grid


def states(run: Path):
    """(title, matrix) for the initial guideline and after each round."""
    snapshots = [json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(run.glob("rounds/iteration_*/snapshot.json"))]
    if not snapshots:
        return []
    out = [("Iter 0", matrix(snapshots[0]["summary_before"]["all_clusters"]))]
    for s in snapshots:
        out.append((f"Iter {s['iteration']}", matrix(s["summary_after"]["all_clusters"])))
    return out


def shade(count: int, top: int) -> str:
    if count <= 0:
        return None
    t = (count / top) ** 1.15
    return "#%02x%02x%02x" % tuple(round(255 - (255 - c) * t) for c in FULL)


def panel(x: float, y: float, grid, top: int) -> list[str]:
    """One matrix. x is the left edge of the number columns, y the top rule."""
    out = [f'<line x1="{x - 24}" y1="{y}" x2="{x + 5 * CELL_W}" y2="{y}" '
           f'stroke="#000" stroke-width="1.1"/>']
    for column, name in enumerate(SHORT):
        out.append(f'<text x="{x + column * CELL_W + CELL_W / 2}" y="{y + 13}" font-size="11.5" '
                   f'text-anchor="middle">{name}</text>')
    out.append(f'<line x1="{x - 24}" y1="{y + 18}" x2="{x + 5 * CELL_W}" y2="{y + 18}" '
               f'stroke="#000" stroke-width="0.7"/>')
    out.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 18 + 5 * CELL_H}" '
               f'stroke="#000" stroke-width="0.7"/>')
    for row, name in enumerate(SHORT):
        base = y + 18 + row * CELL_H
        out.append(f'<text x="{x - 12}" y="{base + 15}" font-size="11.5" '
                   f'text-anchor="middle">{name}</text>')
        for column in range(5):
            value = grid[row][column]
            fill = shade(value, top)
            if fill:
                out.append(f'<rect x="{x + column * CELL_W}" y="{base}" width="{CELL_W}" '
                           f'height="{CELL_H}" fill="{fill}"/>')
            out.append(f'<text x="{x + column * CELL_W + CELL_W / 2}" y="{base + 15}" '
                       f'font-size="11.5" text-anchor="middle">{value}</text>')
    out.append(f'<line x1="{x - 24}" y1="{y + 18 + 5 * CELL_H}" x2="{x + 5 * CELL_W}" '
               f'y2="{y + 18 + 5 * CELL_H}" stroke="#000" stroke-width="1.1"/>')
    return out


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: draw_discrepancy_matrices.py out.svg outputs/<run> ...")
    target, runs = Path(sys.argv[1]), [Path(a) for a in sys.argv[2:]]

    rows = []
    for run in runs:
        cells = states(run)
        if not cells:
            print(f"skipped (no rounds): {run.name}")
            continue
        status = json.loads((run / "status.json").read_text(encoding="utf-8"))
        rows.append((run.name, status, cells))

    columns = max(len(cells) for _, _, cells in rows)
    top = max(v for _, _, cells in rows for _, grid in cells for row in grid for v in row)
    width = GUTTER + columns * PITCH_X - (PITCH_X - 5 * CELL_W) + 10
    height = TOP + len(rows) * PITCH_Y

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" font-family="Times New Roman, Times, serif">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']

    for index in range(columns):
        x = GUTTER + index * PITCH_X
        svg.append(f'<text x="{x + 5 * CELL_W / 2}" y="20" font-size="13" '
                   f'text-anchor="middle">Iter {index}</text>')
    svg.append(f'<text x="{GUTTER - 24}" y="20" font-size="11.5" text-anchor="end">'
               f'<tspan font-weight="bold">Gold</tspan> &#8595;'
               f'<tspan dx="10" font-weight="bold">Pred</tspan> &#8594;</text>')

    for row_index, (name, status, cells) in enumerate(rows):
        y = TOP + row_index * PITCH_Y
        label = name.replace("20260902_ncbi_gpt54-high_", "").replace(
            "20260901_ncbi_gpt54-high_", "").replace("20260802_ncbi_gpt54-high_", "")
        svg.append(f'<text x="{GUTTER - 34}" y="{y + 56}" font-size="12.5" '
                   f'text-anchor="end" font-weight="bold">{label}</text>')
        svg.append(f'<text x="{GUTTER - 34}" y="{y + 73}" font-size="11" text-anchor="end">'
                   f'F1 {status.get("initial_f1", 0):.3f} &#8594; {status.get("final_f1", 0):.3f}</text>')
        svg.append(f'<text x="{GUTTER - 34}" y="{y + 89}" font-size="11" text-anchor="end">'
                   f'{status.get("stop_reason", "")}</text>')
        for column_index, (_, grid) in enumerate(cells):
            total = sum(sum(r) for r in grid)
            x = GUTTER + column_index * PITCH_X
            svg.extend(panel(x, y + 12, grid, top))
            svg.append(f'<text x="{x + 5 * CELL_W / 2}" y="{y + 12 + 18 + 5 * CELL_H + 14}" '
                       f'font-size="11" text-anchor="middle">total {total}</text>')

    svg.append("</svg>")
    target.write_text("\n".join(svg), encoding="utf-8")
    print(f"{target}: {len(rows)} runs x {columns} columns, colour scaled to a maximum of {top}")


if __name__ == "__main__":
    main()
