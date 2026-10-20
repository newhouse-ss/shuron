"""Offline token and cost estimates (no API calls).

Part 1, Azure GPT-5.4: the R3-minus-FALDH check (design: todo-temp/r4-attribution/isolation/20261016_r3_minus_faldh_design.md),
priced from the measured usage of the same kind of call on the same document.

Part 2, DeepSeek flash: per-unit and whole-plan token estimates.
  - Input tokens: prompts are rendered offline with the real templates, then converted to tokens with the
    chars-per-token ratio measured on the saved GPT-5.4 units (DeepSeek's tokenizer may differ; assumption).
  - Visible output tokens (thinking off): JSON size of the saved GPT-5.4 annotation outputs per annotation,
    times the gold entity count of each document (assumption: about one prediction per gold entity).
  - cap64k: every call emits 64,000 output tokens, the cap used for GPT-5.4; a hard bound only if the same
    cap is set on DeepSeek.
  - Thinking on: no DeepSeek usage has ever been saved. As a stand-in scenario, each call is assumed to emit as
    many output tokens as GPT-5.4 high did on the saved full-guideline annotation units (mean and max).
    This is an assumption, to be replaced by the probe's measurement.

Prices: Azure GPT-5.4 from azurespeed.com (East US 2, effective 2026-03-01); DeepSeek from
api-docs.deepseek.com/quick_start/pricing (deepseek-flash, read 2026-10-16). FX from open.er-api.com,
2026-10-16 00:02 UTC.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
UNITS = [ROOT / "todo-temp/r4-attribution/isolation/units", ROOT / "todo-temp/r4-attribution/isolation/units_c3minus",
         ROOT / "todo-temp/r4-attribution/nontarget/units"]
JPY_PER_USD = 158.086954
AZURE = {"Global Standard": (2.50, 15.00), "Data Zone Standard": (2.75, 16.50)}  # USD per 1M (input, output)
DS_OFF = {"miss": 0.15, "hit": 0.003, "out": 0.60}  # USD per 1M, off-peak; peak is 2x
LOOP_ITERATIONS = 4  # largest iteration count among completed NCBI loops in outputs/ncbi_disease
REPLICATES = 3
OUTCFG = OutputConfiguration(include_rationale=True, include_guideline_section=True)


class Capture:
    def __init__(self):
        self.prompt = ""
        self.last_usage = {}

    def complete(self, task, prompt):
        self.prompt = prompt
        return '{"annotations": []}'


entities = [EntityDefinition(name=n) for n in
            json.loads((RUN / "inputs/entity_schema.json").read_text(encoding="utf-8"))]
manifest = {d["filename"]: d for d in json.loads(
    (RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))}
snap4 = json.loads((RUN / "rounds/iteration_04/snapshot.json").read_text(encoding="utf-8"))
original = (RUN / "inputs/initial_guidelines.txt").read_text(encoding="utf-8")
GUIDE = {"c1_R3": snap4["guidelines_before"], "c3_R4": snap4["guidelines_after"]}


def render(text, guideline):
    cap = Capture()
    annotate_with_guidelines(text, guideline, entities, cap, "", output_configuration=OUTCFG)
    return cap.prompt


def usd_jpy(usd):
    return f"${usd:.2f} = JPY {usd * JPY_PER_USD:,.0f}"


units = []
for folder in UNITS:
    for f in sorted(folder.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("usage"):
            units.append(d)

# ---------------- calibration ----------------
print("== calibration on saved GPT-5.4 units ==")
ratios, vis_chars, n_ann = [], 0, 0
for u in units:
    cond = u["unit"].split("__")[0]
    if cond in GUIDE:
        doc = load_sampled_document(ROOT / manifest[u["doc"] if u["doc"].endswith(".json") else u["doc"] + ".json"]["path"])
        ratios.append(len(render(doc.text, GUIDE[cond])) / u["usage"]["input_tokens"])
    vis_chars += len(json.dumps(u["raw_response"], ensure_ascii=False))
    n_ann += len(u["raw_response"].get("annotations", []))
cpt = statistics.mean(ratios)
vis_tok_per_ann = vis_chars / n_ann / cpt
print(f"chars per input token: mean {cpt:.3f} (min {min(ratios):.3f}, max {max(ratios):.3f}, n={len(ratios)})")
print(f"visible output: {vis_chars} chars over {n_ann} annotations in {len(units)} units "
      f"-> {vis_tok_per_ann:.0f} tokens per annotation (assumes the same chars/token)")
full = [u["usage"]["output_tokens"] for u in units
        if u["unit"].split("__")[0] in ("c1_R3", "c3_R4", "c3_minus_faldh")]
think_mean, think_max = statistics.mean(full), max(full)
print(f"GPT-5.4 high output per full-guideline annotation call: n={len(full)} mean {think_mean:,.0f} "
      f"min {min(full):,} max {think_max:,}")

# ---------------- Part 1: Azure ----------------
print("\n== Part 1: Azure GPT-5.4, R3 minus named FALDH exclusion (10577908) ==")
def usage_of(cond, doc="10577908"):
    return [u["usage"] for u in units if u["unit"].startswith(f"{cond}__{doc}")]

r3 = usage_of("c1_R3")
r4m = usage_of("c3_minus_faldh")
r3_out = [x["output_tokens"] for x in r3]
r4m_out = [x["output_tokens"] for x in r4m]
print("measured R3 as-is:", r3_out, "input", r3[0]["input_tokens"])
print("measured R4 minus FALDH:", r4m_out, "input", r4m[0]["input_tokens"])
inp = r3[0]["input_tokens"]
plan_mean = 3 * statistics.mean(r3_out) + 5 * max(statistics.mean(r3_out), statistics.mean(r4m_out))
plan_high = 8 * max(r3_out + r4m_out)
plan_cap = 8 * 64000
fup_mean = 5 * max(statistics.mean(r3_out), statistics.mean(r4m_out))
fup_high = 5 * max(r3_out + r4m_out)
for name, (pin, pout) in AZURE.items():
    print(f"[{name} ${pin}/${pout} per 1M]")
    for label, calls, out in (("main 8 calls, estimate", 8, plan_mean), ("main 8 calls, high end of measured range", 8, plan_high),
                              ("main 8 calls, hard cap 64k each", 8, plan_cap),
                              ("follow-up 5 calls, estimate", 5, fup_mean), ("follow-up 5 calls, high end", 5, fup_high)):
        usd = calls * inp * pin / 1e6 + out * pout / 1e6
        print(f"  {label}: input {calls * inp:,} output {out:,.0f} -> {usd_jpy(usd)}")

# ---------------- Part 2: DeepSeek ----------------
print("\n== Part 2: DeepSeek flash, off-peak prices (peak = 2x) ==")


def annotate_cost(docs, guideline, scenario, cache=True):
    """docs: list of SampledDocument. Returns (calls, miss, hit, out)."""
    miss = hit = out = 0.0
    for i, doc in enumerate(docs):
        prompt = render(doc.text, guideline)
        total = len(prompt) / cpt
        prefix = prompt.index(doc.text) / cpt  # guideline and template come before the document
        if cache and i > 0:
            hit += prefix
            miss += total - prefix
        else:
            miss += total
        visible = len(doc.gold_annotations) * vis_tok_per_ann
        out += {"off": visible, "on_mean": visible + think_mean, "on_max": visible + think_max, "cap64k": 64000}[scenario]
    return len(docs), miss, hit, out


def refine_cost(scenario):
    """3 refinement calls per iteration, sizes averaged over the 4 saved 08/02 iterations."""
    miss = out = 0.0
    for i in range(1, 5):
        s = json.loads((RUN / f"rounds/iteration_{i:02d}/snapshot.json").read_text(encoding="utf-8"))
        miss += sum(len(p) for p in s["prompts"].values()) / cpt
        visible = (len(s["discrepancy_insight"]) + len(s["moderation_principle"]) + len(s["guidelines_after"])) / cpt
        out += {"off": visible, "on_mean": visible + 3 * think_mean, "on_max": visible + 3 * think_max,
                "cap64k": 3 * 64000}[scenario]
    return 3, miss / 4, 0.0, out / 4


def price(c):
    calls, miss, hit, out = c
    return (miss * DS_OFF["miss"] + hit * DS_OFF["hit"] + out * DS_OFF["out"]) / 1e6


def add(*cs):
    return tuple(sum(x[i] for x in cs) for i in range(4))


def scale(c, k):
    return tuple(x * k for x in c)


valid = [load_sampled_document(p) for p in sorted((ROOT / "data/datasets/ncbi_disease/valid").glob("*.json"))]
dev10_names = json.loads((ROOT / "reproduction/dev_splits/ncbi_disease_dev10.json").read_text(encoding="utf-8"))["documents"]
dev10 = [load_sampled_document(ROOT / manifest[n]["path"]) for n in dev10_names]
probe_doc = [d for d in dev10 if d.filename == "10577908.json"]
refined = snap4["guidelines_after"]  # size proxy for a refined guideline
print(f"valid100: {len(valid)} docs, {sum(len(d.gold_annotations) for d in valid)} gold; "
      f"dev10: {len(dev10)} docs, {sum(len(d.gold_annotations) for d in dev10)} gold")
print(f"guideline chars: original {len(original):,}, refined proxy (08/02 R4) {len(refined):,}")

rows = []
for sc in ("off", "on_mean", "on_max", "cap64k"):
    v_orig = annotate_cost(valid, original, sc)
    v_ref = annotate_cost(valid, refined, sc)
    d_orig = annotate_cost(dev10, original, sc)
    d_ref = annotate_cost(dev10, refined, sc)
    ref = refine_cost(sc)
    loop = add(d_orig, scale(add(ref, d_ref), LOOP_ITERATIONS))
    loop_with_valid = add(loop, v_ref)
    rows.append((sc, {"valid100 once, original guideline": v_orig,
                      "valid100 once, refined-size guideline": v_ref,
                      "valid100 once, no cache": annotate_cost(valid, original, sc, cache=False),
                      "dev10 once, original guideline": d_orig,
                      f"one loop ({LOOP_ITERATIONS} iterations, dev10)": loop,
                      "one loop + valid100 of its final guideline": loop_with_valid}))

for sc, items in rows:
    print(f"\n[scenario {sc}]")
    for k, c in items.items():
        print(f"  {k}: calls {c[0]:.0f}, input miss {c[1]:,.0f}, hit {c[2]:,.0f}, output {c[3]:,.0f} "
              f"-> off-peak {usd_jpy(price(c))}, peak {usd_jpy(2 * price(c))}")

print("\n== whole plan ==")
off, on_mean, on_max, cap = (dict(r[1]) for r in rows)
probe_off = annotate_cost(probe_doc, original, "off")
probe_on = {"on_mean": annotate_cost(probe_doc, original, "on_mean"),
            "on_max": annotate_cost(probe_doc, original, "on_max"),
            "cap64k": annotate_cost(probe_doc, original, "cap64k")}
for sc, chosen in (("on_mean", on_mean), ("on_max", on_max), ("off", off), ("cap64k", cap)):
    on = on_mean if sc == "off" else chosen  # stability arm B is thinking on in every plan
    stability = add(scale(probe_off, 2), scale(probe_on["on_mean" if sc == "off" else sc], 2),
                    scale(off["dev10 once, original guideline"], 5), scale(on["dev10 once, original guideline"], 5))
    plan = {
        "1 stability (4-call probe + 2 arms x 5 x dev10)": stability,
        "2 accuracy (valid100 x 3, original guideline)": scale(chosen["valid100 once, original guideline"], 3),
        f"3 baseline loop x {REPLICATES} + valid100 each": scale(chosen["one loop + valid100 of its final guideline"], REPLICATES),
        f"4 Scheme A loop x {REPLICATES} + valid100 each": scale(chosen["one loop + valid100 of its final guideline"], REPLICATES),
        f"5 Scheme B loop x {REPLICATES} + valid100 each": scale(chosen["one loop + valid100 of its final guideline"], REPLICATES),
    }
    total = add(*plan.values())
    print(f"\n[steps 2-5 with scenario {sc}; step 1 arm B always thinking on ({'on_mean' if sc == 'off' else sc})]")
    for k, c in list(plan.items()) + [("TOTAL", total)]:
        print(f"  {k}: calls {c[0]:.0f}, input {c[1] + c[2]:,.0f} (miss {c[1]:,.0f}), output {c[3]:,.0f} "
              f"-> off-peak {usd_jpy(price(c))}, peak {usd_jpy(2 * price(c))}")
