"""Blind I/O and validation only. All line selections are supplied by the reader."""
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'outputs/bar_clause_pilot/codex_locate'
INPUT = ROOT / 'inputs'
OUTPUT = ROOT / 'outputs'
PREFIX = 'top4_loop02'

def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]

def norm(text):
    return ' '.join(text.replace('*', '').replace('_', '').split())

def check(complete=False):
    source = read_jsonl(INPUT / (PREFIX + '_predictions.jsonl'))
    result = read_jsonl(OUTPUT / (PREFIX + '_locate.jsonl'))
    lines = (INPUT / 'guidelines' / (PREFIX + '.txt')).read_text(encoding='utf-8').splitlines()
    errors = []
    if [r['pred_id'] for r in result] != [r['pred_id'] for r in source[:len(result)]]:
        errors.append('Output IDs are not the input prefix in file order')
    if any(n != 1 for n in collections.Counter(r['pred_id'] for r in source).values()):
        errors.append('Duplicate input IDs')
    if any(n != 1 for n in collections.Counter(r['pred_id'] for r in result).values()):
        errors.append('Duplicate output IDs')
    if complete and len(source) != len(result):
        errors.append('Incomplete output')
    roles = collections.Counter()
    statuses = collections.Counter()
    for i, (prediction, row) in enumerate(zip(source, result), 1):
        statuses[row['status']] += 1
        if prediction['pred_text'] not in prediction['context'].replace('[[', '').replace(']]', ''):
            errors.append(f'{i}: predicted text absent from context')
        if row['status'] not in ('located', 'cannot_locate'):
            errors.append(f'{i}: invalid status')
        if (row['status'] == 'located') != bool(row['quotes']):
            errors.append(f'{i}: status/quotes mismatch')
        if len(row['note'].split()) > 20 or (row['status'] == 'cannot_locate' and not row['note']):
            errors.append(f'{i}: invalid note')
        for q in row['quotes']:
            roles[q['role']] += 1
            start, end = q['line_start'], q['line_end']
            if not norm(q['quote']):
                errors.append(f'{i}: empty quote')
            if not (1 <= start <= end <= len(lines)) or norm(q['quote']) not in norm('\n'.join(lines[start-1:end])):
                errors.append(f'{i}: quote mismatch at {start}:{end}')
            if norm(q['condition_words']) not in norm(q['quote']):
                errors.append(f'{i}: condition mismatch')
            if q['role'] not in ('basis', 'ruled_out', 'context'):
                errors.append(f'{i}: invalid role')
        for fragment in prediction['guideline_section'].split(';'):
            if fragment.strip() and not any(fragment.strip() in q['cited_as'] for q in row['quotes']) and not row['note']:
                errors.append(f'{i}: citation fragment omitted')
    summary = dict(total=len(source), written=len(result), statuses=dict(statuses), roles=dict(roles), errors=errors)
    print(json.dumps(summary, ensure_ascii=False))
    return summary

def progress(summary):
    path = OUTPUT / 'progress.json'
    p = json.loads(path.read_text(encoding='utf-8-sig'))
    old = p['guidelines']['top4_loop01']
    old['phase1_complete'] = True
    old['complete'] = True
    old['written'] = 272
    old['note'] = 'rows 21-272 located by claude-haiku-5-5 in top4_loop01_locate_haiku.jsonl'
    old['located'] = None
    old['cannot_locate'] = None
    old['counts_note'] = 'Haiku output not opened in this run; combined status counts not verified.'
    old['local_written'] = 20
    old['external_written'] = 252
    old['last_pred_id'] = None
    n = summary['written']
    rows = read_jsonl(INPUT / (PREFIX + '_predictions.jsonl'))
    p['guidelines'][PREFIX] = dict(total=len(rows), written=n,
        located=summary['statuses'].get('located', 0), cannot_locate=summary['statuses'].get('cannot_locate', 0),
        batches=(n + 19)//20, phase1_complete=n == len(rows), complete=n == len(rows),
        last_pred_id=rows[n-1]['pred_id'] if n else None,
        input_sha256=hashlib.sha256((INPUT / (PREFIX + '_predictions.jsonl')).read_bytes()).hexdigest())
    p['current_guideline'] = PREFIX
    p['next_input_row'] = n + 1
    p['task'] = 'locating_only'
    path.write_text(json.dumps(p, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    command = sys.argv[1]
    rows = read_jsonl(INPUT / (PREFIX + '_predictions.jsonl'))
    if command == 'read':
        start = int(sys.argv[2])
        for i in range(start-1, min(start+19, len(rows))):
            r = rows[i]
            print(json.dumps(dict(row=i+1, text=r['pred_text'], label=r['pred_label'], context=r['context'], citation=r['guideline_section'], rationale=r['rationale']), ensure_ascii=False))
    elif command == 'append':
        # Each quote: [start, end, condition, role, citation_fragment_indices, optional exact span].
        batch = json.loads(sys.stdin.read().lstrip('\ufeff'))
        path = OUTPUT / (PREFIX + '_locate.jsonl')
        existing = read_jsonl(path) if path.exists() else []
        assert batch['start'] == len(existing)+1
        assert len(batch['rows']) == min(20, len(rows)-len(existing))
        lines = (INPUT / 'guidelines' / (PREFIX + '.txt')).read_text(encoding='utf-8').splitlines()
        output = []
        for i, decision in enumerate(batch['rows'], batch['start']-1):
            fragments = [f.strip() for f in rows[i]['guideline_section'].split(';')]
            quotes = []
            for q in decision['q']:
                a,b,condition,role,indices = q[:5]
                quotes.append(dict(quote=q[5] if len(q)>5 else '\n'.join(lines[a-1:b]),
                    line_start=a, line_end=b, condition_words=condition, role=role,
                    cited_as='; '.join(fragments[j] for j in indices)))
            output.append(dict(pred_id=rows[i]['pred_id'], status='located' if quotes else 'cannot_locate',
                quotes=quotes, note=decision.get('note','')))
        with path.open('a', encoding='utf-8', newline='\n') as f:
            for row in output:
                f.write(json.dumps(row, ensure_ascii=False)+'\n')
                f.flush()
        summary = check()
        progress(summary)
        assert not summary['errors']
    elif command == 'check':
        summary = check(complete=True)
        (OUTPUT / 'top4_loop02_checks.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        assert not summary['errors']
    elif command == 'init':
        progress(dict(written=0, statuses={}))

if __name__ == '__main__':
    main()
