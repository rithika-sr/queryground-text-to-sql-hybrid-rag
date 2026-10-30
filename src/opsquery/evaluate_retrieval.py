"""Development-only table retrieval metrics; never SQL accuracy."""
import argparse
import json
from pathlib import Path
from .context import retrieve
from .warehouse import ROOT


def development_cases(root=ROOT):
    # Project only dev inputs and table labels. SQL/answers never enter retrieval.
    return [{'id': c['id'], 'question': c['question'], 'required_tables': c['required_tables']}
            for c in json.loads((root/'eval/cases.json').read_text())
            if c['split'] == 'dev' and c['expected_action'] == 'query']


def evaluate(method='bm25', top_k=5):
    rows = []
    for case in development_cases():
        _, details = retrieve(case['question'], method, top_k)
        required = set(case['required_tables'])
        selected = set(details['selected_tables'])
        missing = sorted(required - selected)
        rows.append(dict(id=case['id'], required_tables=sorted(required),
                         selected_tables=sorted(selected), missing_tables=missing,
                         required_table_recall=len(required & selected)/len(required),
                         selected_table_count=len(selected),
                         initial_tables=details['initial_tables'],
                         dependency_added_tables=details['dependency_added_tables'],
                         bridge_tables=details['bridge_tables']))
    return dict(metric='development required-table retrieval; NOT SQL accuracy', method=method,
                top_k=top_k, case_count=len(rows),
                mean_required_table_recall=sum(r['required_table_recall'] for r in rows)/len(rows),
                mean_selected_table_count=sum(r['selected_table_count'] for r in rows)/len(rows),
                failures=[r['id'] for r in rows if r['missing_tables']], cases=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=['bm25', 'hybrid'], default='bm25')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--output', type=Path, default=Path('reports/day2_retrieval.json'))
    args = parser.parse_args()
    result = evaluate(args.method, args.top_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))


if __name__ == '__main__': main()
