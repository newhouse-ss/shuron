"""Score valid-set predictions against gold locally. No LLM calls, no API key.

Usage:

    python reproduction/eval_valid.py \
        --gold-dir data/datasets/ncbi_disease/valid \
        --pred-dir outputs/ncbi_valid_annotations \
        --label ncbi-gpt-r-g

Add --entities data/schemas/ncbi_entities.schema.json to pin the confusion
matrix axis to the full schema, so labels the model never predicted still show
up as rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.discrepancy import GOLD_ROWS, PRED_ROWS  # noqa: E402
from lib.report import render  # noqa: E402
from lib.scoring import score_directory  # noqa: E402

DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "results"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strict-match evaluation of PubAnnotation predictions against gold.",
    )
    parser.add_argument("--gold-dir", required=True, help="Directory of gold PubAnnotation JSON")
    parser.add_argument("--pred-dir", required=True, help="Directory of predicted PubAnnotation JSON")
    parser.add_argument("--label", default="run", help="Name for this run, used for the output folder")
    parser.add_argument("--entities", help="Entity schema JSON, pins the confusion matrix axis")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Where to write result files")
    parser.add_argument(
        "--orient",
        default=PRED_ROWS,
        choices=[PRED_ROWS, GOLD_ROWS],
        help=(
            "Confusion matrix layout. Default matches how Figure 3's numbers line up "
            "with the Section 5.4 narrative; gold-rows follows the Figure 3 caption. "
            "Layout only, the counts are identical either way."
        ),
    )
    parser.add_argument("--no-write", action="store_true", help="Print the report without writing files")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit non-zero if any document failed to align",
    )
    return parser


def _load_entity_labels(path: str | None) -> list[str] | None:
    if not path:
        return None
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [row if isinstance(row, str) else row["name"] for row in rows]


def main() -> int:
    args = build_parser().parse_args()

    result = score_directory(
        gold_dir=args.gold_dir,
        pred_dir=args.pred_dir,
        label=args.label,
        entity_labels=_load_entity_labels(args.entities),
        orientation=args.orient,
    )

    report = render(result)
    print(report)

    if not args.no_write:
        out_dir = Path(args.out_dir) / args.label
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "metrics.json").write_text(
            json.dumps(result.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / "per_document.json").write_text(
            json.dumps(result.per_document, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / "discrepancies.json").write_text(
            json.dumps([item.as_dict() for item in result.discrepancies], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
        print(f"\nwritten to {out_dir}")

    if args.require_complete and not result.alignment.is_complete:
        print("\nFAILED: --require-complete was set and some documents did not align.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
