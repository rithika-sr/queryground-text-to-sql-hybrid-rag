import tempfile
import unittest
from pathlib import Path
import duckdb
from opsquery.warehouse import build

class WarehouseTests(unittest.TestCase):
    def test_invariants_on_three_seeds(self):
        for seed in (7,42,99):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as tmp:
                db=Path(tmp)/'test.duckdb';counts=build(db,seed)
                self.assertGreater(counts['requests'],5000)
                con=duckdb.connect(str(db),read_only=True)
                try:
                    raw=con.execute("SELECT count(*) FILTER(WHERE status='success'),count(*) FILTER(WHERE status='failed'),sum(input_tokens),sum(output_tokens) FROM requests").fetchone()
                    agg=con.execute('SELECT sum(successful_requests),sum(failed_requests),sum(input_tokens),sum(output_tokens) FROM daily_usage').fetchone()
                    self.assertEqual(raw,agg)
                    self.assertEqual(con.execute('SELECT count(*) FROM requests WHERE service_id=6').fetchone()[0],0)
                    self.assertGreater(con.execute('SELECT count(*) FROM (SELECT billing_id FROM credits GROUP BY 1 HAVING count(*)>1)').fetchone()[0],0)
                    self.assertGreater(con.execute("SELECT count(*) FROM requests WHERE status='failed'").fetchone()[0],0)
                    # An incorrect billing-to-credit join must inflate gross spend.
                    gross=con.execute('SELECT sum(amount_cents) FROM billing_items').fetchone()[0]
                    inflated=con.execute('SELECT sum(b.amount_cents) FROM billing_items b LEFT JOIN credits c USING(billing_id)').fetchone()[0]
                    self.assertGreater(inflated,gross)
                finally:con.close()
                with self.assertRaises(FileExistsError):build(db,seed)

if __name__=='__main__': unittest.main()
