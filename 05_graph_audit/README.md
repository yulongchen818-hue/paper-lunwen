# 05_graph_audit

`audit_graph.py` computes, for each graph version: entity and edge counts; referential integrity (property
values beginning with `sb:` resolved against instantiated identifiers); dangling references by
class.property; declared versus realized relation types; untyped fallback edges; domain/range conformance
of `depicts` and `involvesSegment`; the edge profile of `PushRound`; and stage-linkage counts. These are the
pass rates of the checks that ingestion-time constraints would enforce, computed after the fact. Point the
`GRAPHS` dictionary at your own graph files.
