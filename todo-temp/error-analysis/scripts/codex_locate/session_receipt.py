"""Check saved work and record session counts and file hashes, without locating."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


SCRIPTS = Path(__file__).resolve().parent
BASE = SCRIPTS.parents[1] / "outputs" / "bar_clause_pilot" / "codex_locate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--append-log", action="store_true")
    args = parser.parse_args()
    output = BASE / "outputs"
    progress = json.loads((output / "progress.json").read_text(encoding="utf-8"))
    manifest = json.loads((BASE / "inputs" / "manifest.json").read_text(encoding="utf-8"))
    checks = []
    summaries = []
    failed = False
    for prefix in progress["order"]:
        path = output / f"{prefix}_locate.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        total = manifest["counts"][prefix]["distinct_predictions"]
        roles = Counter(quote["role"] for record in records for quote in record["quotes"])
        counts = Counter(record["status"] for record in records)
        check_status = "not_started"
        if records:
            command = [sys.executable, "-B", str(SCRIPTS / "check_quotes.py"), "--prefix", prefix]
            if len(records) != total:
                command.append("--allow-partial")
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            checks.append(result.stdout.strip() or result.stderr.strip())
            check_status = "PASS" if result.returncode == 0 else "FAIL"
            failed |= result.returncode != 0
        item_path = output / f"{prefix}_items.csv"
        items = list(csv.DictReader(item_path.open(encoding="utf-8", newline=""))) if item_path.exists() else []
        summaries.append({
            "guideline": prefix, "total": total, "written": len(records),
            "located": counts["located"], "cannot_locate": counts["cannot_locate"],
            "quotes_by_role": {role: roles[role] for role in ["basis", "ruled_out", "context"]},
            "items": len(items), "phase1_complete": len(records) == total,
            "phase2_complete": progress["guidelines"].get(prefix, {}).get("phase2_complete", False),
            "checker": check_status,
        })
    timestamp = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    summary = {"timestamp": timestamp, "guidelines": summaries,
               "phase3": {"status": "not_started", "reason": "All eleven guidelines must finish Phases 1 and 2 first."},
               "part_b": "not_started", "network_calls": 0}
    (output / "session_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "session_checks.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    if args.append_log:
        rows = [f"\n### 会话结束检查（{timestamp}）\n",
                "\n完整 guideline 使用完整检查，未完成 guideline 只检查已保存记录。Phase 3 和 Part B 尚未开始。\n",
                "\n| Guideline | 已保存 / 总数 | located | cannot_locate | basis | ruled_out | context | items | Phase 2 | 检查 |\n",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"]
        for record in summaries:
            roles = record["quotes_by_role"]
            rows.append(f"| {record['guideline']} | {record['written']} / {record['total']} | {record['located']} | {record['cannot_locate']} | {roles['basis']} | {roles['ruled_out']} | {roles['context']} | {record['items']} | {'完成' if record['phase2_complete'] else '未完成'} | {record['checker']} |\n")
        rows.append("\n所有生成输出和脚本的 SHA256 记录在 session_hashes.json，检查原始输出记录在 session_checks.txt。session_hashes.json 不包含自身的哈希。\n")
        for record in summaries:
            if record["written"]:
                for suffix in ["locate.jsonl", "items.csv", "quote_to_item.csv"]:
                    path = output / f"{record['guideline']}_{suffix}"
                    if path.exists():
                        rows.append(f"\n{path.name}: `{digest(path)}`\n")
        with (output / "session_log.md").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("".join(rows))
    hashes = {str(path.relative_to(output)).replace("\\", "/"): digest(path)
              for path in sorted(output.rglob("*")) if path.is_file() and path.name != "session_hashes.json"}
    script_hashes = {path.name: digest(path) for path in sorted(SCRIPTS.glob("*.py"))}
    receipt = {"algorithm": "sha256", "outputs": hashes, "scripts": script_hashes,
               "inputs_manifest_sha256": digest(BASE / "inputs" / "manifest.json")}
    (output / "session_hashes.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(checks))
    print(f"Saved session receipt: {sum(record['written'] for record in summaries)} predictions, {len(hashes)} output files")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
