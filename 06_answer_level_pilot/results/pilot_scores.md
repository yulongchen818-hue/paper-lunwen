# Answer-level pilot — mechanical scoring (no human judgment, no model)

| Condition | N answerable | key hit | answers with ≥1 unsupported numeric token | unsupported tokens (total / per answer) | numeric tokens total | citations resolvable | unnecessary abstention | N boundary | safe abstention |
|---|---|---|---|---|---|---|---|---|---|
| CDC-full | 18 | 13/18 | 0/23 | 0 / 0.00 | 43 | 83/83 | 0 | 5 | 5/5 |
| RAG-12 | 18 | 14/18 | 1/23 | 1 / 0.04 | 47 | 57/63 | 0 | 5 | 4/5 |
| NoEvidence | 18 | 2/18 | 7/23 | 8 / 0.35 | 8 | 0/0 | 0 | 5 | 5/5 |

## Per-item

| Q | type | CDC-full (key / unsupported / abstain) | RAG-12 (key / unsupported / abstain) | NoEvidence (key / unsupported / abstain) |
|---|---|---|---|---|
| A01 | answerable | HIT / 0 / no | miss / 0 / yes | HIT / 1 / no |
| A02 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 1 / yes |
| A03 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 2 / yes |
| A04 | answerable | HIT / 0 / yes | HIT / 0 / no | miss / 1 / yes |
| A05 | answerable | HIT / 0 / no | HIT / 0 / no | HIT / 1 / yes |
| A06 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| A07 | answerable | miss / 0 / yes | miss / 0 / no | miss / 0 / yes |
| A08 | answerable | miss / 0 / yes | miss / 0 / yes | miss / 0 / yes |
| A09 | answerable | miss / 0 / yes | miss / 0 / yes | miss / 0 / yes |
| A10 | boundary | SAFE / 0 / yes | unsafe / 0 / no | SAFE / 0 / yes |
| A11 | boundary | SAFE / 0 / yes | SAFE / 0 / yes | SAFE / 0 / yes |
| A12 | boundary | SAFE / 0 / yes | SAFE / 0 / yes | SAFE / 0 / yes |
| B01 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| B02 | answerable | miss / 0 / yes | HIT / 1 / no | miss / 0 / yes |
| B03 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 1 / yes |
| B04 | answerable | HIT / 0 / yes | HIT / 0 / yes | miss / 0 / yes |
| B05 | answerable | miss / 0 / no | HIT / 0 / no | miss / 1 / yes |
| B06 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| B07 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| B08 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| B09 | answerable | HIT / 0 / no | HIT / 0 / no | miss / 0 / yes |
| B10 | boundary | SAFE / 0 / yes | SAFE / 0 / yes | SAFE / 0 / yes |
| B11 | boundary | SAFE / 0 / yes | SAFE / 0 / yes | SAFE / 0 / yes |