# Day 2: context retrieval and SQL proposals

Day 2 builds prompts and validates proposal envelopes. It does not parse, validate
identifiers in, sandbox, or execute model SQL; those execution controls belong to Day 3.
No SQL accuracy has been measured.

## Fresh clone and tests

From the repository root, use Python 3.12:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Tests generate temporary seed-42 and alternate-seed databases and do not require
a database in `data/`. The Day 1 reconciliation, independent reference totals,
inactive-team, fanout and overwrite checks remain. The existing workspace database
is untouched. For the Day 1 command-line reference runner, generate the database
once if absent:

```bash
.venv/bin/python -m opsquery.warehouse
.venv/bin/python -m opsquery.reference
```

The warehouse command deliberately refuses to overwrite an existing database.
Do not run it against an existing file. Day 2 commands never need a database.

## Offline prompts

```bash
.venv/bin/python -m opsquery.proposal 'What was net billed spend by team in September 2026?' --mode full
.venv/bin/python -m opsquery.proposal 'What was net billed spend by team in September 2026?' --mode retrieval --method bm25 --top-k 5
```

Both commands default to offline preview. Output JSON is saved under ignored
`reports/runs/`; `--output /tmp/preview.json` chooses another location. The prompt,
context IDs, rankings, table expansion, requested model, response schema and run
status are saved. Model identity, latency and usage remain null until a live call.
Keep prompts free of secrets; question and context text are intentionally recorded.

The same `SYSTEM` instructions are used for both modes. Full mode supplies every
table DDL and catalog entry plus every business definition, general conventions,
join rules and worked example. Retrieval mode selects documents and always adds
general conventions and join safeguards. Schema documents use IDs such as
`table:billing_items`; individual definitions use IDs such as `rule:net-billed-spend`.
Table documents include catalog metadata (grain, column names/types/nullability,
keys and foreign keys) and authoritative DDL. Grain provides the table description
in the Day 1 catalog. Row counts are static seed-42 metadata, not live statistics.

The corpus has an explicit three-file allowlist: `docs/catalog.json`,
`src/opsquery/schema.sql`, and `docs/business_rules.md`. Evaluation questions,
reference SQL, answers and held-out cases never enter it. Development questions
are used as evaluation queries only, never indexed.

BM25 uses lowercase alphanumeric tokens, splits underscores, k1=1.5 and b=0.75;
only positive matches are ranked, with document-ID tie breaking. Top-k refers to
documents, not tables. Selected definitions declare dependencies in
`context.DEPENDENCIES`, e.g. net billed spend adds billing and credits. Explicit
team mentions add services and teams. These heuristics are deliberately visible
and can overselect or miss relevant context. They are not a semantic parser.

`initial_tables`, `dependency_added_tables`, and `bridge_tables` are disjoint.
For each pair of initial/dependency tables, deterministic breadth-first search
adds intermediate tables on a shortest undirected FK path. This is a connectivity
heuristic, not a guarantee of the correct join plan; equal-length routes may choose
an unnecessary dimension. The final prompt includes full schema documents for
all completed tables. Always inspect retrieval details before interpreting results.

## Optional local embeddings and hybrid ranking

```bash
.venv/bin/python -m pip install -e '.[embeddings]'
.venv/bin/python -m opsquery.proposal 'What was net billed spend by team in September 2026?' --method hybrid
.venv/bin/python -m opsquery.evaluate_retrieval --method hybrid --output reports/day2_hybrid.json
```

For the existing uv-created environment (which has no pip), use
`uv pip install --python .venv/bin/python -e '.[embeddings]'` instead of the pip
installation command. The base Day 2 commands already work in that environment.

Hybrid explicitly loads `sentence-transformers/all-MiniLM-L6-v2` locally; initial
use downloads weights unless cached. BM25 neither imports sentence-transformers
nor downloads weights. Normalized-vector dot products rank semantic matches.
Reciprocal rank fusion sums `1/(60 + rank)` over the two rankings without mixing
raw score scales. Rankings and the embedding model ID are saved. The small corpus
is encoded per retrieval call; this is an initial implementation, not a scalable
cached index. Long schema documents may be truncated by the embedding model.
See the [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and [SentenceTransformer API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).

## Explicit live API calls

Set `OPENAI_API_KEY` securely in your shell and `OPENAI_MODEL` to a model available
to your account that supports Responses API structured outputs. There is no
implicit model default. The API key is never included in the persisted request
payload or run JSON. No dotenv files are loaded automatically.

```bash
export OPENAI_MODEL='YOUR_SUPPORTED_MODEL_ID'
.venv/bin/python -m opsquery.proposal 'What was gross billed spend in September 2026?' --mode full --live
.venv/bin/python -m opsquery.proposal 'What was gross billed spend in September 2026?' --mode retrieval --live
```

`--live` sends the question and selected context to OpenAI and may incur charges.
The stdlib HTTP adapter uses `POST https://api.openai.com/v1/responses`,
`instructions`, `input`, `text.format` with strict JSON schema, and `store: false`.
Implementation checked against [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
on 2026-10-30. There is no automatic retry or SQL execution.

The adapter rejects incomplete responses, API refusals, malformed JSON and invalid
proposal envelopes. Allowed actions are `query`, `clarify`, `unsupported`, `reject`.
Queries require a nonempty SQL string; other actions require null SQL. Explanation
must be a string; every source ID must be present in the actual prompt. Envelope
validation does not prove that citations support the SQL or that SQL is safe.
Successful calls save the returned model identity, usage, latency and proposal.
Failures save status and available model/usage/timing metadata, then exit nonzero;
error bodies and HTTP headers are not logged. Live failures do not silently become
valid non-query actions.

## Development retrieval evaluation

```bash
.venv/bin/python -m opsquery.evaluate_retrieval --method bm25 --top-k 5
```

Only `split=dev`, `expected_action=query` cases contribute. The loader projects
ID, question and required-table labels; reference SQL and answer values are never
passed to retrieval. Held-out cases are not evaluated. Required-table recall is
`|required intersect selected| / |required|` per case, macro-averaged. Selected
count includes dependencies and bridges. These labels specify one reference
formulation; an alternative valid formulation might use different tables.

Actual offline run in `reports/day2_retrieval.json` (12 development query cases):

| Configuration | Mean required-table recall | Mean selected tables | Cases missing tables |
| --- | ---: | ---: | --- |
| BM25, top-k 5 | 0.93056 | 3.91667 | Q07: services; Q12: requests |
| Full context (all 8 schemas, by construction) | 1.0 | 8 | None |
| Hybrid | Not run | Not run | Unknown |

Do not interpret recall as SQL accuracy. No LLM proposals were evaluated, no
held-out performance was measured, and hybrid is not assumed to improve BM25.
The recorded failures remain to make the baseline limitations explicit.

## Verification limits

Both offline CLI modes and BM25 evaluation were run. Unit tests mock Responses
API output, malformed envelopes, incomplete responses and refusals; hybrid fusion
uses a mocked semantic ranking. A real API call and real embedding inference were
not run: no API credentials/model were provisioned for this task and the optional
embedding package/weights were not installed. The base installation remains usable
without them. Optional model availability, network downloads, hardware performance
and real provider integration remain unverified.
