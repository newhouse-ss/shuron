"""Materialise nested development-set splits so size experiments are reproducible.

WHY NOT JUST CHANGE sample_size
-------------------------------
`sample_pubannotation_documents` calls `random.sample(pool, k)`. For this pool
that happens to be nested — the 10 documents at k=10 are a subset of those at
k=30, and so on — but only because CPython's `random.sample` switches algorithms
based on the k/n ratio, and below the switch it draws sequentially. On the NCBI
pool (n=593) the property holds up to k=85 and breaks at k=86. The threshold
moves with pool size, so it differs for BC5CDR (500) and BioRED (400), and it is
an implementation detail that a Python upgrade may change.

A size experiment needs the smaller split to be a strict subset of the larger
one, otherwise "more data" is confounded with "different data". Relying on an
accident of the standard library for that is not acceptable, so the splits are
written to disk once and read back by id.

CONTINUITY
----------
The 10-document split is exactly the subset already used by every run so far
(`random.sample(pool, 10)` with seed 42), so results already collected at size
10 remain valid. Larger splits extend it: each is the previous split plus
additional documents drawn from the remainder with a fixed seed.

    python reproduction/make_dev_splits.py --dataset ncbi_disease --sizes 10 30 50
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation.sampling import list_pubannotation_documents  # noqa: E402

SPLIT_DIR = Path(__file__).resolve().parent / "dev_splits"


def build(dataset: str, sizes: list[int], seed: int) -> dict[int, list[str]]:
    pool = [p.name for p in list_pubannotation_documents(REPO_ROOT / "data/datasets" / dataset / "train")]

    # Seed the smallest split with the subset already in use, so prior runs stay
    # comparable, then grow it by drawing from what remains.
    chosen = sorted(random.Random(seed).sample(pool, sizes[0]))
    splits = {sizes[0]: list(chosen)}

    remaining = [name for name in pool if name not in set(chosen)]
    rng = random.Random(seed)
    rng.shuffle(remaining)

    cursor = 0
    for size in sizes[1:]:
        need = size - len(chosen)
        if need > len(remaining) - cursor:
            raise ValueError(f"pool of {len(pool)} cannot supply {size} documents")
        chosen = chosen + remaining[cursor:cursor + need]
        cursor += need
        splits[size] = sorted(chosen)

    return splits


def main() -> None:
    parser = argparse.ArgumentParser(description="Write nested dev-set splits to disk.")
    parser.add_argument("--dataset", default="ncbi_disease")
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 30, 50])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sizes = sorted(args.sizes)
    splits = build(args.dataset, sizes, args.seed)

    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    for size, names in splits.items():
        path = SPLIT_DIR / f"{args.dataset}_dev{size}.json"
        path.write_text(
            json.dumps({"dataset": args.dataset, "size": size, "seed": args.seed,
                        "documents": names}, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {path.name}  ({len(names)} documents)")

    print()
    previous = None
    for size in sizes:
        current = set(splits[size])
        if previous is not None:
            assert previous < current, f"split {size} does not contain the smaller one"
            print(f"  dev{sizes[sizes.index(size)-1]} ⊂ dev{size}  ok  (+{len(current - previous)} new)")
        previous = current


if __name__ == "__main__":
    main()
