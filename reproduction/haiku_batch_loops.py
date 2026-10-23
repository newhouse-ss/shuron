"""Refinement loops on Claude Haiku 5.5 through the Message Batches API, all loops moving in lockstep.

WHAT IT RUNS
------------
RP v4 step 2 loops: the published top-1 loop (iterative.run_iterative_refinement, unchanged) and the top-4 loop
(reproduction/moderate_topk.py with k=4). Inputs as the published spec: dev10
(reproduction/dev_splits/ncbi_disease_dev10.json), data/guidelines/ncbi_disease_guidelines.txt, n_examples 5,
threshold 0.9, at most 20 rounds, rationale and guideline section in the annotation output. Each final guideline
is annotated once on valid100 and scored with strict PubAnnotation matching (reproduction/lib/scoring.py, the
scorer behind eval_valid.py). Model settings are the Haiku trial's H_xhigh (todo-temp/haiku-trial/run_haiku.py):
claude-haiku-5-5, effort xhigh, adaptive thinking, structured outputs for annotation, except the output cap:
max_tokens 128000 (Haiku 5.5's maximum) for every call of every loop. The first pilot (2026-10-22) ran at the
trial's 64000; its top-4 rewrite was cut off there three times, all of it thinking, so the user raised the cap.
E1 runs (--e1) annotate valid100 with the original guideline through the same validation step, no refinement.

HOW
---
Every provider.complete() call goes into one shared queue instead of the API. When no new call has arrived for
QUIET seconds (every loop is waiting), the queue sends everything pending as one batch, waits for it to end and
hands each loop its reply. So each step of every loop costs one batch. Two changes make a step one batch instead
of several, without changing any prompt:
  * the documents of an annotation step are annotated concurrently (same calls, results in the same order);
  * the top-4 refinement runs its 4 clusters concurrently (within a cluster, discrepancy then principle, exactly
    as moderate_topk.topk_refine; the offline check asserts the prompts are identical).
The top-4 rewrite template is moderate_topk.build_template(published), applied per call, so the top-1 loop in
the same process keeps the published template.

RESUME
------
Every reply is saved under a key of (loop, task, request hash, occurrence, attempt) before it is used. A rerun
replays each loop from the saved replies (the loop is deterministic given its replies) and only new calls go out.
A batch that was sent but not collected is listed in state.json and collected first on restart, so nothing is
sent twice. Two loops never share a reply, even where their prompts are identical.

The runner always runs with PYTHONHASHSEED=0 (main() restarts itself with it): the published loop lists the
true-positive examples in set order, which otherwise changes from process to process, so prompts would differ
after a restart. The first pilot ran without it, so its analysis replies cannot be replayed; its annotation
replies can (annotation prompts do not depend on set order).

The request hash leaves the output cap out (it is computed as if max_tokens were 64000, the cap of the first
pilot), so a reply that ended normally under the old cap is reused after the cap was raised. This assumes a cap
does not change a reply that ends below it. A reply that was cut off under a lower cap than the current one is
skipped and asked again at the current cap; it does not count as an attempt.

A reply that cannot be used (cut off at max_tokens, refused, or annotation JSON that does not parse) is asked
again, at most MAX_ATTEMPTS times; errored or expired batch requests (not billed) are resent the same way. Saved
unusable replies count as tries, so a call that used all its tries fails again on a resume; --max-attempts raises
the limit for such a resume. A rewrite cut off at the cap three times still ends the round (--stop-at-cap).

--first-loop leaves lower-numbered loops alone. The pilot's top-1 loop 01 ran before the hash seed was fixed, so a
rerun would rebuild its analysis prompts differently, send new calls and overwrite its folder; the reproduction
runs loops 02 to 10 (user, 10/22: the pilot loops count as loop 1).

MONEY
-----
Batch price. Spend is summed from the usage of every saved reply; no batch is sent once it reaches --cap-usd.
The cap is checked before each step, so one step can go past it. A step larger than MAX_BATCH_BYTES (the Batch API
takes at most 256 MB) goes out as several batches, all sent before any is collected.

    python reproduction/haiku_batch_loops.py dry-run
    python reproduction/haiku_batch_loops.py run --top1 1 --top4 1 --cap-usd 2.00 --yes
    python reproduction/haiku_batch_loops.py run --first-loop 2 --top1 10 --top4 10 --e1 10 --stop-at-cap --cap-usd 25 --yes
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in (REPO_ROOT / "src", REPO_ROOT / "reproduction", REPO_ROOT / "todo-temp/haiku-trial"):
    sys.path.insert(0, str(extra))

import moderate_topk  # noqa: E402
import run_haiku as rh  # noqa: E402
from lib.scoring import score_directory  # noqa: E402
from llm_guideline_moderation import iterative  # noqa: E402
from llm_guideline_moderation.artifacts import write_json  # noqa: E402
from llm_guideline_moderation.evaluation import PubAnnotationEvaluatorOptions  # noqa: E402
from llm_guideline_moderation.layout import prepare_run_layout  # noqa: E402
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402
from llm_guideline_moderation.pubannotation import annotations_to_pubannotation  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402

DEV_SPLIT = REPO_ROOT / "reproduction/dev_splits/ncbi_disease_dev10.json"
TRAIN_DIR = REPO_ROOT / "data/datasets/ncbi_disease/train"
VALID_DIR = REPO_ROOT / "data/datasets/ncbi_disease/valid"
GUIDELINES = REPO_ROOT / "data/guidelines/ncbi_disease_guidelines.txt"
ENTITY_SCHEMA = REPO_ROOT / "data/schemas/ncbi_entities.schema.json"
OUTPUT_ROOT = REPO_ROOT / "outputs/ncbi_disease"
TAG = "20261022_haiku-xhigh"
ARM = "H_xhigh"
TOPK = 4
N_EXAMPLES = 5
THRESHOLD_F1 = 0.9
QUIET = 5.0
POLL = 30.0
MAX_ATTEMPTS = 3
# The Batch API takes at most 100,000 requests or 256 MB per batch; a larger step goes out as several batches.
MAX_BATCH_BYTES = 100 * 2**20
MAX_BATCH_REQUESTS = 50_000
MAX_OUTPUT_TOKENS = 128_000
KEY_MAX_TOKENS = 64_000  # the cap the first pilot ran at; kept in the request hash so its replies still match
CONFIG = OutputConfiguration(include_rationale=True, include_guideline_section=True)
TOPK_TEMPLATE = moderate_topk.build_template(PROMPT_TEMPLATES["refine_guidelines"])
assert "{verified_examples}" in TOPK_TEMPLATE and "CONSTRAINT CHECK" in TOPK_TEMPLATE
assert "ONE Dominant Discrepancy Case" in PROMPT_TEMPLATES["infer_discrepancy_patterns"]
assert "ONE Core Moderation Principle" in PROMPT_TEMPLATES["generate_moderation_principle"]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_template():
    """The trial's H_xhigh provider with the raised output cap."""
    provider = rh.make_provider(ARM)
    provider.max_output_tokens = MAX_OUTPUT_TOKENS
    return provider


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def say(*parts) -> None:
    print(f"{datetime.now(timezone.utc):%H:%M:%S}", *parts, flush=True)


class BatchQueue:
    """Collects calls from all loops and sends them as one batch once every loop is waiting."""

    def __init__(self, workdir: Path, client, cap_jpy: float, quiet: float = QUIET, poll: float = POLL,
                 max_attempts: int = MAX_ATTEMPTS) -> None:
        self.dir = workdir
        self.replies = workdir / "replies"
        self.replies.mkdir(parents=True, exist_ok=True)
        self.state_path = workdir / "state.json"
        self.client, self.cap, self.quiet, self.poll = client, cap_jpy, quiet, poll
        self.max_attempts = max_attempts
        self.max_bytes = MAX_BATCH_BYTES  # read here, not as a default argument, so a test can lower it
        self.lock = threading.Lock()
        self.pending: dict[str, list] = {}  # custom_id -> [params, meta, future, attempts]
        self.last_add = 0.0
        self.error: str | None = None
        self.sent = 0

    def state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"inflight": {}, "batches": []}

    def save_state(self, state: dict) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def saved(self, cid: str) -> dict | None:
        path = self.replies / f"{cid}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save_reply(self, cid: str, meta: dict, message: dict, batch_id: str) -> None:
        path = self.replies / f"{cid}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"custom_id": cid, "meta": meta, "batch_id": batch_id, "saved_utc": now(),
                                   "message": message}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def spent_jpy(self) -> float:
        return sum(rh.cost_jpy(json.loads(p.read_text(encoding="utf-8"))["message"].get("usage") or {}, True)
                   for p in self.replies.glob("*.json"))

    def start(self) -> None:
        state = self.state()
        for batch_id, metas in list(state["inflight"].items()):
            say(f"collecting batch {batch_id} sent before the restart ({len(metas)} requests)")
            results = self.fetch(batch_id)
            for cid, meta in metas.items():
                result = results.get(cid) or {}
                if result.get("type") == "succeeded":
                    self.save_reply(cid, meta, result["message"], batch_id)
            state = self.state()
            state["inflight"].pop(batch_id, None)
            self.save_state(state)
        threading.Thread(target=self.run, daemon=True).start()

    def request(self, cid: str, params: dict, meta: dict) -> dict:
        hit = self.saved(cid)
        if hit:
            return hit["message"]
        with self.lock:
            if self.error:
                raise RuntimeError(self.error)
            if cid not in self.pending:
                self.pending[cid] = [params, meta, cf.Future(), 0]
                self.last_add = time.monotonic()
            future = self.pending[cid][2]
        return future.result()

    def run(self) -> None:
        while True:
            time.sleep(0.2)
            with self.lock:
                if not self.pending or time.monotonic() - self.last_add < self.quiet:
                    continue
                batch, self.pending = self.pending, {}
            spent = self.spent_jpy()
            if spent >= self.cap:
                self.fail(batch, f"spending cap reached: JPY {spent:.0f} spent, cap JPY {self.cap:.0f}")
                continue
            try:
                self.send(batch)
            except Exception as exc:  # noqa: BLE001 - every waiting loop must hear about it
                self.fail(batch, f"batch failed: {type(exc).__name__}: {exc}")

    def fail(self, batch: dict, reason: str) -> None:
        with self.lock:
            self.error = reason
        say(reason)
        for params, meta, future, attempts in batch.values():
            if not future.done():  # a part of a split step may already have its replies
                future.set_exception(RuntimeError(reason))

    def split(self, batch: dict) -> list[dict]:
        """The step's requests in parts under the size and count limits, in their original order."""
        parts, part, size = [], {}, 0
        for cid, entry in batch.items():
            n = len(json.dumps({"custom_id": cid, "params": entry[0]}))  # ASCII-escaped, so at least the bytes sent
            if part and (size + n > self.max_bytes or len(part) >= MAX_BATCH_REQUESTS):
                parts.append(part)
                part, size = {}, 0
            part[cid] = entry
            size += n
        return parts + [part] if part else parts

    def send(self, batch: dict) -> None:
        from anthropic.types.messages.batch_create_params import Request

        created = []
        for part in self.split(batch):
            sent = self.client.messages.batches.create(
                requests=[Request(custom_id=cid, params=entry[0]) for cid, entry in part.items()])
            state = self.state()
            state["inflight"][sent.id] = {cid: entry[1] for cid, entry in part.items()}
            state["batches"].append({"id": sent.id, "sent_utc": now(), "requests": len(part)})
            self.save_state(state)
            self.sent += 1
            tasks: dict[str, int] = {}
            for entry in part.values():
                key = f"{entry[1]['loop']}:{entry[1]['task'].rstrip('_1234')}"
                tasks[key] = tasks.get(key, 0) + 1
            say(f"sent batch {sent.id}: {len(part)} requests {tasks}")
            created.append((sent.id, part))
        for batch_id, part in created:
            self.collect(batch_id, part)

    def collect(self, batch_id: str, batch: dict) -> None:
        results = self.fetch(batch_id)
        retry, counts = {}, {}
        for cid, (params, meta, future, attempts) in batch.items():
            result = results.get(cid) or {"type": "missing"}
            counts[result.get("type")] = counts.get(result.get("type"), 0) + 1
            if result.get("type") == "succeeded":
                self.save_reply(cid, meta, result["message"], batch_id)
                future.set_result(result["message"])
            elif attempts + 1 < self.max_attempts:
                retry[cid] = [params, meta, future, attempts + 1]
            else:
                future.set_exception(RuntimeError(f"{cid} {meta}: {json.dumps(result)[:500]}"))
        state = self.state()
        state["inflight"].pop(batch_id, None)
        entry = next(b for b in state["batches"] if b["id"] == batch_id)
        entry.update(ended_utc=now(), results=counts, spent_jpy_after=round(self.spent_jpy(), 2))
        self.save_state(state)
        say(f"batch {batch_id} ended: {counts}; spent so far JPY {entry['spent_jpy_after']:.2f} "
            f"(USD {entry['spent_jpy_after'] / rh.rs.JPY_PER_USD:.2f})")
        if retry:
            with self.lock:
                self.pending.update(retry)
                self.last_add = time.monotonic()

    def fetch(self, batch_id: str) -> dict[str, dict]:
        while True:
            batch = self.client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            time.sleep(self.poll)
        return {r.custom_id: r.result.to_dict() for r in self.client.messages.batches.results(batch_id)}


class RewriteCapExceeded(RuntimeError):
    """The guideline rewrite was cut off at the output cap on every try, so the round has no candidate."""


class QueueProvider:
    """One loop's provider: builds the request exactly as ClaudeProvider would and gets the reply via the queue."""

    def __init__(self, queue: BatchQueue, loop_id: str, method: str) -> None:
        self.queue, self.loop_id, self.method = queue, loop_id, method
        self.template = make_template()
        self.lock = threading.Lock()
        self.occurrences: dict[str, int] = {}
        self.log: list[dict] = []

    def superseded(self, message: dict) -> bool:
        """Cut off under a lower cap than the current one, so it says nothing about the current cap."""
        output = (message.get("usage") or {}).get("output_tokens") or 0
        return message.get("stop_reason") == "max_tokens" and output < self.template.max_output_tokens

    def complete(self, task: str, prompt: str) -> str:
        params = self.template.build_params(task, prompt)
        keyed = {**params, "max_tokens": KEY_MAX_TOKENS}
        base = f"{self.loop_id}|{task}|{sha(json.dumps(keyed, sort_keys=True, ensure_ascii=False))}"
        with self.lock:
            occurrence = self.occurrences.get(base, 0)
            self.occurrences[base] = occurrence + 1
        problem, tries, attempt, cutoffs = "", 0, -1, 0
        while tries < self.queue.max_attempts:
            attempt += 1
            cid = sha(f"{base}|{occurrence}|{attempt}")[:48]
            hit = self.queue.saved(cid)
            if hit and self.superseded(hit["message"]):
                continue
            tries += 1
            meta = {"loop": self.loop_id, "task": task, "occurrence": occurrence, "attempt": attempt,
                    "max_tokens": params["max_tokens"], "prompt_sha256": sha(prompt), "prompt_chars": len(prompt)}
            message = hit["message"] if hit else self.queue.request(cid, params, meta)
            reader = make_template()
            try:
                text = reader.read_message(message, task)
            except RuntimeError as exc:
                problem = str(exc)
                cutoffs += "cut off at max_tokens" in problem
            else:
                if reader.last_extraction != "unparsed":
                    with self.lock:
                        self.log.append({**meta, "custom_id": cid, "extraction": reader.last_extraction})
                    return text
                problem = "annotation reply is not JSON"
            say(f"{self.loop_id} {task}: unusable reply (try {tries}): {problem[:200]}")
            if task == "refine_guidelines" and cutoffs >= MAX_ATTEMPTS:
                break  # three rewrites cut off at the cap end the round, however many tries --max-attempts allows
        failure = f"{self.loop_id} {task}: no usable reply in {tries} tries: {problem}"
        if task == "refine_guidelines" and "cut off at max_tokens" in problem:
            raise RewriteCapExceeded(failure)
        raise RuntimeError(failure)


_published_refine = iterative._refine_guidelines_from_pairs


def concurrent_annotate(sampled_documents, guidelines, entities, provider, instructions, output_configuration):
    """iterative._annotate_documents with the documents annotated at the same time."""
    with cf.ThreadPoolExecutor(max_workers=max(1, len(sampled_documents))) as pool:
        futures = {document.filename: pool.submit(
            iterative.annotate_with_guidelines, text=document.text, guidelines=guidelines, entities=entities,
            provider=provider, instructions=instructions, output_configuration=output_configuration)
            for document in sampled_documents}
        return {name: future.result().annotations for name, future in futures.items()}


def topk_refine_concurrent(sampled_documents, predictions, current_guidelines, entities, summary, provider,
                           n_examples, *, k: int = TOPK):
    """moderate_topk.topk_refine with the k clusters handled at the same time; prompts and outputs identical."""
    clusters = summary.all_clusters[:k] or [summary.dominant_cluster]
    entity_schema = iterative._entity_schema_text(entities)
    true_positive_examples = iterative._build_true_positive_examples(sampled_documents, predictions, n_examples)
    verified_examples = iterative._build_verified_examples(sampled_documents, predictions, n_examples)

    def one_cluster(rank, cluster):
        discrepancy_examples = iterative._build_discrepant_examples_from_cluster(cluster, n_examples)
        header = f"### {rank}. {cluster.key} ({cluster.count} cases)"
        insight_prompt = render_prompt("infer_discrepancy_patterns", entity_schema=entity_schema,
                                       discrepant_examples=discrepancy_examples,
                                       true_positive_examples=true_positive_examples)
        insight = provider.complete(f"infer_discrepancy_patterns_{rank}", insight_prompt)
        discrepancy_pattern = cluster.key
        if insight.strip():
            discrepancy_pattern += f"\n\n**INFERRED PATTERNS:**\n{insight}"
        principle_prompt = render_prompt("generate_moderation_principle", entity_schema=entity_schema,
                                         discrepancy_pattern=discrepancy_pattern,
                                         discrepant_examples=discrepancy_examples)
        principle = provider.complete(f"generate_moderation_principle_{rank}", principle_prompt)
        return header, insight_prompt, insight, principle_prompt, principle

    with cf.ThreadPoolExecutor(max_workers=len(clusters)) as pool:
        done = [pool.submit(one_cluster, rank, cluster) for rank, cluster in enumerate(clusters, 1)]
        outputs = [future.result() for future in done]
    prompts: dict[str, str] = {}
    insights, principles = [], []
    for rank, (header, insight_prompt, insight, principle_prompt, principle) in enumerate(outputs, 1):
        prompts[f"infer_discrepancy_patterns_{rank}"] = insight_prompt
        insights.append(f"{header}\n{insight}")
        prompts[f"generate_moderation_principle_{rank}"] = principle_prompt
        principles.append(f"{header}\n{principle}")
    prompts["refine_guidelines"] = TOPK_TEMPLATE.format(
        guidelines=current_guidelines or "(no guidelines provided)",
        new_principles="\n\n".join(principles), verified_examples=verified_examples)
    refined_guidelines = provider.complete("refine_guidelines", prompts["refine_guidelines"])
    return refined_guidelines, "\n\n".join(insights), "\n\n".join(principles), prompts


def refine_by_method(sampled_documents, predictions, current_guidelines, entities, summary, provider, n_examples):
    if getattr(provider, "method", "top-1") == "top-4":
        return topk_refine_concurrent(sampled_documents, predictions, current_guidelines, entities, summary,
                                      provider, n_examples)
    return _published_refine(sampled_documents, predictions, current_guidelines, entities, summary, provider,
                             n_examples)


iterative._annotate_documents = concurrent_annotate
iterative._refine_guidelines_from_pairs = refine_by_method


def load_inputs():
    guidelines = GUIDELINES.read_text(encoding="utf-8")
    assert sha(guidelines).startswith(rh.rs.GUIDELINE_SHA256_PREFIX), "guideline differs from the Haiku trial's"
    split = json.loads(DEV_SPLIT.read_text(encoding="utf-8"))
    documents = [load_sampled_document(TRAIN_DIR / name) for name in split["documents"]]
    entity_rows = json.loads(ENTITY_SCHEMA.read_text(encoding="utf-8"))
    entities = [EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row) for row in entity_rows]
    return guidelines, documents, entities, entity_rows


def run_loop(queue: BatchQueue, method: str, index: int, output_root: Path, inputs, stop_at_cap: bool = False) -> dict:
    guidelines, documents, entities, entity_rows = inputs
    tag = "topk1" if method == "top-1" else f"topk{TOPK}"
    name = f"{TAG}_{tag}_loop{index:02d}"
    provider = QueueProvider(queue, f"{tag}L{index:02d}", method)
    layout = prepare_run_layout(output_root, name)

    def status(state: str, **extra) -> None:
        write_json(layout["run_root"] / "status.json", {"status": state, **extra})

    status("running")
    write_json(layout["inputs"] / "resolved_run_config.json", {
        "provider": "claude-batch", "model": rh.MODEL,
        "settings": {**rh.settings(provider.template), "max_tokens": provider.template.max_output_tokens},
        "cap_note": "max_tokens raised from 64000 to 128000 on 2026-10-22 after the first pilot's top-4 rewrite was "
                    "cut off three times; replies that ended under 64000 are reused (see the runner's RESUME note)",
        "method": method, "k": TOPK if method == "top-4" else 1, "threshold_f1": THRESHOLD_F1,
        "n_examples": N_EXAMPLES, "dev_split": str(DEV_SPLIT.relative_to(REPO_ROOT)), "loop_index": index,
        "runner": "reproduction/haiku_batch_loops.py"})
    write_json(layout["inputs"] / "sampled_train_documents.json",
               [{"filename": d.filename, "sourceid": d.sourceid, "path": d.path} for d in documents])
    (layout["inputs"] / "initial_guidelines.txt").write_text(guidelines, encoding="utf-8")
    write_json(layout["inputs"] / "entity_schema.json", entity_rows)

    accepted = {"guidelines": guidelines, "rounds": 0, "initial_f1": None, "f1": None}

    def checkpoint(snapshot) -> None:
        if accepted["initial_f1"] is None:
            accepted["initial_f1"] = snapshot.summary_before.overall_f1
        accepted.update(guidelines=snapshot.guidelines_after, rounds=snapshot.iteration,
                        f1=snapshot.summary_after.overall_f1)
        round_dir = layout["rounds"] / f"iteration_{snapshot.iteration:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        write_json(round_dir / "snapshot.json", snapshot)
        for prompt_name, prompt_text in snapshot.prompts.items():
            (round_dir / f"{prompt_name}.txt").write_text(prompt_text, encoding="utf-8")
        (round_dir / "guidelines_after.txt").write_text(snapshot.guidelines_after, encoding="utf-8")
        (round_dir / "guidelines_candidate.txt").write_text(snapshot.guidelines_candidate, encoding="utf-8")
        status("running", last_completed_iteration=snapshot.iteration)
        candidate = snapshot.summary_candidate or snapshot.summary_after
        say(f"{name} round {snapshot.iteration}: dev10 F1 {snapshot.summary_before.overall_f1:.4f} -> "
            f"{candidate.overall_f1:.4f} (candidate), improved={snapshot.improved}")

    try:
        try:
            result = iterative.run_iterative_refinement(
                sampled_documents=documents, guidelines=guidelines, entities=entities, provider=provider,
                threshold_f1=THRESHOLD_F1, n_examples=N_EXAMPLES, output_configuration=CONFIG,
                evaluation_options=PubAnnotationEvaluatorOptions(), on_iteration=checkpoint)
            write_json(layout["final"] / "iterative_refinement_run.json", result)
            final_guidelines, stop_reason, rounds = result.final_guidelines, result.stop_reason, len(result.iterations)
            initial_f1, final_f1 = result.initial_summary.overall_f1, result.final_summary.overall_f1
        except RewriteCapExceeded as exc:
            if not stop_at_cap:
                raise
            # --stop-at-cap: a round whose rewrite never fits the output cap has no candidate, so the loop ends
            # as after a rejected round, with the last accepted guideline.
            final_guidelines, stop_reason, rounds = accepted["guidelines"], "rewrite_exceeded_output_cap", accepted["rounds"]
            initial_f1, final_f1 = accepted["initial_f1"], accepted["f1"]
            write_json(layout["final"] / "stopped_at_output_cap.json", {
                "error": str(exc), "failed_round": accepted["rounds"] + 1, "accepted_rounds": accepted["rounds"],
                "final_guidelines_from": f"round {accepted['rounds']}" if accepted["rounds"] else "initial"})
        (layout["final"] / "final_guidelines.txt").write_text(final_guidelines, encoding="utf-8")
        say(f"{name} loop done: {stop_reason}, {rounds} rounds, dev10 F1 "
            f"{initial_f1 if initial_f1 is None else round(initial_f1, 4)} -> "
            f"{final_f1 if final_f1 is None else round(final_f1, 4)}")

        valid, n_valid = annotate_valid(provider, layout["run_root"], name, final_guidelines, entities, entity_rows)
        write_json(layout["run_root"] / "calls.json", provider.log)
        status("completed", stop_reason=stop_reason, iterations=rounds, initial_f1=initial_f1, final_f1=final_f1,
               valid_strict_f1=valid["f1"], valid_documents=n_valid)
        say(f"{name} valid100 strict F1 {valid['f1']:.4f}")
        return {"name": name, "valid_f1": valid["f1"]}
    except BaseException as exc:
        status("failed", error=f"{type(exc).__name__}: {exc}")
        say(f"{name} FAILED: {type(exc).__name__}: {exc}")
        return {"name": name, "error": str(exc)}


def annotate_valid(provider, run_root: Path, name: str, guidelines: str, entities, entity_rows) -> tuple[dict, int]:
    """Annotate valid100 once with one guideline and score it with strict PubAnnotation matching.

    The last step of every loop, and the whole of an E1 run, so both annotate validation alike."""
    valid_paths = sorted(VALID_DIR.glob("*.json"))
    pred_dir = run_root / "valid_predictions"
    pred_dir.mkdir(exist_ok=True)

    def one(path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        annotated = iterative.annotate_with_guidelines(
            text=raw["text"], guidelines=guidelines, entities=entities, provider=provider,
            instructions="", output_configuration=CONFIG)
        document = annotations_to_pubannotation(
            text=raw["text"], annotations=annotated.annotations, sourcedb=raw.get("sourcedb", "unknown"),
            sourceid=raw.get("sourceid", path.stem), project=raw.get("project"), target=raw.get("target"))
        (pred_dir / path.name).write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")

    with cf.ThreadPoolExecutor(max_workers=len(valid_paths)) as pool:
        for future in [pool.submit(one, p) for p in valid_paths]:
            future.result()
    labels = [row if isinstance(row, str) else row["name"] for row in entity_rows]
    scored = score_directory(VALID_DIR, pred_dir, label=name, entity_labels=labels)
    metrics = scored.as_dict()
    write_json(run_root / "valid_metrics.json", metrics)
    return metrics["strict_match"]["pubannotation"], len(valid_paths)


def run_e1(queue: BatchQueue, index: int, output_root: Path, inputs) -> dict:
    """E1: the original guideline annotated once on valid100, no refinement. Each run has its own name, so the
    replies of two runs are never shared even though their prompts are identical."""
    guidelines, _, entities, entity_rows = inputs
    name = f"{TAG}_e1_run{index:02d}"
    provider = QueueProvider(queue, f"E1R{index:02d}", "e1")
    run_root = output_root / name
    (run_root / "inputs").mkdir(parents=True, exist_ok=True)

    def status(state: str, **extra) -> None:
        write_json(run_root / "status.json", {"status": state, **extra})

    status("running")
    write_json(run_root / "inputs" / "resolved_run_config.json", {
        "provider": "claude-batch", "model": rh.MODEL,
        "settings": {**rh.settings(provider.template), "max_tokens": provider.template.max_output_tokens},
        "method": "e1 (original guideline, no refinement)", "run_index": index,
        "runner": "reproduction/haiku_batch_loops.py"})
    (run_root / "inputs" / "initial_guidelines.txt").write_text(guidelines, encoding="utf-8")
    write_json(run_root / "inputs" / "entity_schema.json", entity_rows)
    try:
        valid, n_valid = annotate_valid(provider, run_root, name, guidelines, entities, entity_rows)
        write_json(run_root / "calls.json", provider.log)
        status("completed", valid_strict_f1=valid["f1"], valid_documents=n_valid)
        say(f"{name} valid100 strict F1 {valid['f1']:.4f}")
        return {"name": name, "valid_f1": valid["f1"]}
    except BaseException as exc:
        status("failed", error=f"{type(exc).__name__}: {exc}")
        say(f"{name} FAILED: {type(exc).__name__}: {exc}")
        return {"name": name, "error": str(exc)}


def run_all(client, args, output_root: Path, quiet: float = QUIET, poll: float = POLL) -> list[dict]:
    inputs = load_inputs()
    queue = BatchQueue(output_root / f"{TAG}_batchqueue", client, args.cap_usd * rh.rs.JPY_PER_USD, quiet, poll,
                       max_attempts=getattr(args, "max_attempts", MAX_ATTEMPTS))
    queue.start()
    first = getattr(args, "first_loop", 1)
    assert first >= 1, "--first-loop starts at 1"
    loops = ([("top-1", i) for i in range(first, args.top1 + 1)]
             + [("top-4", i) for i in range(first, args.top4 + 1)])
    stop_at_cap = getattr(args, "stop_at_cap", False)
    with cf.ThreadPoolExecutor(max_workers=max(1, len(loops) + getattr(args, "e1", 0))) as pool:
        futures = [pool.submit(run_loop, queue, m, i, output_root, inputs, stop_at_cap) for m, i in loops]
        futures += [pool.submit(run_e1, queue, i, output_root, inputs) for i in range(1, getattr(args, "e1", 0) + 1)]
        outcomes = [f.result() for f in futures]
    spent = queue.spent_jpy()
    say(f"all loops returned; batches sent this session {queue.sent}; total spent JPY {spent:.2f} "
        f"(USD {spent / rh.rs.JPY_PER_USD:.2f})")
    return outcomes


def cmd_dry_run(args) -> None:
    guidelines, documents, entities, _ = load_inputs()
    trial = {u["doc"]: u["prompt_sha256"] for u in rh.rs.load_units(rh.UNITS) if u["arm"] == ARM}
    first = {d.filename: rh.rs.render_prompt(d, guidelines, entities) for d in documents}
    same = sorted(trial) == sorted(first) and all(sha(first[f]) == trial[f] for f in first)
    print(f"first-step annotation prompts identical to the Haiku trial's H_xhigh prompts: {same}")
    params = make_template().build_params("annotate_with_guidelines", first[documents[0].filename])
    params["messages"] = "<prompt>"
    params["output_config"]["format"] = "<annotation schema>"
    print(f"annotation request: {json.dumps(params)}")
    print(f"top-4 rewrite template = published + one conflict instruction: "
          f"{len(PROMPT_TEMPLATES['refine_guidelines'])} -> {len(TOPK_TEMPLATE)} chars")
    loops = max(0, args.top1 - args.first_loop + 1) + max(0, args.top4 - args.first_loop + 1)
    print(f"loops {args.first_loop:02d} to {args.top1:02d} of top-1 and {args.first_loop:02d} to {args.top4:02d} of "
          f"top-4 ({loops} loops), E1 x{args.e1}; first batch {10 * loops + 100 * args.e1} requests; "
          f"max attempts {args.max_attempts}; cap USD {args.cap_usd:.2f} (JPY {args.cap_usd * rh.rs.JPY_PER_USD:.0f})")
    print(f"outputs: {OUTPUT_ROOT.relative_to(REPO_ROOT)}/{TAG}_topk1_loopNN, _topk{TOPK}_loopNN, _e1_runNN, "
          f"_batchqueue")
    print(f"ANTHROPIC_API_KEY present: {rh.load_key()}")


def cmd_run(args) -> None:
    if not args.yes:
        sys.exit("not sent: add --yes")
    if not rh.load_key():
        sys.exit("ANTHROPIC_API_KEY is not set")
    import anthropic

    run_all(anthropic.Anthropic(max_retries=4), args, OUTPUT_ROOT)


HASH_SEED = "0"


def main() -> None:
    if os.environ.get("PYTHONHASHSEED") != HASH_SEED:
        # iterative._build_true_positive_examples lists matched annotations in set order, and set order follows
        # string hashing, which Python randomises per process. Without a fixed seed the same loop writes
        # different analysis prompts after a restart, so its saved replies no longer match (found 2026-10-22).
        import subprocess

        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONHASHSEED": HASH_SEED}))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("dry-run", "run"):
        p = sub.add_parser(name)
        p.add_argument("--top1", type=int, default=1, help="last top-1 loop number (loops are numbered from 1)")
        p.add_argument("--top4", type=int, default=1, help="last top-4 loop number (loops are numbered from 1)")
        p.add_argument("--first-loop", type=int, default=1,
                       help="first loop number to run for both methods; lower-numbered loops are not touched")
        p.add_argument("--e1", type=int, default=0, help="E1 runs: the original guideline annotated on valid100")
        p.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS,
                       help="tries per call, counting saved replies; a rewrite cut off at the cap three times still "
                            "ends the round")
        p.add_argument("--cap-usd", type=float, default=2.00, help="no batch is sent once spend reaches this")
        p.add_argument("--stop-at-cap", action="store_true",
                       help="end a loop as after a rejected round when its rewrite is cut off at the cap on every try")
        p.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    {"dry-run": cmd_dry_run, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    main()
