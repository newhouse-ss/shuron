"""Would any call cross Claude Haiku 5.5's 100,000-token prompt threshold, and what would the measured DeepSeek
token counts cost at Haiku prices? No API calls.

Haiku 5.5 bills a request on the higher rate card when its prompt (all input tokens, cache reads and writes
included) is over 100,000 tokens; output does not count (platform.claude.com/docs/en/about-claude/pricing,
fetched 2026-10-22). Prices per 1M tokens, prompt up to 100K: input $0.10, cache hit $0.01, output $0.50;
Batch API input $0.05, output $0.25.

Prompt sizes:
  annotation: measured DeepSeek prompt tokens of the 254 saved calls (dev10, original guideline);
  valid100 with a refined guideline: the largest dev10 prompt without the original guideline (template and one
    document) + the largest saved final guideline + the largest valid100 document file, an overestimate;
  loop analysis calls: the largest saved GPT-5.4 dev10 loop prompt (infer / principle / rewrite), as characters.
Characters are turned into tokens at DeepSeek's measured ratio and, as a margin for Haiku's different
tokenizer, at 2 characters per token.
"""
import glob
import json
import statistics as st
from pathlib import Path

import run_stability as rs

THRESHOLD = 100_000
HAIKU = {"in": 0.10, "hit": 0.01, "out": 0.50, "batch_in": 0.05, "batch_out": 0.25}
DEV10_LOOPS = ["20260802_gpt54-high_moderation", "20260902_gpt54-high_topk1_run1", "20260902_gpt54-high_topk1_run2",
               "20260902_gpt54-high_topk1_run3", "20260901_gpt54-high_topk4_dev10", "20260902_gpt54-high_topk4_run1",
               "20260902_gpt54-high_topk4_run2", "20260902_gpt54-high_topk4_run3"]


def main() -> None:
    units = [u for d in rs.UNIT_DIRS.values() for u in rs.load_units(d) if u.get("usage")]
    ratio = sum(u["prompt_chars"] for u in units) / sum(u["usage"]["prompt_tokens"] for u in units)
    print(f"saved DeepSeek calls with usage: {len(units)}; {ratio:.2f} characters per prompt token")
    print(f"annotation prompt tokens: max {max(u['usage']['prompt_tokens'] for u in units):,}")
    print(f"completion tokens (thinking + answer): max {max(u['usage']['completion_tokens'] for u in units):,}")

    original = len(Path(rs.RUN / "inputs/initial_guidelines.txt").read_text(encoding="utf-8"))
    # Everything in the largest dev10 prompt except the guideline: template plus one document (an overestimate).
    template = max(u["prompt_chars"] for u in units) - original
    finals = max(len(p.read_text(encoding="utf-8")) for p in rs.ROOT.glob("outputs/ncbi_disease/2026*/final/final_guidelines.txt"))
    valid_doc = max(len(p.read_text(encoding="utf-8")) for p in rs.ROOT.glob("data/datasets/ncbi_disease/valid/*.json"))
    analysis = max(len(p.read_text(encoding="utf-8")) for name in DEV10_LOOPS
                   for p in (rs.ROOT / "outputs/ncbi_disease" / name / "rounds").glob("iteration_*/*.txt")
                   if p.name in ("infer_discrepancy_patterns.txt", "generate_moderation_principle.txt",
                                 "refine_guidelines.txt"))
    for label, chars in (("valid100 annotation, refined guideline (upper estimate)", template + finals + valid_doc),
                         ("loop analysis call, largest saved dev10 prompt", analysis)):
        print(f"{label}: {chars:,} chars = {chars / ratio:,.0f} tokens at {ratio:.2f} chars/token, "
              f"{chars / 2:,.0f} at 2 chars/token; {chars / 2 / THRESHOLD:.0%} of the threshold at most")

    on = [u for u in rs.load_units(rs.UNIT_DIRS["run"]) if u["arm"] == "B_on"]
    ds = st.mean(rs.cost_jpy(u["usage"], peak=False) for u in on)

    def haiku(u, batch=False):
        us = u["usage"]
        hit = us.get("prompt_cache_hit_tokens", 0) or 0
        miss = us["prompt_tokens"] - hit
        if batch:
            usd = (us["prompt_tokens"] * HAIKU["batch_in"] + us["completion_tokens"] * HAIKU["batch_out"]) / 1e6
        else:
            usd = (miss * HAIKU["in"] + hit * HAIKU["hit"] + us["completion_tokens"] * HAIKU["out"]) / 1e6
        return usd * rs.JPY_PER_USD

    print(f"\nper thinking-on annotation call, same token counts as DeepSeek used ({len(on)} calls):")
    print(f"  DeepSeek off-peak JPY {ds:.3f}, peak JPY {2 * ds:.3f}")
    print(f"  Haiku 5.5 standard JPY {st.mean(haiku(u) for u in on):.3f}, Batch API JPY "
          f"{st.mean(haiku(u, True) for u in on):.3f}")
    print("  Haiku's own thinking length and tokenizer differ; only a measured run gives its real per-call cost")


if __name__ == "__main__":
    main()
