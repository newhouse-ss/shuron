"""Read batches, transcribe human-selected line ranges, and validate locating output.

No citation-to-guideline search or automatic locating is performed.
"""
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'todo-temp/error-analysis/outputs/bar_clause_pilot/codex_locate'
OUT = BASE / 'outputs'
SOURCE = BASE / 'inputs/top4_loop04_predictions.jsonl'
GUIDE = BASE / 'inputs/guidelines/top4_loop04.txt'
TARGET = OUT / 'top4_loop04_locate.jsonl'

def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def norm(text):
    return ' '.join(text.replace('*', '').replace('_', '').split())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def progress(rows):
    path = OUT / 'progress.json'
    p = json.loads(path.read_text(encoding='utf-8'))
    counts = collections.Counter(r['status'] for r in rows)
    p['current_guideline'] = 'top4_loop04'
    p['next_input_row'] = len(rows) + 1
    p['task'] = 'locating_only'
    p['guidelines']['top4_loop04'] = dict(total=281, written=len(rows),
        located=counts['located'], cannot_locate=counts['cannot_locate'],
        batches=(len(rows)+19)//20, phase1_complete=len(rows)==281,
        complete=len(rows)==281, last_pred_id=rows[-1]['pred_id'] if rows else None,
        input_sha256=digest(SOURCE))
    path.write_text(json.dumps(p, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    command = sys.argv[1]
    inputs = read_jsonl(SOURCE)
    lines = GUIDE.read_text(encoding='utf-8').splitlines(keepends=True)
    if command == 'init':
        assert len(inputs) == 281
        assert not TARGET.exists(), 'Existing output must not be overwritten'
        progress([])
        with (OUT / 'session_log.md').open('a', encoding='utf-8') as f:
            f.write('\n\n## 2026-11-06 top4_loop04 定位会话\n\n'
                '本次使用 reasoning effort high。仅按文件顺序每批 20 条定位 top4_loop04，共 281 条，末批 1 条。已先通读完整指南。无 API 或网络调用。\n\n'
                '适用限制：本次用户指定 top4_loop04，优先于规范默认顺序与旧执行者列表；用户明确授权更新 progress.json、追加目标 JSONL 和 session_log.md，优先于规范禁止修改已有文件的通则。盲读限制优先于 AGENTS.md 要求读取 PROGRESS.md、LOG.md 及更新 LOG.md，本次不打开或修改这些文件。\n\n'
                '检查器限制：已有 check_quotes.py 位于本次允许读取范围之外，因此未读取或运行该文件；在获准脚本目录新建本会话检查器，检查相同要求及顺序、引用片段覆盖。只按人工阅读后指定的行号抄录，不进行引用或理由到指南的自动匹配。\n')
        print('Initialized top4_loop04, 281 inputs')
    elif command == 'show':
        start = int(sys.argv[2])
        for i, r in enumerate(inputs[start-1:start+19], start):
            print(json.dumps(dict(row=i, pred_id=r['pred_id'], text=r['pred_text'],
                label=r['pred_label'], context=r['context'], citation=r['guideline_section'],
                rationale=r['rationale']), ensure_ascii=False))
    elif command == 'append':
        decisions = json.loads(sys.stdin.read().lstrip('\ufeff'))
        existing = read_jsonl(TARGET) if TARGET.exists() else []
        start = len(existing)
        assert len(decisions) == min(20, len(inputs)-start)
        result = []
        for r, decision in zip(inputs[start:], decisions):
            fragments = [x.strip() for x in r['guideline_section'].split(';') if x.strip()]
            quotes = []
            for choice in decision['q']:
                a, b, fragment, condition, role = choice
                assert 1 <= a <= b <= len(lines)
                quote = ''.join(lines[a-1:b]).rstrip('\r\n')
                assert norm(condition) in norm(quote)
                cited = fragments[fragment] if isinstance(fragment, int) and fragment >= 0 else fragment if isinstance(fragment, str) else ''
                quotes.append(dict(quote=quote,line_start=a,line_end=b,
                    condition_words=condition,role=role,cited_as=cited))
            note = decision.get('n', '')
            assert len(note.split()) <= 20
            result.append(dict(pred_id=r['pred_id'], status='located' if quotes else 'cannot_locate', quotes=quotes,note=note))
        with TARGET.open('a', encoding='utf-8', newline='\n') as f:
            for r in result:
                f.write(json.dumps(r,ensure_ascii=False)+'\n')
        progress(existing+result)
        print(f'Appended rows {start+1}-{start+len(result)}')
    elif command == 'repair_citation_metadata':
        # These seven assignments were selected after re-reading each source row
        # and the already-located guideline passages. No locating text changes.
        rows = read_jsonl(TARGET)
        repairs = {
            13: {0: [0,1], 1: []},
            15: {0: [0,1], 1: [], 2: [1]},
            28: {2: [1]},
            29: {1: [1]},
            43: {0: [0,1]},
            183: {0: [0,1], 1: [1]},
            265: {1: [1]},
        }
        for number, assignments in repairs.items():
            fragments = [x.strip() for x in inputs[number-1]['guideline_section'].split(';') if x.strip()]
            for index, selected in assignments.items():
                rows[number-1]['quotes'][index]['cited_as'] = '; '.join(fragments[i] for i in selected)
        TARGET.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
        with (OUT/'session_log.md').open('a',encoding='utf-8') as f:
            f.write('\n初检发现第 13、15、28、29、43、183、265 条的 cited_as 未覆盖括号内分号后的片段。已重新阅读这七条输入及指南第 66 至 80、87 至 103、112 至 120、203、236 至 237 行，修正本会话新建输出的引用片段元数据。原定位文本、行号、角色、条件词、条目顺序和条数均未变；未修改任何其他指南输出。\n')
        print('Repaired citation metadata for seven re-read rows')
    elif command == 'check':
        rows = read_jsonl(TARGET)
        errors = []
        if [r['pred_id'] for r in rows] != [r['pred_id'] for r in inputs]:
            errors.append('IDs are incomplete, duplicated, or out of order')
        for i, (source, row) in enumerate(zip(inputs,rows),1):
            if source['pred_text'] not in source['context']:
                errors.append(f'{i}: context lacks predicted text')
            if row['status'] not in ('located','cannot_locate'):
                errors.append(f'{i}: invalid status')
            if (row['status']=='located') != bool(row['quotes']):
                errors.append(f'{i}: status/quotes mismatch')
            if len(row['note'].split()) > 20 or (row['status']=='cannot_locate' and not row['note']):
                errors.append(f'{i}: invalid note')
            for q in row['quotes']:
                a,b = q['line_start'],q['line_end']
                if not 1<=a<=b<=len(lines) or not norm(q['quote']) or norm(q['quote']) not in norm(''.join(lines[a-1:b])):
                    errors.append(f'{i}: invalid quote or lines')
                if norm(q['condition_words']) not in norm(q['quote']):
                    errors.append(f'{i}: invalid condition_words')
                if q['role'] not in ('basis','ruled_out','context'):
                    errors.append(f'{i}: invalid role')
            for fragment in source['guideline_section'].split(';'):
                fragment=fragment.strip()
                if fragment and not any(fragment in q['cited_as'] for q in row['quotes']) and not row['note']:
                    errors.append(f'{i}: unexplained citation fragment {fragment}')
        counts=collections.Counter(r['status'] for r in rows)
        roles=collections.Counter(q['role'] for r in rows for q in r['quotes'])
        report=dict(guideline='top4_loop04',input_count=len(inputs),output_count=len(rows),
            statuses={s:counts[s] for s in ('located','cannot_locate')},roles=dict(roles),errors=errors,
            sha256={p.name:digest(p) for p in (SOURCE,GUIDE,TARGET)},
            reasoning_effort='high',batch_size=20)
        (OUT/'top4_loop04_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        sys.exit(bool(errors))
    elif command == 'finish_log':
        report = json.loads((OUT/'top4_loop04_checks.json').read_text(encoding='utf-8'))
        assert not report['errors'] and report['output_count']==281
        hashes={p.name:digest(p) for p in (TARGET,OUT/'top4_loop04_checks.json',OUT/'progress.json',Path(__file__))}
        receipt=dict(guideline='top4_loop04',reasoning_effort='high',batches=15,
            batch_rows='1-20, 21-40, 41-60, 61-80, 81-100, 101-120, 121-140, 141-160, 161-180, 181-200, 201-220, 221-240, 241-260, 261-280, 281',
            statuses=report['statuses'],roles=report['roles'],checks_passed=True,sha256=hashes)
        (OUT/'top4_loop04_session_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        with (OUT/'session_log.md').open('a',encoding='utf-8') as f:
            f.write('\n完成：281/281 条，15 批（前 14 批各 20 条，末批 1 条），located 281，cannot_locate 0。角色计数：basis 537，context 19，ruled_out 8。本次使用 reasoning effort high。仅定位，无合并、条目文件或收益损失汇总。\n\n'
                '最终检查通过：ID 完整且各一次、文件顺序一致；预测文本均在给定上下文中；引用在指定指南行内符合规范化原文；条件词为引用子串；状态、角色和 note 合规；所有分号引用片段均有记录或说明。检查命令：`python todo-temp/error-analysis/scripts/codex_locate/loop04_session.py check`。progress.json 当前指南为 top4_loop04，written 为 281，next_input_row 为 282。\n\n'
                '实现记录：首批写入前，PowerShell 管道带 BOM 导致 JSON 读取失败，未产生部分输出；读取端支持 BOM 后同一批成功追加。所有批次追加后，仅修正上述七条引用元数据。\n\n输出 SHA256：\n\n')
            for name,value in hashes.items():
                f.write(f'- `{name}`: `{value}`\n')
        print('Final checks and hashes appended to session_log.md')

if __name__ == '__main__':
    main()
