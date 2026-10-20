"""Offline: how much of the 08/02 R4 annotation call can be shown identical to E1's.

1. Prompt templates: the run saved the three refinement prompts of every round. Render each
   current template with unique markers, split on the markers, and check that every static
   chunk appears verbatim in the saved prompt of every round.
2. Document text: compare the text E1 loaded with the text stored in the run's final record.
3. Guideline text: E1 condition c3_R4 vs snapshot guidelines_after of iteration_04.
4. E1 dry-run prompt: check it contains the R4 guideline and the document text verbatim.
No API calls.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()

print("== 1. refinement prompt templates vs saved prompts ==")
for name in ("infer_discrepancy_patterns", "generate_moderation_principle", "refine_guidelines"):
    fields = sorted(set(re.findall(r"\{(\w+)\}", PROMPT_TEMPLATES[name])))
    markers = {f: f"@@{f.upper()}@@" for f in fields}
    rendered = render_prompt(name, **markers)
    chunks = [c for c in re.split(r"@@\w+@@", rendered) if c.strip()]
    for it in range(1, 5):
        saved = (RUN / f"rounds/iteration_{it:02d}/{name}.txt").read_text(encoding="utf-8")
        missing = [c for c in chunks if c not in saved]
        print(f"  {name:30s} iter {it}: {len(chunks)} static chunks, {len(missing)} missing")
        for c in missing[:2]:
            print("     MISSING:", repr(c[:120]))

print("== 2. document text 8326491 ==")
manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
entry = next(d for d in manifest if d["filename"] == "8326491.json")
doc = load_sampled_document(ROOT / entry["path"])
print("  path:", entry["path"], " E1 text sha256", sha(doc.text)[:12], "chars", len(doc.text))
snap4 = json.loads((RUN / "rounds/iteration_04/snapshot.json").read_text(encoding="utf-8"))
for key in ("diagnostics_before", "diagnostics_after"):
    f = next(x for x in snap4[key]["files"] if x["filename"] == "8326491.json")
    dens = f["study_denotations"] + f["reference_denotations"]
    bad = [d for d in dens if doc.text[d["start"]:d["end"]] != d["text"]]
    print(f"  {key}: {len(dens)} saved spans, {len(bad)} whose text differs from E1 document at the same offsets")

print("== 3. guideline text ==")
snap = json.loads((RUN / "rounds/iteration_04/snapshot.json").read_text(encoding="utf-8"))
c3 = (ROOT / "todo-temp/r4-attribution/nontarget/conditions/c3_R4.txt").read_text(encoding="utf-8")
print("  c3_R4 == snapshot guidelines_after:", c3 == snap["guidelines_after"], sha(c3)[:12])

print("== 4. E1 dry-run prompt ==")
dry = (ROOT / "todo-temp/r4-attribution/nontarget/dry_run/c3_R4__8326491.txt").read_text(encoding="utf-8")
print("  contains R4 guideline verbatim:", snap["guidelines_after"] in dry)
print("  contains document text verbatim:", doc.text in dry)
print("  dry-run prompt sha256:", sha(dry)[:12], "chars", len(dry))

