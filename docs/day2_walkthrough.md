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
# zsh: enter the key without echoing it or putting it in shell history.
read -s 'OPENAI_API_KEY?OpenAI API key: '
printf '\n'
export OPENAI_API_KEY
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

Actual runs on 2026-10-30 in `reports/day2_retrieval.json` and
`reports/day2_hybrid.json` (the identical 12 development query cases, Q01–Q12).
The embeddings extra was installed with the documented uv command; MiniLM weights
were downloaded and actual local inference completed. Installed versions included
sentence-transformers 5.7.0, transformers 5.22.1, torch 2.15.0 and numpy 2.5.4.
Package versions and inspected rankings are in `reports/day2_verification.json`.
No evaluation cases, reference SQL or reference answers were edited or indexed.

| Configuration | Mean required-table recall | Mean selected tables | Cases missing tables |
| --- | ---: | ---: | --- |
| BM25, top-k 5 | 0.93056 | 3.91667 | Q07: services; Q12: requests |
| Full context (all 8 schemas, by construction) | 1.0 | 8 | None |
| Hybrid (actual MiniLM + BM25/RRF), top-k 5 | 0.87500 | 3.41667 | Q07: services; Q11: daily_usage |

Hybrid reduced mean table count by 0.50 but reduced macro recall by 5.56 percentage
points. It fixed Q12, retained the Q07 miss and introduced the Q11 miss. Do not
interpret recall as SQL accuracy. No LLM proposals were evaluated and no held-out
performance was measured. The baseline was not retuned after observing these results.

Failure inspection (actual retrieved IDs and rankings are saved in the verification
report):

- Q07 asks for the three services with most successful requests. Both modes miss
  `services`. Top-k is consumed by definitions, join guidance and `daily_usage`;
  the successful-request dependency adds `requests`, but the explicit grouping
  heuristic only handles team mentions, not service mentions. FK completion
  connects tables already selected and cannot infer an absent grouping dimension.
  Its shortest path through `models` also illustrates that connectivity is not
  the same as a useful join plan.
- Q12 asks for teams with no requests. BM25 retrieves team/zero-activity material
  but no document that adds `requests`; the team heuristic supplies only `services`
  and `teams`. Hybrid selects enough request context to recover that table and
  achieves full required-table recall for this case.
- Q11 explicitly asks for daily usage. BM25 ranks `table:daily_usage` first.
  Semantic ranking favors short business definitions, so fused top-k drops that
  schema in favor of join guidance and token/success/failure/spend definitions.
  Their dependencies add `requests` and `billing_items`, not `daily_usage`.
  This is an observed failure of the present fusion/document design, not evidence
  that an alternative SQL formulation using raw requests would satisfy the
  explicitly requested source.

## Net-spend prompt inspection

Inspected both the example question above and exact development Q05 (which also
says “Include teams with no spend”). Full, BM25 and actual hybrid prompts share
identical system instructions. All include full DDL and column metadata for
`billing_items`, `credits`, `services` and `teams`, the net-spend definition,
UTC/half-open date conventions and fact/credit fanout safeguards. Full mode has
all eight tables. Both retrieval modes select five tables: the four required
ones plus `budgets`. The retrieved metric rules supply billing/credit dependencies;
the team mention adds services/teams. For the shorter example no schema document
was an initial top-k hit; all five tables came from dependencies, with no bridge
additions. Thus checking only raw top-k table hits would understate actual context.

Prompts were saved in ignored `reports/runs/net_spend_{full,bm25,hybrid}.json` and
`reports/runs/net_spend_Q05_{full,bm25,hybrid}.json`; context IDs, table expansion and
Q05 rankings are retained in `reports/day2_verification.json`.

Schema availability is not business-definition completeness. Inspecting the
shorter example, BM25 omits the standalone posted-credit rule (hybrid includes it).
Both retrieval modes omit some full-context conventions. For the exact Q05
inactive-team requirement, both do include `rule:zero-activity`, while both omit
the standalone posted-credit rule. This confirms that a small wording change
changes definition selection even when the final table set stays the same.
Full context remains the only mode guaranteed to include every definition.

## Verification limits

Full/BM25/hybrid offline prompts, actual MiniLM inference and both development
retrieval evaluations were run. Unit tests still use mocked provider responses
and semantic rankings so the default suite requires no network/model download.
The existing Day 1 data was preserved. Evaluation files were not modified;
held-out cases were excluded from both retrieval evaluations. The existing reference regression test still runs the
repository-authored reference SQL as before; only development cases contributed
retrieval metrics.

Only presence of `OPENAI_API_KEY` and `OPENAI_MODEL` was checked; both were absent.
No credential values were printed and no real API request was made. To verify
locally, use the secure zsh key-entry commands in “Explicit live API calls”,
replace `YOUR_SUPPORTED_MODEL_ID` with an available model supporting structured
outputs, and run either explicit `--live` command there. A saved run must have
`status: completed`, a returned model identity, usage and a validated proposal
before calling live integration verified. This remains pending. Do not execute
the proposed SQL.

Remaining limitations include this small development-only synthetic benchmark,
heuristic metric/group dependencies, overselected tables, missing definitions,
non-semantic FK path choice, embedding input truncation, an unpinned model revision
and repeated per-question model loading/encoding. Package versions are recorded
but transitive dependencies are not locked. The actual download initially failed
inside the network sandbox and succeeded after network access was granted.
This verifies the current environment, not every platform or offline fresh-cache
installation. The base BM25 path remains usable without embeddings installed.

Final verification: `.venv/bin/python -m unittest discover -s tests -v` passed
all 15 tests, including the net-spend prompt schema/zero-activity regression.
