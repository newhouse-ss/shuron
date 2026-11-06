"""Read batches and serialize manually selected guideline spans. No locating logic."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path('todo-temp/error-analysis/outputs/bar_clause_pilot/codex_locate')
OUT = ROOT / 'outputs'
PREFIX = 'top4_loop06'
INPUT = ROOT / 'inputs' / f'{PREFIX}_predictions.jsonl'
GUIDE = ROOT / 'inputs/guidelines' / f'{PREFIX}.txt'
TARGET = OUT / f'{PREFIX}_locate.jsonl'

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalize(value):
    return ' '.join(value.replace('*', '').replace('_', '').split())

def progress(rows, complete=False):
    path = OUT / 'progress.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    counts = collections.Counter(row['status'] for row in rows)
    data['guidelines'][PREFIX] = dict(total=305, written=len(rows),
        located=counts['located'], cannot_locate=counts['cannot_locate'],
        batches=(len(rows) + 19) // 20, phase1_complete=complete, complete=complete,
        last_pred_id=rows[-1]['pred_id'] if rows else None, input_sha256=digest(INPUT))
    data.update(current_guideline=PREFIX, next_input_row=len(rows)+1, task='locating_only', phase=1)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def check(complete):
    inputs = read_jsonl(INPUT)
    rows = read_jsonl(TARGET) if TARGET.exists() else []
    lines = GUIDE.read_text(encoding='utf-8').splitlines()
    errors = []
    for i, item in enumerate(inputs, 1):
        if '[['+item['pred_text']+']]' not in item['context']:
            errors.append(f'input {i}: context does not contain marked prediction')
    expected = [row['pred_id'] for row in inputs[:len(rows)]]
    if [row['pred_id'] for row in rows] != expected:
        errors.append('output IDs differ from ordered input prefix')
    if complete and len(rows) != len(inputs):
        errors.append('incomplete output')
    if len(set(row['pred_id'] for row in rows)) != len(rows):
        errors.append('duplicate output IDs')
    for i, (row, source) in enumerate(zip(rows, inputs), 1):
        if row['status'] not in ('located', 'cannot_locate'):
            errors.append(f'{i}: invalid status')
        if row['status'] == 'located' and not row['quotes']:
            errors.append(f'{i}: located without quotes')
        if row['status'] == 'cannot_locate' and (row['quotes'] or not row['note']):
            errors.append(f'{i}: invalid cannot_locate')
        if len(row['note'].split()) > 20:
            errors.append(f'{i}: note exceeds 20 words')
        for quote in row['quotes']:
            start, end = quote['line_start'], quote['line_end']
            if not 1 <= start <= end <= len(lines):
                errors.append(f'{i}: invalid line range')
                continue
            if normalize(quote['quote']) not in normalize('\n'.join(lines[start-1:end])):
                errors.append(f'{i}: quote not in selected lines')
            if normalize(quote['condition_words']) not in normalize(quote['quote']):
                errors.append(f'{i}: condition not in quote')
            if quote['role'] not in ('basis', 'ruled_out', 'context'):
                errors.append(f'{i}: invalid role')
        # This checks coverage only, never selects a guideline location.
        for fragment in source['guideline_section'].split(';'):
            fragment = fragment.strip()
            if fragment and not any(fragment in q['cited_as'] for q in row['quotes']) and not row['note']:
                errors.append(f'{i}: unexplained citation fragment')
    result = dict(guideline=PREFIX, input_count=len(inputs), output_count=len(rows),
        status_counts=dict(collections.Counter(row['status'] for row in rows)),
        quote_roles=dict(collections.Counter(q['role'] for r in rows for q in r['quotes'])),
        errors=errors, passed=not errors, complete=complete,
        input_sha256=digest(INPUT), guideline_sha256=digest(GUIDE),
        output_sha256=digest(TARGET) if TARGET.exists() else None)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['init','read','append','check'])
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--plan')
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    if args.mode == 'init':
        rows = read_jsonl(TARGET) if TARGET.exists() else []
        progress(rows)
        print(json.dumps({'existing_rows': len(rows), 'input_count':len(read_jsonl(INPUT))}))
    elif args.mode == 'read':
        for i, row in enumerate(read_jsonl(INPUT)[args.start-1:args.start+19], args.start):
            print(json.dumps(dict(row=i, **row), ensure_ascii=False))
    elif args.mode == 'append':
        inputs = read_jsonl(INPUT)
        lines = GUIDE.read_text(encoding='utf-8').splitlines()
        existing = read_jsonl(TARGET) if TARGET.exists() else []
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
        assert len(plan) == min(20, len(inputs)-len(existing))
        batch = []
        for index, selections, note in plan:
            assert index == len(existing)+len(batch)+1
            quotes = []
            for selection in selections:
                start, end, citation, role, condition, *literal = selection
                quote = literal[0] if literal else '\n'.join(lines[start-1:end])
                quotes.append(dict(quote=quote,line_start=start,line_end=end,
                    condition_words=condition, role=role,cited_as=citation))
            batch.append(dict(pred_id=inputs[index-1]['pred_id'],
                status='located' if quotes else 'cannot_locate',quotes=quotes,note=note))
        with TARGET.open('a', encoding='utf-8', newline='\n') as handle:
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False)+'\n')
        result = check(False)
        assert result['passed'], result['errors']
        progress(existing+batch)
        print(json.dumps({'appended':len(batch),'written':len(existing)+len(batch),'checks':'passed'}))
    else:
        result = check(args.complete)
        (OUT / f'{PREFIX}_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if result['passed'] and args.complete:
            progress(read_jsonl(TARGET), True)
        print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    main()
