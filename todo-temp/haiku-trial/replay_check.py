"""Before restarting top-4: what would a restart send, and is it the same in every process? Offline.

Each check copies outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue to a temporary folder and runs the top-4
loop (--top1 0 --top4 1) in a fresh Python process against a fake client that records the first batch and then
refuses, so nothing is sent anywhere. Printed per process: the hash seed and, for each request of that first
batch, its task, max_tokens and prompt hash.

Expected: the dev10 annotations replay from the saved replies (the first batch holds no annotation request), the
first batch is the 4 discrepancy calls at max_tokens 128000, and two processes with PYTHONHASHSEED=0 write
byte-identical prompts, while seeds 0 and 1 differ (the set-order effect that broke the first replay check).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def child() -> None:
    sys.path.insert(0, str(ROOT / "reproduction"))
    import haiku_batch_loops as hb  # noqa: E402

    source = ROOT / "outputs/ncbi_disease" / f"{hb.TAG}_batchqueue"
    batches = []

    class Recorder:
        def create(self, requests):
            batches.append([r["params"] for r in requests])
            raise RuntimeError("replay check: nothing is sent")

    tmp = Path(tempfile.mkdtemp(prefix="replay_check_"))
    try:
        shutil.copytree(source, tmp / source.name)
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            hb.run_all(SimpleNamespace(messages=SimpleNamespace(batches=Recorder())),
                       SimpleNamespace(top1=0, top4=1, cap_usd=2.00), tmp, quiet=1.0, poll=0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rows = []
    for params in batches[0] if batches else []:
        prompt = params["messages"][0]["content"]
        task = ("annotation" if "format" in params["output_config"] else
                "rewrite" if "NEW MODERATION PRINCIPLES" in prompt else
                "principle" if "ONE Core Moderation Principle" in prompt else "discrepancy")
        rows.append((task, params["max_tokens"], hb.sha(prompt)[:12]))
    print(json.dumps(sorted(rows)))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        child()
        return
    results = {}
    for label, seed in (("seed 0, process A", "0"), ("seed 0, process B", "0"), ("seed 1", "1")):
        out = subprocess.run([sys.executable, __file__, "child"], env={**os.environ, "PYTHONHASHSEED": seed},
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        results[label] = json.loads(out)
        print(f"{label}: first batch {len(results[label])} requests: {results[label]}")
    print(f"seed 0 identical across processes: {results['seed 0, process A'] == results['seed 0, process B']}")
    print(f"seed 0 vs seed 1 identical: {results['seed 0, process A'] == results['seed 1']}")


if __name__ == "__main__":
    main()
