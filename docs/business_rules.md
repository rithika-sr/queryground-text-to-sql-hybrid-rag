# Business definitions, version 1
All records and provider/model labels are invented. Dates use UTC. Reporting periods are half-open: start inclusive, next period exclusive. No runtime-dependent 'today' is used in reference questions.

- Gross billed spend: sum billing_items.amount_cents by billed_at, including inference and platform charges. Never filter billing using request status: billing has no request_id and cannot be attributed to individual requests.
- Posted credits: positive credits.amount_cents by credited_at. Credits belong to the team owning the linked billing item's service.
- Net billed spend: gross charges posted in the period minus credits posted in that period. 'Excluding credits' means gross spend. The original billing date does not determine the credit's reporting period. Net may be negative.
- Successful requests: status='success', grouped by requested_at. Failed requests remain in the denominator for failure rate.
- Failure percentage: failed / all requests * 100. Return NULL for zero denominator, not 0.
- Latency: arithmetic mean over successful requests only, in milliseconds, unless another definition is requested.
- Token counts: recorded input/output usage across all statuses unless the question explicitly requests success-only. Failed requests can consume input tokens.
- Budgets: one positive monthly budget per team, in cents. Budget utilization defaults to gross billed spend / budget * 100. Ask if the user specifically wants another spend basis.
- Team ownership: services have one static owner in this toy dataset. Historical ownership changes are not modeled.
- Zero activity: include inactive teams only when requested, or when comparing all teams against budgets. Use LEFT JOIN and coalesce spend/count to zero. An undefined ratio remains NULL.
- Ranking: break ties alphabetically by displayed team/service name; top N returns exactly N if available.
- Ambiguity: ask about undefined 'efficiency', missing time periods, unspecified relative-date anchors, or undefined quality. Never invent quality or employee data.
- Currency: integer USD cents at storage and reference-output layers. Divide by 100 only when dollars are explicitly requested.

## Join rules
requests -> services -> teams; requests -> models.
billing_items -> services -> teams; billing_items -> models.
credits -> billing_items -> services -> teams.
budgets -> teams, also filtered on month.
daily_usage is an aggregate of requests; do not join the two to sum usage.

Billing and requests are independent fact tables. Aggregate each to the requested reporting grain before joining. Multiple credits per billing item also multiply billing values in a naive join. Aggregate credits separately before combining with gross spend.

## Worked miniature example
September charges: Search 1000 cents, Support 500 cents. Two September credits of 100 and 50 cents apply to Search's one charge. A further 25-cent credit against that charge posts in October.
September gross is 1500; September credits are 150; September net is 1350. Search net is 850, Support net is 500. Joining billing to credits then summing billing can incorrectly report 3500 gross across all credit rows. Apply date filters and aggregate facts independently.
