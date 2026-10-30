"""Execute trusted reference SQL only. This is not an LLM SQL sandbox or accuracy test."""
import json
from .warehouse import ROOT, DEFAULT_DB
import duckdb

def main():
    cases=json.loads((ROOT/'eval/cases.json').read_text())
    con=duckdb.connect(str(DEFAULT_DB),read_only=True)
    try:
        output=[]
        for case in cases:
            item={k:v for k,v in case.items() if k!='reference_sql'}
            if case['expected_action']=='query':
                cur=con.execute(case['reference_sql'])
                item.update(columns=[d[0] for d in cur.description],rows=cur.fetchall())
            output.append(item)
        report=ROOT/'reports/reference_answers.json'
        report.write_text(json.dumps(output,indent=2,default=str)+'\n')
        print(f'Executed {sum(c["expected_action"]=="query" for c in cases)} reference queries; wrote {report}')
    finally: con.close()

if __name__=='__main__':main()
