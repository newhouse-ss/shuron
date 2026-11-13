"""Run all required checks with network and credential reads blocked."""

from __future__ import annotations

import builtins
import difflib
import io
import json
import os
import re
import runpy
import socket
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
from common import (  # noqa: E402
    ARMS, FIND, NODE, ROOT, RUNS, S_PLUS, TRAIN, hb, load_inputs, manifest, prompt, read_json,
)
from run_pilot import arm_dir, dry_run, run_document  # noqa: E402
from score_pilot import document_counts  # noqa: E402
from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = NODE / "outputs"


@contextmanager
def writable_test_temporaries():
    """Use inherited workspace permissions, avoiding Windows Python 3.12's private 0700 ACL."""
    original = tempfile.mkdtemp
    def create(suffix=None, prefix=None, dir=None):
        parent = Path(dir) if dir is not None else OUT
        parent = parent.resolve()
        if not parent.is_relative_to(OUT.resolve()):
            raise AssertionError(f"test temporary directory outside authorized output area: {parent}")
        path = parent / f"{prefix or 'tmp'}{uuid.uuid4().hex[:12]}{suffix or ''}"
        path.mkdir(parents=True)
        return str(path)
    tempfile.mkdtemp = create
    try:
        yield
    finally:
        tempfile.mkdtemp = original


@contextmanager
def offline_guard():
    def denied(*args, **kwargs):
        raise AssertionError("offline checks prohibit network access")
    held = read_json(ROOT / "reproduction/test_splits/ncbi_disease_heldout50.json")
    forbidden = set(held["documents"]) | set(held["excluded_biored"])
    original_open, original_io_open = builtins.open, io.open
    def guarded(opener):
        def open_file(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(file))
                if path.name == ".env" or path.name.startswith(".env."):
                    raise AssertionError("offline checks prohibit credential file reads")
                if path.name in forbidden and path.parent.resolve() == TRAIN.resolve():
                    raise AssertionError("offline checks prohibit held-out document reads")
            return opener(file, *args, **kwargs)
        return open_file
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo)
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = socket.getaddrinfo = denied
    builtins.open, io.open = guarded(original_open), guarded(original_io_open)
    try:
        yield
    finally:
        builtins.open, io.open = original_open, original_io_open
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo = saved


class CaptureProvider:
    def complete(self, task, text):
        self.prompt = text
        return '{"annotations": []}'


def check_prompts():
    guideline, entities = load_inputs()
    name = manifest()["pilot_documents"][0]
    text = read_json(TRAIN / name)["text"]
    capture = CaptureProvider()
    annotate_with_guidelines(text=text, guidelines=guideline, entities=entities, provider=capture,
                             instructions="", output_configuration=hb.CONFIG)
    assert prompt("S", text, guideline, entities) == capture.prompt
    assert hb.make_template().build_params("annotate_with_guidelines", capture.prompt) == hb.make_template().build_params(
        "annotate_with_guidelines", prompt("S", text, guideline, entities))
    # Removing just the final sentence and the two extra output fields makes S+ and find identical.
    plus, find = prompt("S+", text, guideline, entities), prompt("find", text, guideline, entities)
    common_instructions = FIND.rsplit(". ", 1)[0]
    normalized_plus = plus.replace(S_PLUS, common_instructions).replace('  "entity": string,\n', "").replace(',\n  "excluded": string', "")
    normalized_find = find.replace(FIND, common_instructions)
    assert normalized_plus == normalized_find
    print("S+ versus T step-1 prompt diff:")
    print("".join(difflib.unified_diff(plus.splitlines(True), find.splitlines(True), fromfile="S+", tofile="T step 1", n=1)))
    print(f"CHECK 1: PASS; S prompt and request equal reproduction validation; guideline SHA-256={hb.sha(guideline)}; S+/T differences limited to last instruction sentence and output fields")


def check_fake_arms(root):
    guideline, entities = load_inputs()
    names = manifest()["pilot_documents"][:2]
    documents = {n: read_json(TRAIN / n) for n in names}
    rows = {}
    for name, document in documents.items():
        matches = list(re.finditer(r"[A-Za-z]{4,}", document["text"]))[:3]
        assert len(matches) == 3
        rows[name] = [{"start": m.start(), "end": m.end(), "text": m.group(), "rationale": "hand-written",
                       "guideline_section": "1"} for m in matches]
    used = []
    class FakeProvider:
        def __init__(self, arm, run, step, name):
            self.arm, self.step, self.name = arm, step, name
            self.loop_id = f"fake-{arm}-{run}-{step}-{name}"
        def complete(self, task, text):
            used.append(self.loop_id)
            first, second, third = rows[self.name]
            if self.step == "S":
                raw = {"annotations": [{**first, "start": first["start"] + 1, "entity": "SpecificDisease"},
                                       {**second, "entity": "DiseaseClass"}]}
            elif self.step == "S+":
                raw = {"annotations": [{**first, "entity": "SpecificDisease", "excluded": "no"},
                                       {**second, "entity": "DiseaseClass", "excluded": "yes"}]}
            elif self.step == "find":
                raw = {"annotations": [third, second, first] if self.name == names[0] else []}
            else:
                assert self.name == names[0], "no typing call is allowed for the empty document"
                candidates = json.loads(text.split("**CANDIDATE SPANS:**\n")[1].split("\n\nProvide")[0])
                assert [(r["id"], r["start"]) for r in candidates] == [(i, r["start"]) for i, r in enumerate(rows[self.name], 1)]
                raw = {"decisions": [{"id": 1, "entity": "DiseaseClass", "rationale": "first", "guideline_section": "1"},
                                     {"id": 1, "entity": "NONE", "rationale": "repeated", "guideline_section": "1"},
                                     {"id": 3, "entity": "NONE", "rationale": "excluded", "guideline_section": "1"},
                                     {"id": 999, "entity": "SpecificDisease", "rationale": "unknown", "guideline_section": "1"}]}
            return json.dumps(raw)
    for arm in ARMS:
        for run in RUNS:
            for name in names:
                status = run_document(root, arm, run, name, documents[name], guideline, entities, FakeProvider)
                assert status["status"] == "completed", status
                first, second, third = rows[name]
                def expected(spans):
                    return [{"id": f"T{i}", "span": {"begin": r["start"], "end": r["end"]}, "obj": label}
                            for i, (r, label) in enumerate(spans, 1)]
                if arm == "S":
                    one = two = [(first, "SpecificDisease"), (second, "DiseaseClass")]
                elif arm == "S+":
                    one, two = [(first, "SpecificDisease")], [(first, "SpecificDisease"), (second, "DiseaseClass")]
                elif name == names[0]:
                    one, two = [(first, "DiseaseClass")], [(first, "DiseaseClass"), (second, "Candidate"), (third, "Candidate")]
                else:
                    one = two = []
                directory = arm_dir(root, arm, run)
                for track, wanted in (("track1_predictions", one), ("track2_predictions", two)):
                    saved = read_json(directory / track / name)
                    assert saved["text"] == documents[name]["text"] and saved["denotations"] == expected(wanted), (arm, name, track)
                assert status["undecided"] == (1 if arm == "T" and name == names[0] else 0)
    assert len(used) == 14 and len(set(used)) == 14
    print("CHECK 2: PASS; 3 arms x 2 pilot documents x 2 runs; hand-computed Track 1/2 and undecided counts match; missing/repeated/unknown IDs and empty-candidate skip verified")


def check_true_misses():
    predictions = ROOT / "outputs/ncbi_disease/20261022_haiku-xhigh_e1_run01/valid_predictions"
    gold_root = ROOT / "data/datasets/ncbi_disease/valid"
    names = sorted(p.name for p in gold_root.glob("*.json"))
    assert len(names) == 100 and set(names) == {p.name for p in predictions.glob("*.json")}
    total = sum(document_counts(name, read_json(gold_root / name), read_json(predictions / name))["true_misses"] for name in names)
    assert total == 140, total
    print("CHECK 3: PASS; e1_run01 valid100 true misses=140")


def check_split():
    selected = manifest()
    pilot, reserved, pool = (set(selected[k]) for k in ("pilot_documents", "reserved_documents", "pool_names"))
    held = read_json(ROOT / "reproduction/test_splits/ncbi_disease_heldout50.json")
    dev = set(read_json(ROOT / "reproduction/dev_splits/ncbi_disease_dev50.json")["documents"])
    assert (len(pool), len(pilot), len(reserved)) == (487, 200, 100)
    assert not pilot & reserved and pilot | reserved <= pool
    assert not (pilot | reserved) & (dev | set(held["documents"]) | set(held["excluded_biored"]))
    print(f"CHECK 4: PASS; pool=487; pilot=200; reserved=100; disjoint; no dev50/heldout50/BioRED IDs; pool SHA-256={selected['pool_sha256']}")


def reproduction_child(script):
    with offline_guard(), writable_test_temporaries():
        runpy.run_path(str(ROOT / "reproduction/tests" / script), run_name="__main__")


def check_reproduction(root):
    scripts = sorted((ROOT / "reproduction/tests").glob("test_*.py"))
    assert scripts
    for script in scripts:
        child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--reproduction-child", script.name],
                               cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
                                              "TMP": str(root), "TEMP": str(root)},
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        print(f"Reproduction suite: {script.name}")
        print(child.stdout)
        if child.stderr:
            print(child.stderr)
        assert child.returncode == 0, f"{script.name} exit={child.returncode}"
    print(f"CHECK 6: PASS; reproduction/tests/ ({len(scripts)} standalone suites, exit=0 each; fake API only)")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--reproduction-child":
        reproduction_child(sys.argv[2])
        return
    OUT.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    passed = False
    try:
        with redirect_stdout(buffer), offline_guard(), writable_test_temporaries(), tempfile.TemporaryDirectory(prefix="pilot_checks_", dir=OUT) as temporary:
            root = Path(temporary)
            check_prompts()
            check_fake_arms(root / "fake_arms")
            check_true_misses()
            check_split()
            print(dry_run())
            print("CHECK 5: PASS; maximum planned calls=1600 before retries; estimated cost=JPY 1014.40 at JPY 0.634/call; no calls executed")
            sys.path.insert(0, str(HERE / "tests"))
            from test_pilot import run_regressions
            print(run_regressions(root / "regressions"))
            check_reproduction(root)
            print("ALL OFFLINE CHECKS: PASS; network blocked; no credential files read; no paid calls or batches submitted")
            passed = True
    finally:
        text = "\n".join(line.rstrip() for line in buffer.getvalue().splitlines()) + "\n"
        (OUT / "pilot_offline_checks_output.txt").write_bytes(text.encode("utf-8"))
        print(text)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
