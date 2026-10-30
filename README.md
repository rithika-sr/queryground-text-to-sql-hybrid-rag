# OpsQuery
An evaluated text-to-SQL assistant for synthetic AI operations spending.

**Status: Day 2 context retrieval and SQL proposal layers complete. Offline prompts and development retrieval metrics verified; live API and embedding inference unverified. No SQL execution or model accuracy claim.**

Planned question: "Which teams increased AI spending the most last month, excluding credits?" The eventual assistant will resolve business meaning, retrieve relevant schema and definitions, generate validated SQL, and show query results with its grounding.

## Run locally (macOS / Linux)
Requires Python 3.11–3.13; Python 3.12 is the tested environment. No API key needed. Python 3.14 compatibility has not been verified; use an isolated 3.12 environment.

With uv installed:
```bash
cd opsquery
uv python install 3.12
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
python -m opsquery.warehouse
python -m opsquery.reference
python -m unittest discover -s tests -v
```

Or use an existing Python 3.12:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m opsquery.warehouse
python -m opsquery.reference
python -m unittest discover -s tests -v
```
Generated databases are excluded from Git. On a fresh clone, run the warehouse command above before the reference runner. Tests generate temporary databases themselves. If a database already exists, choose a new path with `python -m opsquery.warehouse --db data/alternate.duckdb --seed 7`. The reference runner uses data/opsquery.duckdb. Build refuses to overwrite a database.

## Day 2

Use the existing environment without an API key or model download:

```bash
.venv/bin/python -m opsquery.proposal 'What was net billed spend by team in September 2026?' --mode full
.venv/bin/python -m opsquery.proposal 'What was net billed spend by team in September 2026?' --mode retrieval --method bm25
.venv/bin/python -m opsquery.evaluate_retrieval
.venv/bin/python -m unittest discover -s tests -v
```

Prompts and run metadata are saved under ignored `reports/runs/`. API calls require
`--live`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. Optional hybrid retrieval requires
the `embeddings` extra and downloads MiniLM weights on first use. See
[Day 2 walkthrough](docs/day2_walkthrough.md) for exact setup, live commands,
context IDs, table completion, validation boundaries and verification limits.
BM25 top-k 5 achieved 93.06% mean required-table recall over 12 development query
cases, selecting 3.92 tables on average; Q07 and Q12 missed tables. These are
retrieval metrics, not SQL accuracy. Hybrid has not been measured.

## Files
- src/opsquery/schema.sql: eight-table schema with keys and constraints.
- src/opsquery/warehouse.py: seeded synthetic data generator.
- docs/catalog.json: table grains, descriptions, columns and FK relationships.
- docs/business_rules.md: versioned metric definitions and join pitfalls.
- eval/cases.json: 18 SQL questions and six clarification/rejection/unsupported cases.
- reports/reference_answers.json: executed reference answers; not model predictions.
- tests/: reconciliation and failure-mode checks on three seeds, plus independent Python checks of key reference answers.
- docs/day1_walkthrough.md: learning path and next steps.

## Why this domain?
Spend analysis tests table selection, business interpretation, time windows, multi-fact joins, credits and zero-activity teams. The dataset intentionally contains traps that produce plausible but incorrect SQL results.

## Planned evaluation
Compare full-schema prompting against schema retrieval, business-context retrieval, and examples plus bounded repair using the same model. Measure result correctness, retrieval recall, behavior on non-query requests, latency and tokens. Publish actual results and failure examples even if retrieval does not outperform the baseline.

## Limitations
Synthetic, small, single-schema, USD-only data; static service ownership; no row-level authorization; no query sandbox yet. The reference runner executes only repository-authored SQL. Do not connect it to user/LLM-generated queries. Attribution of billed spend to individual failed requests is unsupported. The current starter cases are not an independently audited benchmark.

## GitHub
Create your own repository and commit these files once you have run and understood them. Generated databases are ignored; the generator reproduces them. No files or model weights from the reference friend's repository are reused here. No credentials or employer data are included.
