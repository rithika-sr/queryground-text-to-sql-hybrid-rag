"""Deterministic, wholly synthetic warehouse; no external services or private data."""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import random
import duckdb

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / 'data' / 'opsquery.duckdb'

def build(path=DEFAULT_DB, seed=42):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f'{path} exists; choose a new path or remove it explicitly')
    rng = random.Random(seed)
    con = duckdb.connect(str(path))
    try:
        con.execute('BEGIN TRANSACTION')
        con.execute((Path(__file__).with_name('schema.sql')).read_text())
        con.executemany('INSERT INTO teams VALUES (?,?)', [(1,'Search'),(2,'Support'),(3,'Analytics'),(4,'Research')])
        con.executemany('INSERT INTO services VALUES (?,?,?)', [(1,'knowledge-search',1),(2,'document-indexer',1),(3,'support-assistant',2),(4,'ticket-triage',2),(5,'analytics-copilot',3),(6,'research-sandbox',4)])
        con.executemany('INSERT INTO models VALUES (?,?,?)', [(1,'synthetic-small','Provider A'),(2,'synthetic-large','Provider A'),(3,'synthetic-embed','Provider B')])
        requests=[]; bills=[]; credits=[]; rid=bid=cid=0
        for day_offset in range(92):
            day=date(2026,8,1)+timedelta(days=day_offset)
            for service in range(1,7):
                # Research has a budget but deliberately no activity.
                if service == 6: continue
                for model in range(1,4):
                    count=rng.randint(2,9)+(5 if service==3 and day.month==10 else 0)
                    for _ in range(count):
                        rid+=1; ok=rng.random()>.13
                        requests.append((rid,service,model,datetime.combine(day,datetime.min.time())+timedelta(seconds=rng.randrange(86400)), 'success' if ok else 'failed',rng.randint(50,3000),rng.randint(5,900) if ok else 0,rng.randint(80,5000)))
                    # Billing is not at request grain; delays cross month boundaries.
                    bid+=1
                    amount=count*(12 if model==2 else 3)+rng.randint(0,9)
                    bills.append((bid,service,model,day+timedelta(days=2),'inference',amount))
                    if day.day in (5,19) and service in (1,3):
                        for part in (1,2):
                            cid+=1; credits.append((cid,bid,day+timedelta(days=5),part*7,'service adjustment'))
                if day.day==1:
                    bid+=1; bills.append((bid,service,1,day,'platform',1500))
        con.executemany('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)',requests)
        con.executemany('INSERT INTO billing_items VALUES (?,?,?,?,?,?)',bills)
        con.executemany('INSERT INTO credits VALUES (?,?,?,?,?)',credits)
        con.executemany('INSERT INTO budgets VALUES (?,?,?)',[(t,date(2026,m,1),18000+t*2000) for t in range(1,5) for m in (8,9,10)])
        con.execute("""INSERT INTO daily_usage SELECT CAST(requested_at AS DATE),service_id,model_id,
          count(*) FILTER(WHERE status='success'),count(*) FILTER(WHERE status='failed'),
          sum(input_tokens),sum(output_tokens) FROM requests GROUP BY 1,2,3""")
        con.execute('COMMIT')
        return {t:con.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('teams','services','models','requests','daily_usage','billing_items','credits','budgets')}
    finally: con.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--db',type=Path,default=DEFAULT_DB);parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args();print(build(args.db,args.seed))
