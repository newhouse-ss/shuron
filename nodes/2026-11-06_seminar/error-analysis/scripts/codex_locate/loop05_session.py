"""Mechanical IO and validation only; all line selections are supplied by a reader."""
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate'
OUT = BASE / 'outputs'
SOURCE = BASE / 'inputs/top4_loop05_predictions.jsonl'
GUIDE = BASE / 'inputs/guidelines/top4_loop05.txt'
TARGET = OUT / 'top4_loop05_locate.jsonl'

def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def log(message):
    with (OUT / 'session_log.md').open('a', encoding='utf-8') as f:
        f.write(message + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def progress(rows, predictions):
    path = OUT / 'progress.json'
    p = json.loads(path.read_text(encoding='utf-8-sig'))
    p.update(current_guideline='top4_loop05', next_input_row=len(rows)+1, task='locating_only')
    counts = collections.Counter(r['status'] for r in rows)
    p['guidelines']['top4_loop05'] = dict(total=len(predictions), written=len(rows),
        located=counts['located'], cannot_locate=counts['cannot_locate'],
        batches=(len(rows)+19)//20, phase1_complete=len(rows)==len(predictions),
        complete=len(rows)==len(predictions), last_pred_id=rows[-1]['pred_id'] if rows else None,
        input_sha256=sha(SOURCE))
    dump(path, p)

def norm(s):
    return ' '.join(s.replace('*', '').replace('_', '').split())

predictions = read_jsonl(SOURCE)
lines = GUIDE.read_text(encoding='utf-8').splitlines()
mode = sys.argv[1]
if mode == 'init':
    assert not TARGET.exists(), 'Output already exists; do not overwrite.'
    progress([], predictions)
    log('\n## 2026-11-06 top4_loop05 locating only\n\n本次使用 reasoning effort high。仅处理 top4_loop05，按输入顺序每批 20 条，最后一批 18 条。已先完整阅读 guideline。无 API 或网络调用，无自动文本定位。\n\n适用例外：本次用户指令优先于 spec 的执行顺序和禁止修改既有文件条款，仅更新指定 progress.json 并追加 session_log.md。AGENTS.md 已按要求读取；未读取 PROGRESS.md、LOG.md、OVERVIEW.md，以遵守盲法范围。既有 checker 位于允许读取范围外，故在本次专用脚本中实现结构检查，不读取既有脚本。')
    print(json.dumps({'total': len(predictions), 'guideline_lines': len(lines)}))
elif mode == 'read':
    start = int(sys.argv[2])
    for i, p in enumerate(predictions[start-1:start+19], start):
        print(json.dumps({'row': i, **p}, ensure_ascii=False))
elif mode == 'append':
    batch = json.loads(sys.stdin.read().lstrip('\ufeff'))
    rows = read_jsonl(TARGET) if TARGET.exists() else []
    start = len(rows)
    assert len(batch) == min(20, len(predictions)-start)
    new = []
    for offset, entry in enumerate(batch):
        p = predictions[start+offset]
        assert entry['row'] == start+offset+1
        assert '[[' + p['pred_text'] + ']]' in p['context'], p['pred_id']
        fragments = [s.strip() for s in p['guideline_section'].split(';')]
        quotes = []
        for selection in entry['q']:
            a, b, ci = selection[:3]
            role = selection[3] if len(selection)>3 else 'basis'
            condition = selection[4] if len(selection)>4 else ''
            citation = fragments[ci] if isinstance(ci, int) else ci
            quote = '\n'.join(lines[a-1:b])
            assert condition == '' or norm(condition) in norm(quote)
            quotes.append(dict(quote=quote, line_start=a, line_end=b,
                condition_words=condition, role=role, cited_as=citation))
        note = entry.get('note', '')
        assert len(note.split()) <= 20
        new.append(dict(pred_id=p['pred_id'], status='located' if quotes else 'cannot_locate', quotes=quotes, note=note))
    with TARGET.open('a', encoding='utf-8', newline='\n') as f:
        for r in new:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rows.extend(new)
    progress(rows, predictions)
    print(json.dumps({'appended': len(new), 'written': len(rows)}))
elif mode == 'check':
    rows = read_jsonl(TARGET)
    errors = []
    ids = [p['pred_id'] for p in predictions]
    if [r['pred_id'] for r in rows] != ids:
        errors.append('Input IDs not present exactly once in file order')
    roles = collections.Counter()
    statuses = collections.Counter()
    for i, (p, r) in enumerate(zip(predictions, rows), 1):
        if '[[' + p['pred_text'] + ']]' not in p['context']:
            errors.append(f'{i}: context lacks marked prediction')
        statuses[r['status']] += 1
        if r['status'] not in ('located', 'cannot_locate'):
            errors.append(f'{i}: invalid status')
        if bool(r['quotes']) != (r['status']=='located'):
            errors.append(f'{i}: status/quotes inconsistent')
        if len(r['note'].split())>20 or (r['status']=='cannot_locate' and not r['note']):
            errors.append(f'{i}: invalid note')
        for q in r['quotes']:
            a, b = q['line_start'], q['line_end']
            if not 1 <= a <= b <= len(lines) or norm(q['quote']) not in norm('\n'.join(lines[a-1:b])):
                errors.append(f'{i}: invalid quotation')
            if norm(q['condition_words']) not in norm(q['quote']):
                errors.append(f'{i}: invalid condition')
            roles[q['role']] += 1
            if q['role'] not in ('basis', 'ruled_out', 'context'):
                errors.append(f'{i}: invalid role')
        for fragment in p['guideline_section'].split(';'):
            if fragment.strip() not in [q['cited_as'] for q in r['quotes']] and not r['note']:
                errors.append(f'{i}: unexplained citation fragment: {fragment.strip()}')
    result = dict(guideline='top4_loop05', input_count=len(predictions), output_count=len(rows),
        status_counts=dict(statuses), quote_roles=dict(roles), errors=errors,
        passed=not errors, output_sha256=sha(TARGET), input_sha256=sha(SOURCE), guideline_sha256=sha(GUIDE))
    dump(OUT / 'top4_loop05_checks.json', result)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(bool(errors))
elif mode == 'review':
    # Explicit reader-supplied corrections, with no text-to-rule search.
    rows = read_jsonl(TARGET)
    changes = json.loads(sys.stdin.read().lstrip('\ufeff'))
    for item in changes['quotes']:
        row, index, a, b = item[:4]
        q = rows[row-1]['quotes'][index]
        q.update(quote='\n'.join(lines[a-1:b]), line_start=a, line_end=b)
        if len(item)>4:
            q['condition_words'] = item[4]
        assert norm(q['condition_words']) in norm(q['quote']), (row, index)
    for row, note in changes.get('notes', []):
        assert len(note.split()) <= 20
        rows[row-1]['note'] = note
    for row, index, role in changes.get('roles', []):
        assert role in ('basis', 'ruled_out', 'context')
        rows[row-1]['quotes'][index]['role'] = role
    with TARGET.open('w', encoding='utf-8', newline='\n') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed_quote_metadata': len(changes['quotes']), 'reviewed_notes': len(changes.get('notes', []))}))
elif mode == 'finish':
    checks = json.loads((OUT / 'top4_loop05_checks.json').read_text(encoding='utf-8'))
    assert checks['passed'] and checks['output_count'] == 238
    receipt = dict(guideline='top4_loop05', reasoning_effort='high', batches=12,
        batch_sizes=[20]*11+[18], written=238, located=238, cannot_locate=0,
        quote_roles=checks['quote_roles'], checks_passed=True, network_calls=0,
        locating_method='Manual reading; explicit line selections only',
        hashes={str(path.relative_to(ROOT)).replace('\\', '/'): sha(path)
                for path in [SOURCE, GUIDE, TARGET, OUT/'top4_loop05_checks.json', OUT/'progress.json', Path(__file__)]})
    dump(OUT / 'top4_loop05_session_receipt.json', receipt)
    log('\n完成记录：238/238 条均 located，cannot_locate 为 0。按文件顺序完成 12 批，前 11 批各 20 条，末批 18 条。引文角色计数：basis 343，ruled_out 7，context 2。仅定位，没有合并、收益损失聚合或 items 文件。其他 guideline 输出未改动。\n\n检查命令：`python nodes/2026-11-06_seminar/error-analysis/scripts/codex_locate/loop05_session.py check`。最终通过：所有输入 ID 按顺序恰好出现一次；所有 context 包含预测文本标记；所有引文在指定行内逐字出现；规范化仅移除星号和下划线并折叠空白；条件词均为引文子串；状态、角色、备注长度及 citation 分片覆盖检查通过。\n\n修正记录：首次检查发现第 85 条 citation 在括号内由分号切成 `patient-anchored)` 片段，复读输入后用备注说明其承接同一 Section 1 引用。复读 guideline 后缩短 33 处引文范围，补充明确的条件词，并将第 7 条中被 rationale 用于 inherited reading 的遗传语境规则标为 basis。只修正本次新建输出，未删除或重排预测。第 2 批和第 6 批各出现一次条件词子串校验失败，发生在追加前，无部分写入；复读原句并重新选择其原文条件词后成功写入。progress.json 当前为 top4_loop05，written 238，next_input_row 239。\n\n本次使用 reasoning effort high。输出哈希如下：\n')
    for path, digest in receipt['hashes'].items():
        log(f'- `{path}`: `{digest}`')
    print(json.dumps({'receipt': 'top4_loop05_session_receipt.json', 'logged': True}))
