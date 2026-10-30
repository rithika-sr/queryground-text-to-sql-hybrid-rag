"""Independent Python checks on a temporary seed-42 DB, including fresh clones."""
from collections import defaultdict
from datetime import date, datetime
import json
import unittest
import tempfile
from pathlib import Path
import duckdb
from opsquery.warehouse import ROOT, build

class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.db = Path(cls.tmp.name) / 'reference.duckdb'
        build(cls.db, seed=42)

    def test_reference_cases_and_independent_totals(self):
        c=duckdb.connect(str(self.db),read_only=True)
        try:
            cases=json.loads((ROOT/'eval/cases.json').read_text())
            answers={q['id']: c.execute(q['reference_sql']).fetchall() for q in cases if q['expected_action']=='query'}
            rows=c.execute('SELECT status,requested_at FROM requests').fetchall()
            success=sum(s=='success' and datetime(2026,9,1)<=dt<datetime(2026,10,1) for s,dt in rows)
            self.assertEqual(answers['Q01'],[(success,)])
            owners=dict(c.execute('SELECT service_id,team_id FROM services').fetchall())
            names=dict(c.execute('SELECT team_id,team_name FROM teams').fetchall())
            bills=c.execute('SELECT billing_id,service_id,billed_at,amount_cents FROM billing_items').fetchall()
            bill_owner={bid:owners[sid] for bid,sid,_,_ in bills}
            net=defaultdict(int);gross=0
            for bid,sid,dt,amount in bills:
                if date(2026,9,1)<=dt<date(2026,10,1):
                    net[owners[sid]]+=amount;gross+=amount
            for bid,dt,amount in c.execute('SELECT billing_id,credited_at,amount_cents FROM credits').fetchall():
                if date(2026,9,1)<=dt<date(2026,10,1):net[bill_owner[bid]]-=amount
            self.assertEqual(answers['Q03'],[(gross,)])
            self.assertEqual(answers['Q05'],sorted((name,net[tid]) for tid,name in names.items()))
            self.assertEqual(answers['Q12'],[('Research',)])
            self.assertEqual(len(cases),24)
        finally:c.close()

if __name__=='__main__':unittest.main()
