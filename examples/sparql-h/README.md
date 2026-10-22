# SPARQL-H examples

`.srqh` is a repository filename convention, not a registered media type.
Positive examples have paired `.rq` files containing their expected standard-SPARQL
query after removal of the parsed holon clause. The query must be executed with the
resolved scope graph as the default graph and no named graphs; the `.rq` text alone
does not construct the scope or identify its source dataset.

Examples cover the default and explicit modes, SELECT, ASK, CONSTRUCT, COUNT,
trailing VALUES, ordinary subqueries, case-insensitive keywords, explicit GRAPH,
and keyword-like text in strings/comments. `negative-*.srqh` are rejection cases,
including `HOLON:City`, which is a prefixed name rather than a holon clause.

Run `python tests/sparql-h/check_examples.py` with rdflib installed. The checker tests
expected lowerings and result semantics only. It neither parses SPARQL-H nor
executes negative parser/protocol cases. The authoritative RDF manifest is `tests/sparql-h/manifest.ttl`; the old JSON manifest is a legacy snapshot. The full adapter runner and EARL reporting are documented in `tests/README.md`.
