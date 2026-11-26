# Living Library v0.1
Owner authorization: 2026-11-26. ARGO bootstrap, non-canonical.
## Boundaries
ARGO-KOP owns governance, original events and canonical promotion. ARGO-Research owns research. Library owns derived retrieval cards, not original evidence. Public repository: only public or explicitly cleared material; private mappings and restricted cards stay private. No automatic publication from private sources.
## Model
One immutable card per source event/lesson, stable ID, mechanism tags across domains, explicit evidence status and applicability limits. Corrections are new cards linked by supersedes; preserve failures. Distinguish author, extractor, verifier and user correction. Deduplicate by source identity plus lesson, not title. Missing links remain unresolved. No inferred canonical status.
## Operation
Search by problem/mechanism before execution; read source, apply within limits, record use and outcome separately. Generated indexes are disposable; independent cards avoid shared-file conflicts. No paid CI required; run local validation before batch merges. Never alter house entry rules without separate authorization.
## Migration
SEMER coordinates inventory at pinned source revision, reconciles #763 counts, partitions public-cleared vs restricted vs unresolved, imports in small batches with manifests and source hashes kept in appropriate visibility. No original deletion. Compare old retrieval vs new on frozen queries, measure precision@5, recall against adjudicated relevant set, time, tool calls, tokens, merge costs and downstream task outcomes; report misses and negative results. No learning claim without independent outcome evidence.
## Layout
cards/<id>.json; schema/card.schema.json; tools/search.py. Private counterpart may use identical schema. Public cards must contain only public/cleared evidence references. Generated output is not committed by default.
