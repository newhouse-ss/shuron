"""Instance table, section groups, no-prediction lookup and citation audit for the changed guidelines (2026-11-06). Offline, no API, stdlib only.

For a changed guideline (default "top-4 loop07"; "all" = the 11 changed guidelines) against the 19 runs with the original
guideline, every instance whose difference d = y - p is non-zero (same definition and counting rule as count_workload.py):
  instance : a gold mention (doc, start, end, label), or a no-gold prediction position (doc, start, end, label) from `extra` rows;
  y        : 1 if this run labels the gold mention right (strict) / makes the no-gold prediction, else 0;
  p        : share of the 19 original runs that do the same.
Five categories: gold_now_right, gold_now_wrong_with_prediction, gold_now_unlabelled, nogold_new_prediction,
nogold_dropped_prediction. The first, second and fourth have a prediction in this run; the third and fifth do not.

Linking a prediction to an instance (link_status in the instances csv):
  linked          the scorer's own pairing in prediction_index.jsonl (scoring.paired_gold);
  overlap_unique  a gold with no paired prediction (scorer state `unpaired`) that exactly one prediction of this run overlaps
                  according to scoring.all_gold_overlaps; that prediction is the link;
  unlinked        none of the above. No "first overlapping prediction" rule.

Citations (mechanical, no semantic judgment). The cited_section string is split at ';' (outside parentheses) into references.
A reference is a section number (3, 1b, 1.2(d), 1a(ii)(c)), a child index after "step"/"item" ("3.1 step 2(a)" = 3.1(2)(a)),
"Example N", "Principle N", or a number after a list name ("What NOT to Annotate", "Pending Annotation Review", "Precedence",
the guideline's own numbered `##` blocks). Numbers inside parentheses count only after Section/item/step/rule/principle words.
Its text runs from the number to the next reference. A number with no list name means a heading of "What to Annotate"
(scope assumed). Resolution order, each fixed before it was run:
  override           a row of outputs/bar_clause_pilot/citation_overrides.csv (guideline, raw_reference_text, line) wins over everything;
  (a) title_exact    the reference text contains the title of a heading / bold run-in paragraph title / numbered item
                     (case-insensitive, punctuation and whitespace normalised, whole words);
  (b) title_keywords else a title is chosen when at least MIN_KEYWORDS of its keywords (words of length >= 4 minus STOPWORDS)
                     occur in the reference text and no other title also reaches that; several = title_ambiguous (all kept);
                     titles of Examples items take part in (a) only;
  (c) section_only   else the section number looked up in the index of the guideline text the run used
                     (0 lines = unresolved, 2 or more = ambiguous).
References with an explicit list name other than What to Annotate (NOT, Pending, Precedence, Example, Principle, other block)
skip (a) and (b). Groups are keyed by the finest resolved line. An instance citing several items appears in each group.
Every distinct reference text is listed with its method in <prefix>_citation_audit.csv; the original-run citations of the lookup
files are listed in original_citation_audit.csv.

Inputs (under todo-temp/error-analysis/outputs/):
  error_rows.csv, 20261030_rationale_audit/{prediction_index.jsonl, run_manifest.json, guidelines/<sha>.txt, documents/<doc>.txt},
  bar_attribution.json, bar_clause_pilot/{count_workload_output.txt, citation_overrides.csv}.
Outputs (outputs/bar_clause_pilot/ or --outdir; <prefix> = <method>_<loop> without the dash, e.g. top4_loop07):
  <prefix>_instances.csv, <prefix>_section_groups.csv, <prefix>_noprediction_lookup.csv, <prefix>_citation_audit.csv,
  <prefix>_build_instances_output.txt; with --guideline all also original_citation_audit.csv and citation_audit_summary.txt.
  citation_overrides.csv is created with its header only when it does not exist; it is never overwritten.
Usage: python -I build_instances.py [--guideline "top-4 loop07"|all] [--prefix loop07] [--outdir DIR]
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
ALL_GUIDELINES = ["top-1 loop05", "top-1 loop07"] + [f"top-4 loop{n:02d}" for n in (1, 2, 4, 5, 6, 7, 8, 9, 10)]
CATS = ["gold_now_right", "gold_now_wrong_with_prediction", "nogold_new_prediction",
        "gold_now_unlabelled", "nogold_dropped_prediction"]
WITH_PRED = CATS[:3]
REF_CATS = ["override", "title_exact", "title_keywords", "title_ambiguous", "section_only_explicit", "section_only_assumed",
            "section_only_ambiguous", "unresolved"]
SAFE_CATS = {"override", "title_exact", "section_only_explicit"}      # not listed for manual verification
EPS = 1e-9
CTX = 80
OVERRIDE_HEADER = ["guideline", "raw_reference_text", "line"]

# Title-matching constants, fixed before the first run and not tuned on results. STOPWORDS: function words of length >= 4,
# plus the three words of the guideline template that occur in 6 or more of the 51 inventory titles of the first guideline
# examined (annotate 13, disease 11, mention(s) 6; no other word occurs in more than 4), which say nothing about which
# paragraph is meant.
MIN_KEYWORDS = 2
STOPWORDS = frozenset("""
annotate annotated annotation annotations disease diseases mention mentions
that this these those with within without from into when where which what than then they their there have been were will
also only each both such some more other over under between upon does used using shall should would could about after before
""".split())

ap = argparse.ArgumentParser()
ap.add_argument("--guideline", default=DEFAULT, help='changed guideline as "<method> <loop>", e.g. "top-4 loop07", or "all"')
ap.add_argument("--prefix", default=None, help="output file prefix (default <method>_<loop> without the dash, e.g. top4_loop07)")
ap.add_argument("--outdir", default=None, help="output directory (default outputs/bar_clause_pilot; use another one for trial runs)")
args = ap.parse_args()
WRITE = Path(args.outdir) if args.outdir else PILOT
WRITE.mkdir(parents=True, exist_ok=True)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one_line(s):
    return " ".join(str(s).split())


# ---------------------------------------------------------------- manual overrides
OV_FILE = PILOT / "citation_overrides.csv"
if not OV_FILE.exists():
    with open(OV_FILE, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(OVERRIDE_HEADER)
OVERRIDES = {}
with open(OV_FILE, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        if r.get("guideline") and r.get("raw_reference_text") and r.get("line"):
            OVERRIDES[(r["guideline"].strip(), one_line(r["raw_reference_text"]))] = [int(x) for x in re.findall(r"\d+", r["line"])]

# ---------------------------------------------------------------- shared data: runs, states, predictions
rows = list(csv.DictReader(open(OUT / "error_rows.csv", encoding="utf-8")))
manifest = {m["run"]: m for m in json.load(open(AUDIT / "run_manifest.json", encoding="utf-8"))}
runs_csv = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig = sorted(r for r, v in runs_csv.items() if v[2] == "original")
assert len(orig) == 19, len(orig)
assert set(orig) == {r for r, m in manifest.items() if m["guideline_group"] == "original"}, "orig runs differ from manifest"
orig_sha = {manifest[r]["guideline_sha256"] for r in orig}
assert len(orig_sha) == 1, orig_sha
ORIG_SHA = orig_sha.pop()

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


MAPS = {run: pred_maps(run) for run in orig}
bars = json.load(open(OUT / "bar_attribution.json", encoding="utf-8"))["bars"]
wl = (PILOT / "count_workload_output.txt").read_text(encoding="utf-8").split("\n")
DOCS = {}


def doc_text(doc):
    if doc not in DOCS:
        with open(AUDIT / "documents" / f"{doc}.txt", encoding="utf-8", newline="") as f:
            DOCS[doc] = f.read()
    return DOCS[doc]


# ---------------------------------------------------------------- guideline structure: index and title inventory
PREFIX_WORD = {"NOT": "NOT", "EX": "Example", "PEND": "Pending", "PREC": "Precedence", "PRINC": "Principle", "OTHER": "Block"}
SUB_ID = r"(?:[a-z]{1,4}|\d{1,2})"
HEAD_ID = r"\d+(?:\.\d+)*[a-z]?(?:\(" + SUB_ID + r"\))*"
LIST_SCOPES = ("NOT", "PEND", "PREC", "EX", "PRINC", "OTHER")


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
    """-> dict(idx, inv, parent_of, scope_of_line, extra_markers).
    idx: (scope, ident) -> [line numbers]. Idents: heading numbers (### 3. / #### 1.2 / **1a.** / **1a(i).**), bold paren
         sub-heads (**(b) Title.**) and lettered bullets ("- (a)", "- **(a)**", "- **(a) Title.**") nested by indentation
         under the latest heading or sub-head ("1a(ii)(c)"), numbered items below a (sub-)head ("1.2(b)(2)"), numbered items of
         the NOT / Examples / Pending / Precedence / other ## blocks, and "Principle N" tags found in titles.
    inv: title inventory = every ### / #### heading, every bold run-in or bold-only paragraph title at line start, bold
         bullet titles ending in a period, numbered items (title = leading bold span; none for Precedence and other blocks).
    parent_of: line -> line of the enclosing ## block heading or ### section heading."""
    idx = collections.defaultdict(list)
    inv, parent_of, scope_of_line = [], {}, {}
    base, prec_level, head, sub, sect = "OTHER", None, None, None, 0
    stack = []                                   # (indent, key) of lettered bullets
    other_title, other_markers = "", []

    def add(no, scope, ident, title, kind):
        norm = norm_text(title)
        kw = {w for w in norm.split() if len(w) >= 4 and w not in STOPWORDS and not w.isdigit()}
        inv.append({"line": no, "scope": scope, "ident": ident, "title": title, "norm": norm, "kw": kw, "kind": kind,
                    "titled": bool(norm) and scope in ("WTA", "NOT", "PEND", "EX")})
        parent_of[no] = sect

    for no, line in enumerate(lines, 1):
        scope = "PREC" if prec_level else base
        scope_of_line[no] = scope
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            head = sub = None
            stack = []
            if level <= 2:
                base, prec_level, sect = scope_of_title(title), None, no
                parent_of[no] = no
                scope_of_line[no] = base
                other_title = clean_title(title) if base == "OTHER" else ""
                continue
            if prec_level and level <= prec_level:
                prec_level = None
            mm = re.match(rf"({HEAD_ID})[.)]?\s+(.*)", title)
            ident, ttl = (mm.group(1).lower(), mm.group(2)) if mm else (None, title)
            is_prec = bool(re.match(r"(?:rule\s+|principle\s+)?precedence\b", ttl, re.I))
            if ident:
                idx[(base, ident)].append(no)
                head = ident
            if is_prec:
                prec_level = level
            if level == 3 or is_prec:
                sect = no
            scope_of_line[no] = base
            add(no, "PREC" if is_prec and not ident else base, ident, clean_title(ttl), "heading")
            continue
        s = line.strip()
        if not s:
            continue
        indent = len(line) - len(line.lstrip(" "))
        # bold numbered heading: **1a. Title** / **1a(i). Title.**
        mm = re.match(rf"^\*\*({HEAD_ID})[.)]\s+(.*?)\*\*", line)
        if mm:
            head, sub, stack = mm.group(1).lower(), None, []
            idx[(scope, head)].append(no)
            add(no, scope, head, clean_title(mm.group(2)), "run-in")
            continue
        # bold paren sub-head at column 0: **(b) Title.** / **(ii) Title.**
        mm = re.match(rf"^\*\*\(({SUB_ID})\)\s+(.*?)\*\*", line)
        if mm:
            stack = []
            key = f"{head}({mm.group(1).lower()})" if head else None
            if key:
                idx[(scope, key)].append(no)
                sub = key
            add(no, scope, key, clean_title(mm.group(2)), "run-in")
            continue
        # other bold paragraph titles at column 0: "**Title.** text" or a bold-only line of two or more words
        if indent == 0 and s.startswith("**"):
            stack = []
            mm = re.match(r"^\*\*([^*]+?)\*\*(.*)$", s)
            if mm:
                span, rest = mm.group(1).strip(), mm.group(2)
                run_in = span.endswith(".") and (rest == "" or rest[0].isspace())
                bold_only = rest.strip() == "" and (len(span.split()) >= 2 or span.endswith((".", ":")))
                if run_in or bold_only:
                    add(no, scope, None, clean_title(span), "run-in")
            continue
        # numbered list items at column 0
        mn = re.match(r"^(\d+)\.\s+(.*)$", line)
        if mn:
            stack = []
            n = mn.group(1)
            if scope in ("NOT", "EX", "PEND", "PREC"):
                idx[(scope, n)].append(no)
                add(no, scope, n, item_title(mn.group(2)), "item")
            elif scope == "OTHER":
                idx[("OTHER", n)].append(no)
                if other_title and other_title not in other_markers:
                    other_markers.append(other_title)
            else:
                parent = sub or head
                if parent:
                    key = f"{parent}({n})"
                    idx[(scope, key)].append(no)
                    ttl = item_title(mn.group(2))
                    if ttl.endswith(("→", ")")) or mn.group(2).startswith("**"):
                        add(no, scope, key, ttl, "item")
            continue
        # bullets
        mb = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if mb:
            ind, rest = len(mb.group(1)), mb.group(2)
            while stack and stack[-1][0] >= ind:
                stack.pop()
            ml = re.match(rf"^(\*\*)?\(({SUB_ID})\)", rest)
            if ml and scope == "WTA":
                parent = stack[-1][1] if stack else (sub or head)
                if parent:
                    key = f"{parent}({ml.group(2).lower()})"
                    idx[(scope, key)].append(no)
                    stack.append((ind, key))
                    mt = re.match(rf"^\*\*\({SUB_ID}\)\s+(.*?)\*\*", rest) if ml.group(1) else None
                    if mt and mt.group(1).strip().endswith("."):
                        add(no, scope, key, clean_title(mt.group(1)), "run-in")
                continue
            mt = re.match(r"^\*\*([^*]+?)\.\*\*\s", rest)
            if mt and scope in ("WTA", "NOT", "PEND"):
                add(no, scope, None, clean_title(mt.group(1)), "run-in")
            continue
        if indent == 0:
            stack = []
    # "Principle N" / "Moderation Principle N" tags in titles
    for e in inv:
        for mm in re.finditer(r"principles?\s+(\d+(?:\s*(?:,|;|and|&)\s*(?:moderation\s+principles?\s+)?\d+)*)", e["title"], re.I):
            for n in re.findall(r"\d+", mm.group(1)):
                if e["line"] not in idx[("PRINC", n)]:
                    idx[("PRINC", n)].append(e["line"])
    extra_markers = [("OTHER", re.compile(r"\s+".join(re.escape(w) for w in t.split()[:2]), re.I)) for t in other_markers]
    return {"idx": idx, "inv": inv, "parent_of": parent_of, "scope_of_line": scope_of_line, "extra_markers": extra_markers}


def load_guideline(sha):
    p = AUDIT / "guidelines" / f"{sha}.txt"
    text = p.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    lines = text.split("\n")
    G = build_index(lines)
    G["lines"], G["sha"] = lines, sha
    G["label"] = {}                                       # line -> identifier shown for a group
    for (sc_, id_), lns_ in G["idx"].items():
        for ln_ in lns_:
            G["label"].setdefault(ln_, display(sc_, id_))
    for e_ in G["inv"]:
        G["label"].setdefault(e_["line"], e_["title"] or f"L{e_['line']}")
    return G


ORIG_G = load_guideline(ORIG_SHA)

# ---------------------------------------------------------------- citation parsing
MARKERS = [("NOT", re.compile(r"what\s+not\s+to\s+annotate", re.I)),
           ("WTA", re.compile(r"what\s+to\s+annotate", re.I)),
           ("PEND", re.compile(r"pending\s+annotation\s+review", re.I)),
           ("PREC", re.compile(r"precedence(?:\s+(?:between\s+overlapping\s+)?rules?)?", re.I))]
DONOT = re.compile(r"do\s+not\s+annotate", re.I)
EXAMPLE = re.compile(r"\bexamples?\s+#?(\d+(?:\s*(?:,|and|&)\s*\d+)*)", re.I)
PRINCIPLE = re.compile(r"\b(?:moderation\s+)?principles?\s+(\d+(?:\s*(?:,|;|and|&)\s*(?:moderation\s+principles?\s+)?\d+)*)", re.I)
NUM = re.compile(r"(?<![\w.])(?:§\s*)?(\d+(?:\.\d+)*)([a-z](?![a-z]))?((?:\((?:[a-z]{1,4}|\d{1,2})\))*)(?!\w)", re.I)
LICENSE = re.compile(r"(?:section|sections|§|item|items|step|steps|rule|rules|guideline|guidelines|principle|principles|"
                     r"example|examples|annotate|review|precedence)\s*#?$", re.I)
CONTINUATION = re.compile(r"^\s*(?:,|;|and|&|or|to)?\s*(?:section|sections|§|item|items|step|steps|rule|rules)?\s*#?$", re.I)
CHILD = re.compile(r"\b(?:step|steps|item|items)\s*$", re.I)


def parse_citation(raw, extra_markers=()):
    """-> list of dicts (scope, ident, assumed, segment, text); duplicates of (scope, ident) inside one citation are dropped.
    text = the part of the segment from the reference's number (or "Example"/"Principle") to the next reference."""
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
        events = []                                     # (pos, order, kind, value)
        for rx, scope in ((EXAMPLE, "EX"), (PRINCIPLE, "PRINC")):
            for m in rx.finditer(seg):
                for n in re.findall(r"\d+", m.group(1)):
                    events.append((m.start(), 0, "ref", (scope, n, False)))
                for i in range(m.start(), m.end()):
                    mask[i] = " "
        masked = "".join(mask)
        wta_word = False
        for sc, rx in MARKERS + list(extra_markers):
            for m in rx.finditer(masked):
                events.append((m.start(), -1, "mark", sc))
                wta_word = wta_word or sc == "WTA"
        donot = any(dep[m.start()] == 0 for m in DONOT.finditer(masked))
        prev_end = -1
        for m in NUM.finditer(masked):
            before = masked[:m.start()]
            licensed = dep[m.start()] == 0 or bool(LICENSE.search(before.rstrip())) or \
                (prev_end >= 0 and bool(CONTINUATION.match(masked[prev_end:m.start()])))
            if not licensed:
                continue
            prev_end = m.end()
            base_num, suffix = m.group(1) + (m.group(2) or ""), (m.group(3) or "")
            if CHILD.search(before):
                events.append((m.start(), 1, "child", (base_num.lower(), suffix.lower())))
            else:
                events.append((m.start(), 1, "num", (base_num + suffix).lower()))
        evs = sorted(events, key=lambda e: (e[0], e[1], e[2], str(e[3])))
        cur, last = None, None                          # scope set by a list name; (scope, ident, assumed) of the previous reference
        for k, (pos, _, kind, val) in enumerate(evs):
            if kind == "mark":
                cur, last = val, None
                continue
            if kind == "ref":
                sc, ident, assumed = val
            elif kind == "child" and last is not None and k > 0 and evs[k - 1][2] != "mark":
                sc, assumed = last[0], last[2]
                ident = f"{last[1]}({val[0]}){val[1]}"
            else:
                idn = val if kind == "num" else val[0] + val[1]
                if cur:
                    sc, ident, assumed = cur, idn, False
                elif donot:
                    sc, ident, assumed = "NOT", idn, False
                else:
                    sc, ident, assumed = "WTA", idn, not wta_word
            last = (sc, ident, assumed)
            end = len(seg)
            for j in range(k + 1, len(evs)):
                if evs[j][0] > pos:
                    if evs[j][2] == "mark" and all(e[2] == "mark" for e in evs[j:]):
                        continue                          # list-name words after the last reference belong to it
                    end = evs[j][0]
                    break
            if (sc, ident) in seen:
                continue
            seen.add((sc, ident))
            refs.append({"scope": sc, "ident": ident, "assumed": assumed, "segment": seg.strip(), "text": one_line(seg[pos:end])})
    return refs


def resolve_number(ref, G):
    """Section-number resolution -> dict(status, lines=[(no, text)], parent=(no, text)|None, note)."""
    lines, idx = G["lines"], G["idx"]
    hits = idx.get((ref["scope"], ref["ident"]), [])
    parent, note = None, ""
    m = re.match(r"^(.*)\((?:[a-z]{1,4}|\d{1,2})\)$", ref["ident"])
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
    cand = [e for e in inv if e["titled"]]
    exact = [e for e in cand if f" {e['norm']} " in nt]
    exact = [e for e in exact if not any(o is not e and o["norm"] != e["norm"] and f" {e['norm']} " in f" {o['norm']} " for o in exact)]
    if exact:
        return ("title_exact" if len(exact) == 1 else "title_ambiguous"), exact, [[] for _ in exact]
    toks = set(nt.split())
    hits = [(e, sorted(e["kw"] & toks)) for e in cand if e["scope"] != "EX" and len(e["kw"] & toks) >= MIN_KEYWORDS]
    if len(hits) == 1:
        return "title_keywords", [hits[0][0]], [hits[0][1]]
    if hits:
        return "title_ambiguous", [e for e, _ in hits], [k for _, k in hits]
    return None


def resolve_ref(ref, G, gname):
    """Override, title rules, then section number. -> dict(num, method, cat, status, lines, entries, kws, scope_changed,
    agrees, parent, candidates)."""
    lines = G["lines"]
    num = resolve_number(ref, G)
    ov = OVERRIDES.get((gname, ref["text"]))
    tm = None
    if not ov and not (not ref["assumed"] and ref["scope"] in LIST_SCOPES):
        tm = title_match(ref["text"], G["inv"])
    if ov:
        method, ents, kws = "override", [], []
        lns = [(n, lines[n - 1]) for n in ov if 1 <= n <= len(lines)]
        status = "resolved" if len(lns) == 1 else "ambiguous" if lns else "unresolved"
        sc = {G["scope_of_line"].get(n) for n, _ in lns}
        changed = "no" if sc == {ref["scope"]} else "yes" if ref["scope"] not in sc else "partial"
    elif tm:
        method, ents, kws = tm
        status = "resolved" if len(ents) == 1 else "ambiguous"
        lns = [(e["line"], lines[e["line"] - 1]) for e in ents]
        same = [e["scope"] == ref["scope"] for e in ents]
        changed = "no" if all(same) else "yes" if not any(same) else "partial"
    else:
        method, ents, kws, status, lns, changed = "section_only", [], [], num["status"], num["lines"], "no"
    agrees = "n/a"
    if method.startswith("title") and num["status"] == "resolved":
        agrees = "yes" if {G["parent_of"].get(n) for n, _ in lns} == {G["parent_of"].get(num["lines"][0][0])} else "no"
    if method in ("override",) or method.startswith("title"):
        cat = method
    elif status == "unresolved":
        cat = "unresolved"
    elif status == "ambiguous":
        cat = "section_only_ambiguous"
    else:
        cat = "section_only_assumed" if ref["assumed"] else "section_only_explicit"
    p = G["parent_of"].get(lns[0][0]) if lns else None
    cand = sorted({n for n, _ in lns} | {n for n, _ in num["lines"]})
    return {"num": num, "method": method, "cat": cat, "status": status, "lines": lns, "entries": ents, "kws": kws,
            "scope_changed": changed, "agrees": agrees, "parent": (p, lines[p - 1]) if p else None, "candidates": cand}


def lines_str(lns):
    return "|".join(f"L{n}" for n, _ in lns) or "-"


AUDIT_COLS = ["guideline", "raw_reference_text", "identifier", "scope_given", "method", "needs_manual_check", "proposed_lines",
              "proposed_line_text", "number_based_lines", "candidate_lines", "matched_keywords", "scope_changed"]


def audit_row(gname, text, ref, res):
    return {"guideline": gname, "raw_reference_text": text, "identifier": display(ref["scope"], ref["ident"]),
            "scope_given": "assumed" if ref["assumed"] else "explicit", "method": res["cat"],
            "needs_manual_check": "no" if res["cat"] in SAFE_CATS else "yes", "proposed_lines": lines_str(res["lines"]),
            "proposed_line_text": " || ".join(f"L{n}: {t.strip()}" for n, t in res["lines"]) or res["num"]["note"],
            "number_based_lines": lines_str(res["num"]["lines"]),
            "candidate_lines": "|".join(f"L{n}" for n in res["candidates"]) or "-",
            "matched_keywords": " ; ".join(",".join(k) for k in res["kws"] if k), "scope_changed": res["scope_changed"]}


LOOKUP_USE = collections.defaultdict(set)         # reference text -> {(guideline, instance position)} over the lookup files
SUMMARY_ROWS = []


# ================================================================ one changed guideline
def process(gname, prefix):
    METHOD, LOOP = gname.split()
    summary_name = f"{prefix}_build_instances_output.txt"
    tgt_runs = [r for r, v in runs_csv.items() if v[:2] == (METHOD, LOOP) and v[2] != "original"]
    assert len(tgt_runs) == 1, tgt_runs
    TGT = tgt_runs[0]
    assert TGT in manifest
    TGT_SHA = manifest[TGT]["guideline_sha256"]
    assert TGT_SHA != ORIG_SHA
    G = load_guideline(TGT_SHA)
    TGT_LINES, LABEL = G["lines"], G["label"]
    tgt_final = REPO / manifest[TGT]["guideline_path"]
    final_same = tgt_final.read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n") == TGT_LINES
    orig_file_same = (REPO / "data/guidelines/ncbi_disease_guidelines.txt").read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n") == ORIG_G["lines"]
    maps_t = pred_maps(TGT)
    at_t, paired_t = maps_t
    MAPS_T = dict(MAPS)
    MAPS_T[TGT] = maps_t

    extra_mismatch = []
    for run in [TGT] + orig:
        a = set(extra[run])
        b = {(p["doc"], p["start"], p["end"], p["pred_label"]) for p in pred_by_run[run] if p["kind"] == "extra"}
        if a != b:
            extra_mismatch.append((run, len(a), len(b)))

    # ---- instances
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

    ctx_fallback = []

    def context(inst):
        doc, s, e = inst["pos"][:3]
        tx = doc_text(doc)
        if tx[s:e] != inst["text"]:
            ctx_fallback.append((doc, s, e, inst["text"], tx[s:e]))
            return one_line(gctx.get(inst["pos"]) or extra_ctx.get(inst["pos"]) or "")
        return one_line(tx[max(0, s - CTX):s] + "[[" + tx[s:e] + "]]" + tx[e:e + CTX])

    # ---- link target predictions and resolve citations
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
                ov, claimed = [], set()
                for p in pred_by_run[TGT]:
                    if p["doc"] != doc:
                        continue
                    for g in p["scoring"]["all_gold_overlaps"]:
                        if (g["start"], g["end"], g["label"]) == (s, e, lab):
                            ov.append(p)
                            claimed |= set(g["overlapping_prediction_indices"])
                if claimed != {p["prediction_index"] for p in ov}:
                    overlap_index_mismatch.append((doc, s, e, sorted(claimed), [p["prediction_index"] for p in ov]))
                inst["overlap_preds"] = ov
                if len(ov) == 1:
                    inst["linked"], inst["link_status"] = ov, "overlap_unique"
        cites = [p["cited_section"] for p in inst["linked"]]
        inst["cited_raw"] = " || ".join(cites)
        inst["rationale"] = " || ".join(one_line(p["raw_rationale"]) for p in inst["linked"])
        refs, seen = [], set()
        for c in cites:
            for r in parse_citation(c, G["extra_markers"]):
                if (r["scope"], r["ident"]) not in seen:
                    seen.add((r["scope"], r["ident"]))
                    r["res"] = resolve_ref(r, G, gname)
                    r["cited"] = c
                    refs.append(r)
        inst["refs"] = refs
        inst["context"] = context(inst)
        inst["overlap_note"] = [f"{p['pred_label']} {p['start']}-{p['end']} {p['pred_text']!r} (scorer kind {p['kind']}; paired to "
                                f"{[g['text'] for g in p['scoring']['paired_gold']]}; cited {p['cited_section']!r})"
                                for p in inst["overlap_preds"]]

    def per_ref(i, fn):
        return " | ".join(fn(r) for r in i["refs"])

    # ---- instances csv
    f_inst = WRITE / f"{prefix}_instances.csv"
    with open(f_inst, "w", encoding="utf-8", newline="") as f:
        cols = ["category", "doc", "start", "end", "text", "gold_label", "nogold_label", "n_orig_of_19", "d", "target_state",
                "link_status", "n_linked_predictions", "target_pred_label", "target_pred_start", "target_pred_end",
                "target_pred_text", "overlap_prediction_info", "cited_section_raw", "parsed_references", "reference_text",
                "resolved_lines", "resolution_status", "sub_item_line", "sub_item_title", "sub_method", "audit_category",
                "scope_changed", "finest_item", "scope_assumed", "raw_rationale", "context"]
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
                "audit_category": per_ref(i, lambda r: r["res"]["cat"]),
                "scope_changed": per_ref(i, lambda r: r["res"]["scope_changed"]),
                "finest_item": per_ref(i, lambda r: lines_str(r["res"]["lines"]) + ("" if r["res"]["status"] == "resolved" else f" {r['res']['status']}")),
                "scope_assumed": " | ".join(display(r["scope"], r["ident"]) for r in i["refs"] if r["assumed"]),
                "raw_rationale": i["rationale"], "context": i["context"]})

    # ---- section groups (keyed by the finest resolved line)
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
        others = ""
        if gk[0] == "L":
            ident = LABEL.get(gk[1], f"L{gk[1]}")
            if any(x["assumed"] and x["res"]["method"] == "section_only" for x in g["refs"]):
                sc_id = [k for k, v in G["idx"].items() if gk[1] in v]
                if sc_id and sc_id[0][0] == "WTA":
                    others = "; ".join(f"{display(sc, sc_id[0][1])}=L{G['idx'][(sc, sc_id[0][1])][0]}" for sc in ("NOT", "EX", "PEND", "PREC")
                                       if (sc, sc_id[0][1]) in G["idx"])
        elif gk[0] == "A":
            ident = "ambiguous " + "|".join(f"L{n}" for n in gk[1])
        else:
            ident = display(r["scope"], r["ident"])
        grows.append(group_row(ident, res["status"], lines_str(res["lines"]), text, parent_sec, parent_head, g["members"],
                               raw_ref=r["segment"] if res["status"] == "unresolved" else "", refs=g["refs"], others=others))
    if no_ref:
        grows.append(group_row("(no parsable reference)", "no_reference", "-", "", "", "", no_ref))
    if unlinked:
        grows.append(group_row("(unlinked)", "unlinked", "-", "no paired prediction and no unique overlapping prediction", "", "", unlinked))
    grows.sort(key=lambda r: (-r["_abs"], r["identifier"]))
    f_groups = WRITE / f"{prefix}_section_groups.csv"
    gcols = ["identifier", "status", "resolved_lines", "line_text", "parent_section", "parent_heading", "raw_reference", "methods",
             "n_scope_assumed", "n_scope_changed", "other_scope_candidates", "n_instances", "sum_positive_d", "sum_negative_d",
             "n_documents", "n_strings", "category_counts", "members"]
    with open(f_groups, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=gcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(grows)

    # ---- no-prediction lookup (original runs' citations, original guideline, same title rules)
    f_look = WRITE / f"{prefix}_noprediction_lookup.csv"
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
            refcount = collections.OrderedDict()
            for p in found:
                refs_p = parse_citation(p["cited_section"], ORIG_G["extra_markers"])
                if not refs_p:
                    numberless[p["cited_section"]] += 1
                for r in refs_p:
                    res = resolve_ref(r, ORIG_G, "original")
                    LOOKUP_USE[r["text"]].add((gname, i["pos"]))
                    key = (display(r["scope"], r["ident"]), res["method"], res["status"], tuple(n for n, _ in res["lines"]), res["scope_changed"])
                    ent = refcount.setdefault(key, [res, 0, 0])
                    ent[1] += 1
                    ent[2] += r["assumed"] and res["method"] == "section_only"
            res_txt = []
            for key, (res, k, k_assumed) in sorted(refcount.items(), key=lambda kv: (-kv[1][1], kv[0][0])):
                body = " || ".join(f"L{n}: {t}" for n, t in res["lines"]) if res["lines"] else res["num"]["note"] or "-"
                tag = res["method"] + ("; scope changed" if res["scope_changed"] != "no" else "")
                res_txt.append(f"{key[0]} [{res['status']}; {tag}] x{k}{f' (scope assumed in {k_assumed})' if k_assumed else ''} -> {body}")
            w.writerow({"category": i["category"], "doc": doc, "start": s, "end": e, "text": i["text"],
                        "gold_label": lab if i["kind"] == "gold" else "", "nogold_label": lab if i["kind"] == "nogold" else "",
                        "d": f"{i['d']:.4f}", "n_orig_of_19": i["n"], "n_orig_predictions_found": len(found),
                        "original_cited_sections": " | ".join(f"{c!r} x{k}" for c, k in cc.most_common()),
                        "rationale_example_1": rats[0] if len(rats) > 0 else "", "rationale_example_2": rats[1] if len(rats) > 1 else "",
                        "rationale_example_3": rats[2] if len(rats) > 2 else "",
                        "citations_resolved_in_original_guideline": " ## ".join(res_txt), "context": i["context"]})

    # ---- citation audit table: one row per distinct reference text
    all_refs = [(i, r) for i in instances for r in i["refs"]]
    aud = collections.OrderedDict()
    for i, r in all_refs:
        a = aud.setdefault(r["text"], {"ref": r, "insts": set(), "cited": []})
        a["insts"].add(i["pos"])
        if r["cited"] not in a["cited"] and len(a["cited"]) < 2:
            a["cited"].append(r["cited"])
    audit_rows = []
    for text, a in aud.items():
        row = audit_row(gname, text, a["ref"], a["ref"]["res"])
        row["n_instances"], row["example_cited_sections"] = len(a["insts"]), " || ".join(a["cited"])
        audit_rows.append(row)
    audit_rows.sort(key=lambda r: (r["needs_manual_check"] != "yes", r["method"], -r["n_instances"], r["raw_reference_text"]))
    f_audit = WRITE / f"{prefix}_citation_audit.csv"
    with open(f_audit, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_COLS + ["n_instances", "example_cited_sections"])
        w.writeheader()
        w.writerows(audit_rows)

    # ---- checks and summary
    L = []
    P = L.append
    by_cat = {c: [i for i in instances if i["category"] == c] for c in CATS}
    sd = lambda xs: sum(i["d"] for i in xs)
    n_with = sum(len(by_cat[c]) for c in WITH_PRED)
    no_gold_unlab, no_drop = by_cat["gold_now_unlabelled"], by_cat["nogold_dropped_prediction"]

    P(f"build_instances.py: {gname} against the 19 original runs (offline, no API); prefix {prefix}")
    P(f"target run: {TGT}")
    P(f"target guideline snapshot sha256: {TGT_SHA}")
    P(f"  identical to {manifest[TGT]['guideline_path']} after CRLF -> LF: {final_same}")
    P(f"original guideline snapshot sha256: {ORIG_SHA}; identical to data/guidelines/ncbi_disease_guidelines.txt after CRLF -> LF: {orig_file_same}")
    P(f"original runs: {len(orig)}; all 19 use the same snapshot (manifest guideline_sha256); instances with d != 0: {len(instances)}")
    P(f"manual overrides in {OV_FILE.name}: {len(OVERRIDES)} rows, {sum(1 for k in OVERRIDES if k[0] == gname)} for this guideline")
    P("")
    P("A. Instances by category (n | sum d | sum of positive d | sum of negative d)")
    for c in CATS:
        xs = by_cat[c]
        P(f"   {c:32s} {len(xs):4d} | {sd(xs):+8.2f} | {sum(i['d'] for i in xs if i['d'] > 0):+8.2f} | {sum(i['d'] for i in xs if i['d'] < 0):+8.2f}")
    P(f"   with a prediction in this run: {n_with}; without: {len(no_gold_unlab) + len(no_drop)}")
    P("")

    m1 = [re.match(rf"^\s+{re.escape(gname)}:\s+(\d+) \|\s+(\d+) \(([+-][\d.]+)\);", l) for l in wl]
    m1 = [m for m in m1 if m][0]
    ref_with, ref_without, ref_sum = int(m1.group(1)), int(m1.group(2)), float(m1.group(3))
    my_without = len(no_gold_unlab) + len(no_drop)
    my_sum = sd(no_gold_unlab) + sd(no_drop)
    c1 = n_with == ref_with and my_without == ref_without and abs(round(my_sum, 1) - ref_sum) < 1e-9
    line_b = {}
    for l in wl:
        mm = re.match(r"^B\. (gold mentions|no-gold predictions) .*: (\d+) positions, summed difference ([+-][\d.]+)", l)
        if mm and gname == DEFAULT:
            line_b[mm.group(1)] = (int(mm.group(2)), float(mm.group(3)))
    if line_b:
        c1 = c1 and line_b["gold mentions"] == (len(no_gold_unlab), round(sd(no_gold_unlab), 1)) \
            and line_b["no-gold predictions"] == (len(no_drop), round(sd(no_drop), 1))
    P(f"CHECK 1 counts vs count_workload_output.txt: {'PASS' if c1 else 'FAIL'}")
    P(f"   with prediction {n_with} (file {ref_with}); without {my_without} (file {ref_without}); summed d without {my_sum:+.2f} (file {ref_sum:+.1f})")
    if line_b:
        P(f"   gold left unlabelled {len(no_gold_unlab)}, summed d {sd(no_gold_unlab):+.2f} (file {line_b.get('gold mentions')}); "
          f"no-gold dropped {len(no_drop)}, summed d {sd(no_drop):+.2f} (file {line_b.get('no-gold predictions')})")

    c2 = True
    P("CHECK 2 sum of d over gold instances of each label vs bar in bar_attribution.json (tolerance 0.05):")
    for lab in ("SpecificDisease", "DiseaseClass", "Modifier"):
        mine = sum(i["d"] for i in instances if i["kind"] == "gold" and i["pos"][3] == lab)
        bar = bars[lab][gname]
        ok = abs(mine - bar) <= 0.05
        c2 = c2 and ok
        P(f"   {lab:16s} sum d {mine:+.4f}  bar {bar:+.4f}  diff {mine - bar:+.2e}  {'ok' if ok else 'MISMATCH'}")
    other_labels = sorted({i["pos"][3] for i in instances if i["kind"] == "gold"} - {"SpecificDisease", "DiseaseClass", "Modifier"})
    P(f"   gold labels with d != 0 outside the three bars: {other_labels or 'none'}")
    P(f"   -> {'PASS' if c2 else 'FAIL'}")

    n_paired = sum(1 for i in instances if i["link_status"] == "linked")
    ou = [i for i in instances if i["link_status"] == "overlap_unique"]
    c3 = not unlinked
    P(f"CHECK 3 links of the {n_with} instances with a prediction: paired {n_paired}; overlap_unique {len(ou)}; "
      f"still unlinked {len(unlinked)} (expected 0) -> {'PASS' if c3 else 'FAIL'}")
    for i in unlinked:
        P(f"   unlinked: {i['category']} {i['pos'][0]}:{i['pos'][1]}-{i['pos'][2]} {i['pos'][3]} {i['text']!r} d {i['d']:+.2f} "
          f"target state {i['tstate']}; overlapping predictions {len(i['overlap_preds'])}")
    if ou:
        kinds = collections.Counter(f"{i['linked'][0]['pred_label']}/scorer kind {i['linked'][0]['kind']}" for i in ou)
        P(f"   overlap_unique: scorer state of the gold {sorted({i['tstate'] for i in ou})}, summed d {sd(ou):+.2f}; "
          f"label / scorer kind of the linked predictions: {dict(kinds)}")
        P(f"   all_gold_overlaps agrees with overlapping_prediction_indices: {'yes' if not overlap_index_mismatch else 'NO ' + str(overlap_index_mismatch)}")

    nrefs = len(all_refs)
    cnt = collections.Counter(r["res"]["num"]["status"] for _, r in all_refs)
    P(f"CHECK 4 citation resolution by section number alone ({sum(1 for i in instances if i['has_pred'] and i['linked'])} instances with a linked "
      f"prediction, {nrefs} references, one per distinct identifier per instance): resolved {cnt['resolved']}, "
      f"ambiguous {cnt['ambiguous']}, unresolved {cnt['unresolved']}; citations with no parsable reference: {len(no_ref)}")
    cc_ = collections.Counter(r["res"]["cat"] for _, r in all_refs)
    dist = collections.Counter(row["method"] for row in audit_rows)
    P("CHECK 5 references by method after override and title rules (references | distinct reference texts):")
    for c in REF_CATS:
        P(f"   {c:24s} {cc_[c]:5d} | {dist[c]:4d}")
    n_manual = sum(1 for row in audit_rows if row["needs_manual_check"] == "yes")
    P(f"   distinct reference texts that are not title_exact, explicit-scope section_only or override (to verify by hand): {n_manual} of {len(audit_rows)}; table {f_audit.name}")
    P(f"   unresolved: {', '.join(repr(row['raw_reference_text']) for row in audit_rows if row['method'] == 'unresolved')[:600] or 'none'}")

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
    P("F. Sub-item resolution (references counted once per instance and distinct identifier)")
    P(f"   MIN_KEYWORDS = {MIN_KEYWORDS}; STOPWORDS = {sorted(STOPWORDS)}")
    mc = collections.Counter(r["res"]["method"] for _, r in all_refs)
    P("   references by method: " + ", ".join(f"{m} {mc[m]}" for m in ("override", "title_exact", "title_keywords", "title_ambiguous", "section_only")) + f" (total {nrefs})")
    tm_refs = [(i, r) for i, r in all_refs if r["res"]["method"].startswith("title")]
    ag = collections.Counter(r["res"]["agrees"] for _, r in tm_refs)
    P(f"   title matches whose line lies in the same section as the cited number: yes {ag['yes']}, no {ag['no']}, number not resolved to one line {ag['n/a']}")
    sc_ = collections.Counter(r["res"]["scope_changed"] for _, r in all_refs)
    P(f"   scope changed by a title match or override (matched list differs from the assumed or explicit scope): yes {sc_['yes']}, partial {sc_['partial']}")

    def agg_lines(refs_sel):
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
    chg = [(i, r) for i, r in all_refs if r["res"]["scope_changed"] != "no"]
    P(f"   references whose scope changed: {len(chg)}")
    for key, items in agg_lines(chg).items():
        r = items[0][1]
        P(f"   x{len(items):<3d} {key[0]!r}: {r['scope']}{'(assumed)' if r['assumed'] else '(explicit)'} -> "
          f"{','.join(sorted({G['scope_of_line'].get(n) for n, _ in r['res']['lines']}))}, {key[2]}, "
          f"{key[1]}={lines_str(r['res']['num']['lines'])} -> {lines_str(r['res']['lines'])}")
    P("")
    P("G. Title inventory of the target guideline (line | list | number | kind | titled | title | keywords)")
    for e in G["inv"]:
        P(f"   L{e['line']:<4d}{e['scope']:5s}{e['ident'] or '-':12s}{e['kind']:8s}{'T' if e['titled'] else '-'} {e['title'][:70]!r} | {','.join(sorted(e['kw']))}")
    P("")
    P(f"   index keys: {len(G['idx'])}; extra block markers: {[rx.pattern for _, rx in G['extra_markers']]}")
    P("")
    P("H. Files (sha256)")
    P(f"   input  error_rows.csv {sha256(OUT / 'error_rows.csv')}")
    P(f"   input  prediction_index.jsonl {sha256(AUDIT / 'prediction_index.jsonl')}")
    P(f"   input  run_manifest.json {sha256(AUDIT / 'run_manifest.json')}")
    P(f"   input  {OV_FILE.name} {sha256(OV_FILE)}")
    for fp in (f_inst, f_groups, f_look, f_audit):
        P(f"   output {fp.name} {sha256(fp)}")
    ALL_PASS = c1 and c2 and c3
    P("")
    P(f"OVERALL: checks 1-3 {'PASS' if ALL_PASS else 'NOT ALL PASS'}")
    (WRITE / summary_name).write_text("\n".join(L) + "\n", encoding="utf-8")
    SUMMARY_ROWS.append({"guideline": gname, "prefix": prefix, "c1": c1, "c2": c2, "unlinked": len(unlinked), "overlap_unique": len(ou),
                         "refs": cc_, "distinct": dist, "n_manual": n_manual, "n_distinct": len(audit_rows), "audit": f_audit.name,
                         "n_inst": len(instances)})
    return L


# ================================================================ original-guideline citation audit
def original_audit():
    aud = collections.OrderedDict()
    for o in orig:
        for p in pred_by_run[o]:
            for r in parse_citation(p["cited_section"], ORIG_G["extra_markers"]):
                a = aud.setdefault(r["text"], {"ref": r, "n_pred": 0, "cited": []})
                a["n_pred"] += 1
                if p["cited_section"] not in a["cited"] and len(a["cited"]) < 2:
                    a["cited"].append(p["cited_section"])
    rows_ = []
    for text, a in aud.items():
        res = resolve_ref(a["ref"], ORIG_G, "original")
        row = audit_row("original", text, a["ref"], res)
        row["n_lookup_instances"] = len(LOOKUP_USE.get(text, ()))
        row["n_predictions_in_19_original_runs"] = a["n_pred"]
        row["example_cited_sections"] = " || ".join(a["cited"])
        rows_.append(row)
    rows_.sort(key=lambda r: (r["needs_manual_check"] != "yes", r["n_lookup_instances"] == 0, r["method"], -r["n_lookup_instances"],
                              -r["n_predictions_in_19_original_runs"], r["raw_reference_text"]))
    path = WRITE / "original_citation_audit.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_COLS + ["n_lookup_instances", "n_predictions_in_19_original_runs", "example_cited_sections"])
        w.writeheader()
        w.writerows(rows_)
    return path, rows_


if args.guideline == "all":
    for gname in ALL_GUIDELINES:
        process(gname, args.prefix or f"{gname.split()[0].replace('-', '')}_{gname.split()[1]}")
    path, orows = original_audit()
    dist = collections.Counter(r["method"] for r in orows)
    used = [r for r in orows if r["n_lookup_instances"] > 0]
    dist_used = collections.Counter(r["method"] for r in used)
    out = ["Citation audit summary (references | distinct reference texts) per guideline"]
    out.append(f"{'guideline':14s} " + " ".join(f"{c[:14]:>14s}" for c in REF_CATS) + "   to_verify/distinct  checks(1,2,unlinked,overlap_unique)")
    for s in SUMMARY_ROWS:
        out.append(f"{s['guideline']:14s} " + " ".join(f"{s['refs'][c]:>6d}|{s['distinct'][c]:<7d}" for c in REF_CATS) +
                   f"   {s['n_manual']}/{s['n_distinct']}   {s['c1']},{s['c2']},{s['unlinked']},{s['overlap_unique']}   {s['audit']}")
    out.append("")
    out.append(f"original-run citations (19 runs, all predictions): {len(orows)} distinct reference texts; by method: "
               + ", ".join(f"{c} {dist[c]}" for c in REF_CATS))
    out.append(f"  used in the lookup files: {len(used)} distinct reference texts; by method: " + ", ".join(f"{c} {dist_used[c]}" for c in REF_CATS))
    out.append(f"  to verify by hand (not title_exact / explicit-scope / override): all {sum(1 for r in orows if r['needs_manual_check'] == 'yes')}, "
               f"lookup-used {sum(1 for r in used if r['needs_manual_check'] == 'yes')}; table {path.name}")
    (WRITE / "citation_audit_summary.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
else:
    METHOD_, LOOP_ = args.guideline.split()
    lines_out = process(args.guideline, args.prefix or f"{METHOD_.replace('-', '')}_{LOOP_}")
    print("\n".join(lines_out))
