# Day 1 walkthrough
Goal: understand the data and define correct answers before adding a language model.

1. Read docs/business_rules.md. Explain gross versus net and why request dates differ from billing dates.
2. Open src/opsquery/schema.sql. Trace the route from a credit to a team. Identify the two independent fact tables.
3. Run the README setup commands. The generator creates August–October request activity, billing delayed by two days, credits delayed by five days, and an inactive team. Some billing/credits therefore post in November.
4. Read Q05 in eval/cases.json. Its two CTEs aggregate charges and credits independently, preventing fanout.
5. Inspect reports/reference_answers.json. These are trusted-reference outputs, NOT predictions or a model accuracy result.
6. Try Q01 and Q05 yourself before reading their reference SQL. Check how the inactive Research team appears.
7. Run the tests. They check reconciliation, inactive-team behavior, fanout, and deterministic generation across seeds.

## Scope and next steps
Day 1 includes eight tables, deterministic generation, 18 SQL reference cases, six non-query behavior cases, data catalog, business definitions, and reproducible tests. These 24 cases are a starter set, not the eventual 60-case benchmark.

Day 2: implement full-schema prompting as a baseline; then retrieve table/column descriptions and business rules. Add FK bridge tables explicitly. Keep the generation API separate from execution.
Day 3: add query parsing, identifier validation, sandboxed execution and one repair attempt.
Day 4: compare configurations using answer correctness, retrieval recall, latency and token usage. Expand to 60 reviewed cases before making portfolio performance claims.
Days 5–6: Streamlit demo, screenshots, README results and demo video.

## Evaluation discipline
The split labels are provisional: a developer reading this repository can see held-out references. Never index holdout SQL or outputs for retrieval, use them as prompt examples, or tune against them repeatedly. Near-duplicate count/join questions exist here; curate a separate unseen final set before claiming generalization. A tiny single-schema synthetic dataset cannot establish enterprise readiness or unseen-schema performance.

Future result comparison must preserve duplicate rows, ignore row order only for unordered questions, compare NULLs correctly, use numeric tolerances, and require both queries to execute successfully. Always report non-query behavior separately from SQL correctness. Run alternate data seeds to reduce accidental result matches. Public model benchmarks may have training contamination; this custom benchmark has different limitations.

## Your Day 1 checkpoint
You should be able to explain: Why RAG needs business definitions; why valid SQL can be wrong; why joining raw fact tables is dangerous; why a successful empty result differs from an execution failure; and why reference answers are not model results.
