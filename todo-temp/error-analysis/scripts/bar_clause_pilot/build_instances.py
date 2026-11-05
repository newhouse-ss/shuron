"""Instance table, section groups and no-prediction lookup for one changed guideline (2026-11-05). Offline, no API, stdlib only.

For one changed guideline (default "top-4 loop07") against the 19 runs with the original guideline, every instance whose
difference d = y - p is non-zero (same definition and counting rule as count_workload.py):
  instance : a gold mention (doc, start, end, label), or a no-gold prediction position (doc, start, end, label) from `extra` rows;
  y        : 1 if this run labels the gold mention right (strict) / makes the no-gold prediction, else 0;
  p        : share of the 19 original runs that do the same.
Five categories: gold_now_right, gold_now_wrong_with_prediction, gold_now_unlabelled, nogold_new_prediction,
nogold_dropped_prediction. The first, second and fourth have a prediction in this run; the third and fifth do not.

Linking a prediction to an instance (link_status in the instances csv):
  linked          the scorer's own pairing in prediction_index.jsonl (scoring.paired_gold): the correct prediction with the same
                  span and label (gold_now_right), the prediction paired to the gold (gold_now_wrong_...), the `extra` prediction
                  at the same span and label (nogold_new_prediction);
  overlap_unique  a gold with no paired prediction (scorer state `unpaired`) that exactly one prediction of this run overlaps
                  according to scoring.all_gold_overlaps; that prediction is the link;
  unlinked        none of the above (no overlap, or two or more overlapping predictions). No "first overlapping prediction" rule.

Citations (mechanical only, no semantic judgment): each cited_section string is split at ';' (outside parentheses) into
references. A reference is a section number (3, 1b, 1b(a), 1.2(d)) or "Example N" with the text that follows it up to the next
reference; its scope is given by the words before it ("What NOT to Annotate", "Pending Annotation Review", "Precedence",
"Examples", or "Do not annotate" in the same segment), else "What to Annotate" is assumed (`scope_assumed`). Each reference is
looked up only in the guideline text the run used (1-based lines of that text). Resolution order, fixed before any run:
  (a) title_exact     the reference text contains the title of a heading / bold run-in paragraph title / numbered item of the
                      guideline (case-insensitive, punctuation and whitespace normalised, whole words);
  (b) title_keywords  else, keywords of a title = its words of length >= 4 minus STOPWORDS; the title is chosen when at least
                      MIN_KEYWORDS of its keywords occur as words in the reference text and no other title also reaches that;
                      two or more titles reaching it = title_ambiguous (all kept);
  (c) section_only    else the section number: 0 lines = unresolved, 2 or more = ambiguous.
A title match may land in another list than the assumed scope (`scope_changed`). Groups are keyed by the finest resolved line.
An instance citing several items appears in each group. The title rules are applied to the changed guideline only; the
no-prediction lookup resolves the original runs' citations against the original guideline by section number alone.

Inputs (all under todo-temp/error-analysis/outputs/):
  error_rows.csv, 20261030_rationale_audit/{prediction_index.jsonl, run_manifest.json, guidelines/<sha>.txt, documents/<doc>.txt},
  bar_attribution.json, bar_clause_pilot/count_workload_output.txt.
Outputs (outputs/bar_clause_pilot/; <prefix> = loop07 for the default, else <method>_<loop>):
  <prefix>_instances.csv, <prefix>_section_groups.csv, <prefix>_noprediction_lookup.csv, build_instances_output.txt
  (output.txt gets the suffix _<prefix> for a non-default guideline).
Usage: python -I build_instances.py [--guideline "top-4 loop07"] [--prefix loop07] [--outdir DIR]
"""
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]            # todo-temp/error-analysis
REPO = HERE.parents[1]
OUT = HERE / "outputs"
AUDIT = OUT / "20261030_rationale_audit"
PILOT = OUT / "bar_clause_pilot"
DEFAULT = "top-4 loop07"
CATS = ["gold_now_right", "gold_now_wrong_with_prediction", "nogold_new_prediction",
        "gold_now_unlabelled", "nogold_dropped_prediction"]
WITH_PRED = CATS[:3]
EPS = 1e-9
CTX = 80

# Title-matching constants, fixed before the first run and not tuned on results. STOPWORDS: function words of length >= 4,
# plus the three words of the guideline template that occur in 6 or more of the 51 inventory titles (annotate 13, disease 11,
# mention(s) 6; no other word occurs in more than 4), which say nothing about which paragraph is meant.
MIN_KEYWORDS = 2
STOPWORDS = frozenset("""
annotate annotated annotation annotations disease diseases mention mentions
that this these those with within without from into when where which what than then they their there have been were will
also only each both such some more other over under between upon does used using shall should would could about after before
""".split())

ap = argparse.ArgumentParser()
ap.add_argument("--guideline", default=DEFAULT, help='changed guideline as "<method> <loop>", e.g. "top-4 loop07"')
ap.add_argument("--prefix", default=None, help="output file prefix (default loop07 for top-4 loop07, else <method>_<loop>)")
ap.add_argument("--outdir", default=None, help="output directory (default outputs/bar_clause_pilot; use another one for trial runs)")
args = ap.parse_args()
WRITE = Path(args.outdir) if args.outdir else PILOT
METHOD, LOOP = args.guideline.split()
PREFIX = args.prefix or (LOOP if METHOD == "top-4" else f"{METHOD.replace('-', '')}_{LOOP}")
SUMMARY = "build_instances_output.txt" if args.guideline == DEFAULT else f"build_instances_output_{PREFIX}.txt"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one_line(s):
    return " ".join(str(s).split())


# ---------------------------------------------------------------- runs, guidelines
rows = list(csv.DictReader(open(OUT / "error_rows.csv", encoding="utf-8")))
manifest = {m["run"]: m for m in json.load(open(AUDIT / "run_manifest.json", encoding="utf-8"))}
runs_csv = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig = sorted(r for r, v in runs_csv.items() if v[2] == "original")
assert len(orig) == 19, len(orig)
assert set(orig) == {r for r, m in manifest.items() if m["guideline_group"] == "original"}, "orig runs differ from manifest"
tgt_runs = [r for r, v in runs_csv.items() if v[:2] == (METHOD, LOOP) and v[2] != "original"]
assert len(tgt_runs) == 1, tgt_runs
TGT = tgt_runs[0]
assert TGT in manifest
orig_sha = {manifest[r]["guideline_sha256"] for r in orig}
assert len(orig_sha) == 1, orig_sha
ORIG_SHA = orig_sha.pop()
TGT_SHA = manifest[TGT]["guideline_sha256"]
assert TGT_SHA != ORIG_SHA


def load_guideline(sha):
    p = AUDIT / "guidelines" / f"{sha}.txt"
    text = p.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return text.split("\n")


TGT_LINES = load_guideline(TGT_SHA)
ORIG_LINES = load_guideline(ORIG_SHA)
tgt_final = REPO / manifest[TGT]["guideline_path"]
final_same = tgt_final.read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n") == TGT_LINES
orig_file_same = (REPO / "data/guidelines/ncbi_disease_guidelines.txt").read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n") == ORIG_LINES

# ---------------------------------------------------------------- guideline index and title inventory
PREFIX_WORD = {"NOT": "NOT", "EX": "Example", "PEND": "Pending", "PREC": "Precedence"}


def display(scope, ident):
    """Identifier shown in the CSVs: bare for What to Annotate, otherwise prefixed (NOT 4, Example 5, Pending 1, Precedence 2)."""
    return ident if scope == "WTA" else f"{PREFIX_WORD.get(scope, scope)} {ident}"


def scope_of_title(t):
    t = t.lower()
    for key, sc in (("what not to annotate", "NOT"), ("what to annotate", "WTA"), ("example", "EX"),
                    ("pending annotation review", "PEND"), ("precedence", "PREC")):
        if key in t:
            return sc
    return "OTHER"


def norm_text(s):
    """Lower case, every run of non-alphanumeric characters (punctuation, section signs, hyphens, markdown) -> one space."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def clean_title(t):
    return " ".join(t.replace("*", "").split()).rstrip(".:;, ").strip()


def item_title(rest):
    """Title of a numbered list item = its leading bold span ("" when the item does not start with bold text)."""
    if not rest.startswith("**"):
        return ""
    s = rest.rstrip()
    if s.endswith("**") and len(s) > 4:          # the whole line is bold (also repairs "**a **b**")
        return clean_title(s[2:-2])
    end = s.find("**", 2)
    return clean_title(s[2:end] if end > 0 else s[2:])


def build_index(lines):
    """-> (idx, inv, parent_of).
    idx: (scope, ident) -> [line numbers]; idents are heading numbers (### 3. / #### 1a. / **1b.**), numbered list items at
         column 0 of the NOT, Examples, Pending and Precedence blocks, and lettered bullets "- (a)" under the latest heading.
    inv: title inventory = every #### or ### heading, every bold run-in paragraph title at line start ("**Title.** text",
         "**1a. Title**"), every numbered list item of the four blocks (title = its leading bold span, "" if none).
    parent_of: line -> line of the enclosing ## block heading or ### section heading."""
    idx, inv, parent_of = collections.defaultdict(list), [], {}
    base, prec_level, head, sect = "OTHER", None, None, 0

    def add(no, scope, ident, title, kind):
        norm = norm_text(title)
        kw = {w for w in norm.split() if len(w) >= 4 and w not in STOPWORDS and not w.isdigit()}
        inv.append({"line": no, "scope": scope, "ident": ident, "title": title, "norm": norm, "kw": kw, "kind": kind})
        parent_of[no] = sect

    for no, line in enumerate(lines, 1):
        scope = "PREC" if prec_level else base
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level, title = len(m.group(1)), m.group(2)
            head = None
            if level <= 2:
                base, prec_level, sect = scope_of_title(title), None, no
                parent_of[no] = no
                continue
            if prec_level and level <= prec_level:
                prec_level = None
            if "precedence" in title.lower():
                prec_level = level
                sect = no
                add(no, "PREC", None, clean_title(title), "heading")
                continue
            scope = "PREC" if prec_level else base
            ident, ttl = None, title
            mm = re.match(r"(\d+(?:\.\d+)*[a-z]?)[.)]?\s+(.*)", title)
            if mm:
                ident = head = mm.group(1)
                ttl = mm.group(2)
                idx[(scope, ident)].append(no)
            if level == 3:
                sect = no
            add(no, scope, ident, clean_title(ttl), "heading")
            continue
        mm = re.match(r"^\*\*(\d+(?:\.\d+)*[a-z]?)[.)]\s+(.*?)\*\*", line)
        if mm:
            head = mm.group(1)
            idx[(scope, head)].append(no)
            add(no, scope, head, clean_title(mm.group(2)), "run-in")
            continue
        mm = re.match(r"^\*\*([^*]+?)\.\*\*\s", line)
        if mm:
            add(no, scope, None, clean_title(mm.group(1)), "run-in")
            continue
        mm = re.match(r"^(\d+)\.\s+(.*)", line)
        if mm and scope in ("NOT", "EX", "PEND", "PREC"):
            idx[(scope, mm.group(1))].append(no)
            add(no, scope, mm.group(1), item_title(mm.group(2)), "item")
            continue
        mm = re.match(r"^\s*[-*]\s*\(([a-z]{1,4})\)\s", line)
        if mm and head is not None and scope == "WTA":
            idx[(scope, f"{head}({mm.group(1)})")].append(no)
            parent_of[no] = sect
    return idx, inv, parent_of


# ---------------------------------------------------------------- citation parsing
MARKERS = [("NOT", re.compile(r"what\s+not\s+to\s+annotate", re.I)),
           ("WTA", re.compile(r"what\s+to\s+annotate", re.I)),
           ("PEND", re.compile(r"pending\s+annotation\s+review", re.I)),
           ("PREC", re.compile(r"precedence(?:\s+(?:between\s+overlapping\s+)?rules?)?", re.I))]
DONOT = re.compile(r"do\s+not\s+annotate", re.I)
EXAMPLE = re.compile(r"\bexamples?\s+#?(\d+(?:\s*(?:,|and|&)\s*\d+)*)", re.I)
NUM = re.compile(r"(?<![\w.])(?:§\s*)?(\d+(?:\.\d+)*)([a-z](?![a-z]))?((?:\([a-z]{1,4}\))*)(?!\w)", re.I)


def parse_citation(raw):
    """-> list of dicts (scope, ident, assumed, segment, text); duplicates of (scope, ident) inside one citation are dropped.
    text = the part of the segment from the reference's number (or "Example") to the next reference."""
    depth, d = [], 0
    for ch in raw:
        depth.append(d)
        d = d + 1 if ch == "(" else max(0, d - 1) if ch == ")" else d
    bounds, s = [], 0
    for i, ch in enumerate(raw):
        if ch == ";" and depth[i] == 0:
            bounds.append((s, i))
            s = i + 1
    bounds.append((s, len(raw)))
    refs, seen = [], set()
    for a, b in bounds:
        seg, dep = raw[a:b], depth[a:b]
        mask = list(seg)
        events = []
        for m in EXAMPLE.finditer(seg):
            for n in re.findall(r"\d+", m.group(1)):
                events.append((m.start(), 0, "ref", ("EX", n, False)))
            for i in range(m.start(), m.end()):
                mask[i] = " "
        masked = "".join(mask)
        wta_word = False
        for sc, rx in MARKERS:
            for m in rx.finditer(masked):
                if dep[m.start()] == 0:
                    events.append((m.start(), -1, "mark", sc))
                    wta_word = wta_word or sc == "WTA"
        donot = any(dep[m.start()] == 0 for m in DONOT.finditer(masked))
        for m in NUM.finditer(masked):
            if dep[m.start()] != 0:
                continue
            ident = (m.group(1) + (m.group(2) or "") + (m.group(3) or "")).lower()
            events.append((m.start(), 1, "num", ident))
        evs = sorted(events)
        cur = None
        for k, (pos, _, kind, val) in enumerate(evs):
            if kind == "mark":
                cur = val
                continue
            if kind == "ref":
                sc, ident, assumed = val
            elif cur:
                sc, ident, assumed = cur, val, False
            elif donot:
                sc, ident, assumed = "NOT", val, False
            else:
                sc, ident, assumed = "WTA", val, not wta_word
            end = len(seg)
            for j in range(k + 1, len(evs)):
                if evs[j][0] > pos:
                    if evs[j][2] == "mark" and all(e[2] == "mark" for e in evs[j:]):
                        continue                      # marker words after the last reference belong to it
                    end = evs[j][0]
                    break
            if (sc, ident) in seen:
                continue
            seen.add((sc, ident))
            refs.append({"scope": sc, "ident": ident, "assumed": assumed, "segment": seg.strip(), "text": seg[pos:end].strip()})
    return refs


def resolve_number(ref, lines, idx):
    """Section-number resolution -> dict(status, lines=[(no, text)], parent=(no, text)|None, note)."""
    hits = idx.get((ref["scope"], ref["ident"]), [])
    parent, note = None, ""
    m = re.match(r"^(.*?)\([a-z]{1,4}\)$", ref["ident"])
    if m:
        ph = idx.get((ref["scope"], m.group(1)), [])
        if len(ph) == 1:
            parent = (ph[0], lines[ph[0] - 1])
        if not hits:
            note = f"sub-item absent; parent {m.group(1)} " + (f"found at L{ph[0]}" if len(ph) == 1 else "not found uniquely")
    status = "resolved" if len(hits) == 1 else "ambiguous" if hits else "unresolved"
    return {"status": status, "lines": [(n, lines[n - 1]) for n in hits], "parent": parent, "note": note}


def title_match(text, inv):
    """-> (method, entries, matched keywords per entry) or None. (a) title_exact, (b) title_keywords / title_ambiguous."""
    nt = " " + norm_text(text) + " "
    exact = [e for e in inv if e["norm"] and f" {e['norm']} " in nt]
    exact = [e for e in exact if not any(o is not e and o["norm"] != e["norm"] and f" {e['norm']} " in f" {o['norm']} " for o in exact)]
    if exact:
        return ("title_exact" if len(exact) == 1 else "title_ambiguous"), exact, [[] for _ in exact]
    toks = set(nt.split())
    hits = [(e, sorted(e["kw"] & toks)) for e in inv if len(e["kw"] & toks) >= MIN_KEYWORDS]
    if len(hits) == 1:
        return "title_keywords", [hits[0][0]], [hits[0][1]]
    if hits:
        return "title_ambiguous", [e for e, _ in hits], [k for _, k in hits]
    return None


def resolve_ref(ref, lines, idx, inv, parent_of):
    """Number resolution plus title rules. -> dict(num, method, status, lines, entries, kws, scope_changed, parent, agrees)."""
    num = resolve_number(ref, lines, idx)
    tm = title_match(ref["text"], inv)
    if tm:
        method, ents, kws = tm
        status = "resolved" if len(ents) == 1 else "ambiguous"
        lns = [(e["line"], lines[e["line"] - 1]) for e in ents]
        same = [e["scope"] == ref["scope"] for e in ents]
        changed = "no" if all(same) else "yes" if not any(same) else "partial"
        agrees = "n/a"
        if num["status"] == "resolved":
            agrees = "yes" if {parent_of.get(e["line"]) for e in ents} == {parent_of.get(num["lines"][0][0])} else "no"
    else:
        method, ents, kws, status, lns, changed, agrees = "section_only", [], [], num["status"], num["lines"], "no", "n/a"
    p = parent_of.get(lns[0][0]) if lns else None
    return {"num": num, "method": method, "status": status, "lines": lns, "entries": ents, "kws": kws, "scope_changed": changed,
            "agrees": agrees, "parent": (p, lines[p - 1]) if p else None}


TGT_IDX, TGT_INV, TGT_PAR = build_index(TGT_LINES)
ORIG_IDX, _, _ = build_index(ORIG_LINES)
LABEL = {}                                                  # line -> identifier shown for a group
for (sc_, id_), lns_ in TGT_IDX.items():
    for ln_ in lns_:
        LABEL.setdefault(ln_, display(sc_, id_))
for e_ in TGT_INV:
    LABEL.setdefault(e_["line"], e_["title"] or f"L{e_['line']}")

# ---------------------------------------------------------------- states per run (same convention as count_workload.py)
gstate = collections.defaultdict(dict)      # run -> gold -> kind
gtext, gctx = {}, {}
extra = collections.defaultdict(dict)       # run -> (doc, start, end, label) -> text
extra_ctx = {}
for r in rows:
    if r["gold_start"]:
        g = (r["doc"], int(r["gold_start"]), int(r["gold_end"]), r["gold_label"])
        assert g not in gstate[r["run"]], "two rows for one gold in one run"
        gtext[g] = r["gold_text"]
        gctx.setdefault(g, r["context"])
        gstate[r["run"]][g] = r["kind"]
    if r["kind"] == "extra":
        e = (r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"])
        extra[r["run"]][e] = r["pred_text"]
        extra_ctx.setdefault(e, r["context"])
orig_extra_text = {}
for o in orig:
    orig_extra_text.update(extra[o])

# ---------------------------------------------------------------- predictions of the 30 runs
pred_by_run = collections.defaultdict(list)
for line in open(AUDIT / "prediction_index.jsonl", encoding="utf-8"):
    p = json.loads(line)
    pred_by_run[p["run"]].append(p)
assert set(pred_by_run) == set(manifest)


def pred_maps(run):
    at = collections.defaultdict(list)      # (kind, doc, start, end, label) -> rows, for correct / extra
    paired = collections.defaultdict(list)  # (doc, start, end, label) of paired gold -> rows
    for p in pred_by_run[run]:
        if p["kind"] in ("correct", "extra"):
            at[(p["kind"], p["doc"], p["start"], p["end"], p["pred_label"])].append(p)
        for g in p["scoring"]["paired_gold"]:
            paired[(p["doc"], g["start"], g["end"], g["label"])].append(p)
    return at, paired


MAPS = {run: pred_maps(run) for run in [TGT] + orig}

# sanity: `extra` rows of error_rows equal the `extra` predictions of prediction_index in these 20 runs
extra_mismatch = []
for run in [TGT] + orig:
    a = set(extra[run])
    b = {(p["doc"], p["start"], p["end"], p["pred_label"]) for p in pred_by_run[run] if p["kind"] == "extra"}
    if a != b:
        extra_mismatch.append((run, len(a), len(b)))

# ---------------------------------------------------------------- instances
instances = []


def add(cat, kind, pos, text, n, d, tstate):
    instances.append({"category": cat, "kind": kind, "pos": pos, "text": text, "n": n, "d": d, "tstate": tstate})


for g, t in gtext.items():
    n = sum(g not in gstate[o] for o in orig)
    st = gstate[TGT].get(g)
    d = (1 if st is None else 0) - n / 19
    if abs(d) <= EPS:
        continue
    cat = "gold_now_right" if st is None else "gold_now_unlabelled" if st == "missed" else "gold_now_wrong_with_prediction"
    add(cat, "gold", g, t, n, d, "right" if st is None else st)
for e in set(orig_extra_text) | set(extra[TGT]):
    n = sum(e in extra[o] for o in orig)
    made = e in extra[TGT]
    d = (1 if made else 0) - n / 19
    if abs(d) <= EPS:
        continue
    add("nogold_new_prediction" if made else "nogold_dropped_prediction", "nogold", e,
        extra[TGT].get(e) or orig_extra_text[e], n, d, "extra" if made else "not_predicted")
instances.sort(key=lambda i: (CATS.index(i["category"]), -abs(i["d"]), i["pos"][0], i["pos"][1], i["pos"][2], i["pos"][3]))

# ---------------------------------------------------------------- context from the document text
DOCS = {}


def doc_text(doc):
    if doc not in DOCS:
        with open(AUDIT / "documents" / f"{doc}.txt", encoding="utf-8", newline="") as f:
            DOCS[doc] = f.read()
    return DOCS[doc]


ctx_fallback = []


def context(inst):
    doc, s, e = inst["pos"][:3]
    tx = doc_text(doc)
    if tx[s:e] != inst["text"]:
        ctx_fallback.append((doc, s, e, inst["text"], tx[s:e]))
        key = inst["pos"]
        return one_line(gctx.get(key) or extra_ctx.get(key) or "")
    return one_line(tx[max(0, s - CTX):s] + "[[" + tx[s:e] + "]]" + tx[e:e + CTX])


# ---------------------------------------------------------------- link target predictions and parse citations
at_t, paired_t = MAPS[TGT]
overlap_index_mismatch = []
for inst in instances:
    doc, s, e, lab = inst["pos"]
    inst["linked"], inst["overlap_preds"] = [], []
    if inst["category"] == "gold_now_right":
        inst["linked"] = [p for p in at_t.get(("correct", doc, s, e, lab), [])
                          if any((g["start"], g["end"], g["label"]) == (s, e, lab) for g in p["scoring"]["paired_gold"])]
    elif inst["category"] == "gold_now_wrong_with_prediction":
        inst["linked"] = paired_t.get((doc, s, e, lab), [])
    elif inst["category"] == "nogold_new_prediction":
        inst["linked"] = at_t.get(("extra", doc, s, e, lab), [])
    inst["has_pred"] = inst["category"] in WITH_PRED
    if not inst["has_pred"]:
        inst["link_status"] = "no_prediction"
    elif inst["linked"]:
        inst["link_status"] = "linked"
    else:
        inst["link_status"] = "unlinked"
        if inst["kind"] == "gold":
            # predictions of this run that the scorer lists as overlapping this gold (all_gold_overlaps)
            ov, claimed = [], set()
            for p in pred_by_run[TGT]:
                if p["doc"] != doc:
                    continue
                for g in p["scoring"]["all_gold_overlaps"]:
                    if (g["start"], g["end"], g["label"]) == (s, e, lab):
                        ov.append(p)
                        claimed |= set(g["overlapping_prediction_indices"])
            if claimed != {p["prediction_index"] for p in ov}:       # the scorer's own index list must name the same predictions
                overlap_index_mismatch.append((doc, s, e, sorted(claimed), [p["prediction_index"] for p in ov]))
            inst["overlap_preds"] = ov
            if len(ov) == 1:
                inst["linked"], inst["link_status"] = ov, "overlap_unique"
    cites = [p["cited_section"] for p in inst["linked"]]
    inst["cited_raw"] = " || ".join(cites)
    inst["rationale"] = " || ".join(one_line(p["raw_rationale"]) for p in inst["linked"])
    refs, seen = [], set()
    for c in cites:
        for r in parse_citation(c):
            if (r["scope"], r["ident"]) not in seen:
                seen.add((r["scope"], r["ident"]))
                r["res"] = resolve_ref(r, TGT_LINES, TGT_IDX, TGT_INV, TGT_PAR)
                refs.append(r)
    inst["refs"] = refs
    inst["context"] = context(inst)
    inst["overlap_note"] = [f"{p['pred_label']} {p['start']}-{p['end']} {p['pred_text']!r} (scorer kind {p['kind']}; paired to "
                            f"{[g['text'] for g in p['scoring']['paired_gold']]}; cited {p['cited_section']!r})"
                            for p in inst["overlap_preds"]]

# ---------------------------------------------------------------- instances csv
f_inst = WRITE / f"{PREFIX}_instances.csv"


def lines_str(lns):
    return "|".join(f"L{n}" for n, _ in lns) or "-"


def per_ref(i, fn):
    return " | ".join(fn(r) for r in i["refs"])


with open(f_inst, "w", encoding="utf-8", newline="") as f:
    cols = ["category", "doc", "start", "end", "text", "gold_label", "nogold_label", "n_orig_of_19", "d", "target_state",
            "link_status", "n_linked_predictions", "target_pred_label", "target_pred_start", "target_pred_end",
            "target_pred_text", "overlap_prediction_info", "cited_section_raw", "parsed_references", "reference_text",
            "resolved_lines", "resolution_status", "sub_item_line", "sub_item_title", "sub_method", "scope_changed",
            "finest_item", "scope_assumed", "raw_rationale", "context"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for i in instances:
        doc, s, e, lab = i["pos"]
        p = i["linked"][0] if i["linked"] else None
        w.writerow({
            "category": i["category"], "doc": doc, "start": s, "end": e, "text": i["text"],
            "gold_label": lab if i["kind"] == "gold" else "", "nogold_label": lab if i["kind"] == "nogold" else "",
            "n_orig_of_19": i["n"], "d": f"{i['d']:.4f}", "target_state": i["tstate"], "link_status": i["link_status"],
            "n_linked_predictions": len(i["linked"]) if i["has_pred"] else "",
            "target_pred_label": p["pred_label"] if p else "", "target_pred_start": p["start"] if p else "",
            "target_pred_end": p["end"] if p else "", "target_pred_text": p["pred_text"] if p else "",
            "overlap_prediction_info": " || ".join(i["overlap_note"]),
            "cited_section_raw": i["cited_raw"],
            "parsed_references": per_ref(i, lambda r: display(r["scope"], r["ident"])),
            "reference_text": per_ref(i, lambda r: r["text"]),
            "resolved_lines": per_ref(i, lambda r: f"{display(r['scope'], r['ident'])}={lines_str(r['res']['num']['lines'])}"),
            "resolution_status": per_ref(i, lambda r: f"{display(r['scope'], r['ident'])}:{r['res']['num']['status']}"),
            "sub_item_line": per_ref(i, lambda r: lines_str(r["res"]["lines"]) if r["res"]["method"] != "section_only" else "-"),
            "sub_item_title": per_ref(i, lambda r: " / ".join(e["title"] or f"L{e['line']}" for e in r["res"]["entries"]) or "-"),
            "sub_method": per_ref(i, lambda r: r["res"]["method"]),
            "scope_changed": per_ref(i, lambda r: r["res"]["scope_changed"]),
            "finest_item": per_ref(i, lambda r: lines_str(r["res"]["lines"]) + ("" if r["res"]["status"] == "resolved" else f" {r['res']['status']}")),
            "scope_assumed": " | ".join(display(r["scope"], r["ident"]) for r in i["refs"] if r["assumed"]),
            "raw_rationale": i["rationale"], "context": i["context"]})

# ---------------------------------------------------------------- section groups (keyed by the finest resolved line)
groups = collections.OrderedDict()
no_ref, unlinked = [], []
for i in instances:
    if not i["has_pred"]:
        continue
    if not i["linked"]:
        unlinked.append(i)
        continue
    if not i["refs"]:
        no_ref.append(i)
    for r in i["refs"]:
        res = r["res"]
        if res["status"] == "resolved":
            gk = ("L", res["lines"][0][0])
        elif res["status"] == "ambiguous":
            gk = ("A", tuple(n for n, _ in res["lines"]))
        else:
            gk = ("U", r["scope"], r["ident"], r["segment"])
        g = groups.setdefault(gk, {"ref": r, "members": [], "refs": []})
        if i not in g["members"]:
            g["members"].append(i)
        g["refs"].append(r)


def member_str(i):
    doc, s, e, _ = i["pos"]
    return f"{doc}:{s}-{e} {i['text']} {i['d']:+.2f}"


def group_row(ident, status, lines_txt, text, parent_sec, parent_head, members, raw_ref="", refs=(), others=""):
    pos = sum(m["d"] for m in members if m["d"] > 0)
    neg = sum(m["d"] for m in members if m["d"] < 0)
    cc = collections.Counter(m["category"] for m in members)
    mc = collections.Counter(r["res"]["method"] for r in refs)
    mem = sorted(members, key=lambda m: (-abs(m["d"]), m["pos"][0], m["pos"][1]))
    return {"identifier": ident, "status": status, "resolved_lines": lines_txt, "line_text": text, "parent_section": parent_sec,
            "parent_heading": parent_head, "raw_reference": raw_ref,
            "methods": "; ".join(f"{k}={v}" for k, v in sorted(mc.items())),
            "n_scope_assumed": sum(1 for r in refs if r["assumed"] and r["res"]["method"] == "section_only"),
            "n_scope_changed": sum(1 for r in refs if r["res"]["scope_changed"] != "no"),
            "other_scope_candidates": others,
            "n_instances": len(members), "sum_positive_d": f"{pos:.4f}", "sum_negative_d": f"{neg:.4f}",
            "n_documents": len({m["pos"][0] for m in members}),
            "n_strings": len({m["text"].strip().casefold() for m in members}),
            "category_counts": "; ".join(f"{c}={cc[c]}" for c in CATS if cc[c]),
            "members": " | ".join(member_str(m) for m in mem), "_abs": pos - neg}


grows = []
for gk, g in groups.items():
    r = g["ref"]
    res = r["res"]
    parent_sec = f"L{res['parent'][0]}: {res['parent'][1]}" if res["parent"] else ""
    parent_head = f"L{res['num']['parent'][0]}: {res['num']['parent'][1]}" if res["num"]["parent"] and res["method"] == "section_only" else ""
    text = " || ".join(f"L{n}: {t}" for n, t in res["lines"]) or res["num"]["note"]
    if gk[0] == "L":
        ident = LABEL.get(gk[1], f"L{gk[1]}")
        others = ""
        n_ass = sum(1 for x in g["refs"] if x["assumed"] and x["res"]["method"] == "section_only")
        if n_ass:
            sc_id = [k for k, v in TGT_IDX.items() if gk[1] in v]
            if sc_id and sc_id[0][0] == "WTA":
                others = "; ".join(f"{display(sc, sc_id[0][1])}=L{TGT_IDX[(sc, sc_id[0][1])][0]}" for sc in ("NOT", "EX", "PEND", "PREC")
                                   if (sc, sc_id[0][1]) in TGT_IDX)
    elif gk[0] == "A":
        ident, others = "ambiguous " + "|".join(f"L{n}" for n in gk[1]), ""
    else:
        ident, others = display(r["scope"], r["ident"]), ""
    grows.append(group_row(ident, res["status"], lines_str(res["lines"]), text, parent_sec, parent_head, g["members"],
                           raw_ref=r["segment"] if res["status"] == "unresolved" else "", refs=g["refs"], others=others))
if no_ref:
    grows.append(group_row("(no parsable reference)", "no_reference", "-", "", "", "", no_ref))
if unlinked:
    grows.append(group_row("(unlinked)", "unlinked", "-", "no paired prediction and no unique overlapping prediction", "", "", unlinked))
grows.sort(key=lambda r: (-r["_abs"], r["identifier"]))
f_groups = WRITE / f"{PREFIX}_section_groups.csv"
gcols = ["identifier", "status", "resolved_lines", "line_text", "parent_section", "parent_heading", "raw_reference", "methods",
         "n_scope_assumed", "n_scope_changed", "other_scope_candidates", "n_instances", "sum_positive_d", "sum_negative_d",
         "n_documents", "n_strings", "category_counts", "members"]
with open(f_groups, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=gcols, extrasaction="ignore")
    w.writeheader()
    w.writerows(grows)

# ---------------------------------------------------------------- no-prediction lookup (original runs' citations, original guideline)
f_look = WRITE / f"{PREFIX}_noprediction_lookup.csv"
look_n_mismatch = []
numberless = collections.Counter()
with open(f_look, "w", encoding="utf-8", newline="") as f:
    cols = ["category", "doc", "start", "end", "text", "gold_label", "nogold_label", "d", "n_orig_of_19",
            "n_orig_predictions_found", "original_cited_sections", "rationale_example_1", "rationale_example_2",
            "rationale_example_3", "citations_resolved_in_original_guideline", "context"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for i in instances:
        if i["has_pred"]:
            continue
        doc, s, e, lab = i["pos"]
        found = []
        for o in orig:
            at_o, paired_o = MAPS[o]
            if i["category"] == "gold_now_unlabelled":
                ps = [p for p in at_o.get(("correct", doc, s, e, lab), [])
                      if any((g["start"], g["end"], g["label"]) == (s, e, lab) for g in p["scoring"]["paired_gold"])]
            else:
                ps = at_o.get(("extra", doc, s, e, lab), [])
            found.extend(ps[:1])
        if len(found) != i["n"]:
            look_n_mismatch.append((i["category"], i["pos"], i["n"], len(found)))
        cc = collections.Counter(p["cited_section"] for p in found)
        rats, seen = [], set()
        for p in found:
            r = one_line(p["raw_rationale"])
            if r not in seen:
                seen.add(r)
                rats.append(r)
        # section-number resolution only: the title rules are defined for the changed guideline; applied to the original
        # guideline they let the long example sentences of "Examples" capture generic words (see build_instances_output.txt)
        refcount = collections.OrderedDict()
        for p in found:
            refs_p = parse_citation(p["cited_section"])
            if not refs_p:
                numberless[p["cited_section"]] += 1
            for r in refs_p:
                ent = refcount.setdefault((r["scope"], r["ident"]), [r, 0, 0])
                ent[1] += 1
                ent[2] += r["assumed"]
        res_txt = []
        for (sc, idn), (r, k, k_assumed) in sorted(refcount.items(), key=lambda kv: -kv[1][1]):
            res = resolve_number(r, ORIG_LINES, ORIG_IDX)
            body = " || ".join(f"L{n}: {t}" for n, t in res["lines"]) if res["lines"] else res["note"] or "-"
            res_txt.append(f"{display(sc, idn)} [{res['status']}] x{k}{f' (scope assumed in {k_assumed})' if k_assumed else ''} -> {body}")
        w.writerow({"category": i["category"], "doc": doc, "start": s, "end": e, "text": i["text"],
                    "gold_label": lab if i["kind"] == "gold" else "", "nogold_label": lab if i["kind"] == "nogold" else "",
                    "d": f"{i['d']:.4f}", "n_orig_of_19": i["n"], "n_orig_predictions_found": len(found),
                    "original_cited_sections": " | ".join(f"{c!r} x{k}" for c, k in cc.most_common()),
                    "rationale_example_1": rats[0] if len(rats) > 0 else "", "rationale_example_2": rats[1] if len(rats) > 1 else "",
                    "rationale_example_3": rats[2] if len(rats) > 2 else "",
                    "citations_resolved_in_original_guideline": " ## ".join(res_txt), "context": i["context"]})

# ---------------------------------------------------------------- checks and summary
L = []
P = L.append
by_cat = {c: [i for i in instances if i["category"] == c] for c in CATS}
sd = lambda xs: sum(i["d"] for i in xs)
n_with = sum(len(by_cat[c]) for c in WITH_PRED)
no_gold_unlab, no_drop = by_cat["gold_now_unlabelled"], by_cat["nogold_dropped_prediction"]
all_refs = [(i, r) for i in instances for r in i["refs"]]

P(f"build_instances.py: {args.guideline} against the 19 original runs (offline, no API)")
P(f"target run: {TGT}")
P(f"target guideline snapshot sha256: {TGT_SHA}")
P(f"  identical to {manifest[TGT]['guideline_path']} after CRLF -> LF: {final_same}")
P(f"original guideline snapshot sha256: {ORIG_SHA}; identical to data/guidelines/ncbi_disease_guidelines.txt after CRLF -> LF: {orig_file_same}")
P(f"original runs: {len(orig)}; all 19 use the same snapshot (manifest guideline_sha256); instances with d != 0: {len(instances)}")
P("")
P("A. Instances by category (n | sum d | sum of positive d | sum of negative d)")
for c in CATS:
    xs = by_cat[c]
    P(f"   {c:32s} {len(xs):4d} | {sd(xs):+8.2f} | {sum(i['d'] for i in xs if i['d'] > 0):+8.2f} | {sum(i['d'] for i in xs if i['d'] < 0):+8.2f}")
P(f"   with a prediction in this run: {n_with}; without: {len(no_gold_unlab) + len(no_drop)}")
P("")

# check 1
wl = (OUT / "bar_clause_pilot" / "count_workload_output.txt").read_text(encoding="utf-8").split("\n")
m1 = [re.match(rf"^\s+{re.escape(args.guideline)}:\s+(\d+) \|\s+(\d+) \(([+-][\d.]+)\);", l) for l in wl]
m1 = [m for m in m1 if m][0]
ref_with, ref_without, ref_sum = int(m1.group(1)), int(m1.group(2)), float(m1.group(3))
my_without = len(no_gold_unlab) + len(no_drop)
my_sum = sd(no_gold_unlab) + sd(no_drop)
c1 = n_with == ref_with and my_without == ref_without and abs(round(my_sum, 1) - ref_sum) < 1e-9
line_b = {}
for l in wl:
    mm = re.match(r"^B\. (gold mentions|no-gold predictions) .*: (\d+) positions, summed difference ([+-][\d.]+)", l)
    if mm and args.guideline == DEFAULT:
        line_b[mm.group(1)] = (int(mm.group(2)), float(mm.group(3)))
if line_b:
    c1 = c1 and line_b["gold mentions"] == (len(no_gold_unlab), round(sd(no_gold_unlab), 1)) \
        and line_b["no-gold predictions"] == (len(no_drop), round(sd(no_drop), 1))
P(f"CHECK 1 counts vs count_workload_output.txt: {'PASS' if c1 else 'FAIL'}")
P(f"   with prediction {n_with} (file {ref_with}); without {my_without} (file {ref_without}); summed d without {my_sum:+.2f} (file {ref_sum:+.1f})")
P(f"   gold left unlabelled {len(no_gold_unlab)}, summed d {sd(no_gold_unlab):+.2f} (file {line_b.get('gold mentions')}); "
  f"no-gold dropped {len(no_drop)}, summed d {sd(no_drop):+.2f} (file {line_b.get('no-gold predictions')})")

# check 2
bars = json.load(open(OUT / "bar_attribution.json", encoding="utf-8"))["bars"]
c2 = True
P("CHECK 2 sum of d over gold instances of each label vs bar in bar_attribution.json (tolerance 0.05):")
for lab in ("SpecificDisease", "DiseaseClass", "Modifier"):
    mine = sum(i["d"] for i in instances if i["kind"] == "gold" and i["pos"][3] == lab)
    bar = bars[lab][args.guideline]
    ok = abs(mine - bar) <= 0.05
    c2 = c2 and ok
    P(f"   {lab:16s} sum d {mine:+.4f}  bar {bar:+.4f}  diff {mine - bar:+.2e}  {'ok' if ok else 'MISMATCH'}")
other_labels = sorted({i["pos"][3] for i in instances if i["kind"] == "gold"} - {"SpecificDisease", "DiseaseClass", "Modifier"})
P(f"   gold labels with d != 0 outside the three bars: {other_labels or 'none'}")
P(f"   -> {'PASS' if c2 else 'FAIL'}")

# check 3
n_paired = sum(1 for i in instances if i["link_status"] == "linked")
n_overlap = sum(1 for i in instances if i["link_status"] == "overlap_unique")
c3 = not unlinked and (n_overlap == 12 or args.guideline != DEFAULT)
P(f"CHECK 3 links of the {n_with} instances with a prediction: paired {n_paired}; overlap_unique {n_overlap}"
  f"{' (expected 12)' if args.guideline == DEFAULT else ''}; still unlinked {len(unlinked)} (expected 0) -> {'PASS' if c3 else 'FAIL'}")
for i in unlinked:
    P(f"   unlinked: {i['category']} {i['pos'][0]}:{i['pos'][1]}-{i['pos'][2]} {i['pos'][3]} {i['text']!r} d {i['d']:+.2f} "
      f"target state {i['tstate']}; overlapping predictions {len(i['overlap_preds'])}")
ou = [i for i in instances if i["link_status"] == "overlap_unique"]
if ou:
    kinds = collections.Counter(f"{i['linked'][0]['pred_label']}/scorer kind {i['linked'][0]['kind']}" for i in ou)
    P(f"   overlap_unique: scorer state of the gold {sorted({i['tstate'] for i in ou})}, summed d {sd(ou):+.2f}; "
      f"label / scorer kind of the linked predictions: {dict(kinds)}; "
      f"cited sections: {dict(collections.Counter(i['linked'][0]['cited_section'] for i in ou))}")
    P(f"   all_gold_overlaps agrees with overlapping_prediction_indices (same predictions, checked for every gold without a paired prediction): "
      f"{'yes' if not overlap_index_mismatch else 'NO ' + str(overlap_index_mismatch)}")
multi = [i for i in instances if len(i["linked"]) > 1]
P(f"   instances with more than one linked prediction: {len(multi)}")
P(f"   linked-prediction scorer kind by category: " + "; ".join(
    f"{c}: " + ",".join(f"{k}={v}" for k, v in sorted(collections.Counter(i['linked'][0]['kind'] for i in by_cat[c] if i['linked']).items()))
    for c in WITH_PRED))

# check 4 (section-number resolution, as before)
cnt = collections.Counter()
raw_unres = collections.Counter()
for i, r in all_refs:
    cnt[r["res"]["num"]["status"]] += 1
    if r["res"]["num"]["status"] == "unresolved":
        raw_unres[(display(r["scope"], r["ident"]), r["segment"])] += 1
nrefs = len(all_refs)
n_linked_inst = sum(1 for i in instances if i["has_pred"] and i["linked"])
P(f"CHECK 4 citation resolution by section number against the target guideline ({n_linked_inst} instances with a linked prediction, "
  f"{nrefs} references, one per distinct identifier per instance)")
P(f"   resolved {cnt['resolved']}, ambiguous {cnt['ambiguous']}, unresolved {cnt['unresolved']}; "
  f"citations with no parsable reference: {len(no_ref)}")
P(f"   references whose scope was assumed (no scope word, taken as the '### N.' heading of What to Annotate): "
  f"{sum(1 for _, r in all_refs if r['assumed'])} of {nrefs}")
for (idn, seg), k in raw_unres.most_common(10):
    P(f"   unresolved x{k}: {idn}   <- {seg!r}")
fc = collections.Counter(r["res"]["status"] for _, r in all_refs)
P(f"   final resolution (title rules first, then section number): resolved {fc['resolved']}, ambiguous {fc['ambiguous']}, unresolved {fc['unresolved']}")

# extra diagnostics
P("")
P("D. Other consistency checks")
P(f"   extra rows of error_rows.csv vs extra predictions of prediction_index.jsonl (target + 19 original runs): "
  f"{'equal' if not extra_mismatch else 'DIFFER ' + str(extra_mismatch)}")
P(f"   lookup: original predictions found at the position equal n_orig_of_19: "
  f"{'yes for all ' + str(my_without) if not look_n_mismatch else 'MISMATCH ' + str(look_n_mismatch[:5])}")
P(f"   lookup: cited_section strings of the original runs without any parsable reference (not resolved): "
  f"{sum(numberless.values())}" + (f", e.g. {list(numberless)[:3]}" if numberless else ""))
P(f"   context from document text (offsets agree with instance text): {len(instances) - len(ctx_fallback)} of {len(instances)}"
  + (f"; fallback to error_rows context for {ctx_fallback[:5]}" if ctx_fallback else ""))
P(f"   groups: {sum(1 for r in grows if r['status'] in ('resolved', 'ambiguous'))} resolved or ambiguous, "
  f"{sum(1 for r in grows if r['status'] == 'unresolved')} unresolved raw references, "
  f"{sum(1 for r in grows if r['status'] in ('no_reference', 'unlinked'))} pseudo rows (no_reference / unlinked)")

P("")
P("E. Ten largest groups by total |d| (identifier | status | line | sum positive d | sum negative d | documents | strings | instances | line text)")
for r in [r for r in grows if r["status"] in ("resolved", "ambiguous", "unresolved")][:10]:
    P(f"   {r['identifier'][:34]:34s} {r['status']:9s} {r['resolved_lines']:9s} {r['sum_positive_d']:>9s} {r['sum_negative_d']:>9s}  "
      f"{r['n_documents']:3d} docs  {r['n_strings']:3d} strings  {r['n_instances']:3d} inst   {r['line_text'][:60]}")

# ---- sub-item resolution report
P("")
P("F. Sub-item resolution (title rules; references counted once per instance and distinct identifier)")
P(f"   MIN_KEYWORDS = {MIN_KEYWORDS}; STOPWORDS = {sorted(STOPWORDS)}")
mc = collections.Counter(r["res"]["method"] for _, r in all_refs)
P("   references by method: " + ", ".join(f"{m} {mc[m]}" for m in ("title_exact", "title_keywords", "title_ambiguous", "section_only")) + f" (total {nrefs})")
tm_refs = [(i, r) for i, r in all_refs if r["res"]["method"] != "section_only"]
ag = collections.Counter(r["res"]["agrees"] for _, r in tm_refs)
P(f"   title matches whose line lies in the same section as the cited number: yes {ag['yes']}, no {ag['no']}, number not resolved to one line {ag['n/a']}")
sc_ = collections.Counter(r["res"]["scope_changed"] for _, r in all_refs)
so = [r for _, r in all_refs if r["res"]["method"] == "section_only"]
P(f"   section_only references: {len(so)}, of which scope assumed (no scope word, so the What to Annotate heading was taken): "
  f"{sum(1 for r in so if r['assumed'])}")
P(f"   scope changed by a title match (matched list differs from the assumed or explicit scope): yes {sc_['yes']}, partial {sc_['partial']}")


def agg_lines(refs_sel):
    """Distinct (reference text, cited identifier) -> list of instances."""
    ag_ = collections.OrderedDict()
    for i, r in refs_sel:
        ag_.setdefault((r["text"], display(r["scope"], r["ident"]), r["res"]["method"]), []).append((i, r))
    return ag_


def fmt_match(key, items):
    text, ident, method = key
    r = items[0][1]
    res = r["res"]
    tgt = " + ".join(f"L{e['line']} {(e['title'] or LABEL.get(e['line'], ''))[:48]!r}" for e in res["entries"])
    kws = " ; ".join(",".join(k) for k in res["kws"]) if method != "title_exact" else ""
    num = f"{ident}={lines_str(res['num']['lines'])}" if res["num"]["lines"] else f"{ident}=unresolved"
    return (f"   x{len(items):<3d} {text!r} -> {tgt}" + (f"  [keywords: {kws}]" if kws else "") +
            f"  | number-based {num} | scope {r['scope']}{'(assumed)' if r['assumed'] else ''}->"
            f"{','.join(sorted({e['scope'] for e in res['entries']}))} changed={res['scope_changed']} same_section={res['agrees']}")


for m in ("title_keywords", "title_ambiguous"):
    sel = [(i, r) for i, r in tm_refs if r["res"]["method"] == m]
    P(f"   {m}: {len(sel)} references, {len(agg_lines(sel))} distinct reference texts")
    for key, items in agg_lines(sel).items():
        P(fmt_match(key, items))
ex = collections.Counter()
for i, r in tm_refs:
    if r["res"]["method"] == "title_exact":
        ex[(r["res"]["entries"][0]["line"], r["res"]["scope_changed"], r["res"]["agrees"])] += 1
P(f"   title_exact: {mc['title_exact']} references by matched line (line, scope_changed, same_section): "
  + "; ".join(f"L{ln}{' ' + repr(LABEL.get(ln, '')[:24]) if ln in LABEL else ''} {sch}/{agr} x{k}" for (ln, sch, agr), k in sorted(ex.items())))
P("   references whose scope changed (distinct reference text; instances; assumed or explicit scope -> matched list; method; number-based line -> matched line):")
chg = [(i, r) for i, r in all_refs if r["res"]["scope_changed"] != "no"]
for key, items in agg_lines(chg).items():
    r = items[0][1]
    P(f"   x{len(items):<3d} {key[0]!r}: {r['scope']}{'(assumed)' if r['assumed'] else '(explicit)'} -> "
      f"{','.join(sorted({e['scope'] for e in r['res']['entries']}))}, {key[2]}, "
      f"{key[1]}={lines_str(r['res']['num']['lines'])} -> {lines_str(r['res']['lines'])}")
dis = [(i, r) for i, r in tm_refs if r["res"]["agrees"] == "no"]
P(f"   title matches in a different section than the cited number, not already listed as scope changes: "
  f"{sum(1 for i, r in dis if r['res']['scope_changed'] == 'no')}")
for key, items in agg_lines([(i, r) for i, r in dis if r["res"]["scope_changed"] == "no"]).items():
    r = items[0][1]
    P(f"   x{len(items):<3d} {key[0]!r}: {key[1]}={lines_str(r['res']['num']['lines'])} -> {lines_str(r['res']['lines'])} ({key[2]})")

P("")
P("G. Title inventory of the target guideline (line | list | number | kind | title | keywords)")
for e in TGT_INV:
    P(f"   L{e['line']:<4d}{e['scope']:5s}{e['ident'] or '-':8s}{e['kind']:8s}{e['title'][:70]!r} | {','.join(sorted(e['kw']))}")

P("")
P("H. Files (sha256)")
P(f"   input  error_rows.csv {sha256(OUT / 'error_rows.csv')}")
P(f"   input  prediction_index.jsonl {sha256(AUDIT / 'prediction_index.jsonl')}")
P(f"   input  run_manifest.json {sha256(AUDIT / 'run_manifest.json')}")
for fp in (f_inst, f_groups, f_look):
    P(f"   output {fp.name} {sha256(fp)}")
ALL_PASS = c1 and c2 and c3
P("")
P(f"OVERALL: checks 1-3 {'PASS' if ALL_PASS else 'NOT ALL PASS'}")
(WRITE / SUMMARY).write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
