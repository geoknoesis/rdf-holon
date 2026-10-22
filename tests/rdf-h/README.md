# RDF-H conformance fixtures

Run `python tests/rdf-h/check_composition.py` with rdflib installed.

Checks cover direct GRAPH queries, recursive descendant aggregation, visible scope,
explicit ancestor imports, non-transitive and cyclic imports, and exclusion of
ancestors' and descendants' imports and imported holons' descendants.

Shapes are in a separate validation dataset and are imported explicitly. With
pyshacl installed, the script also checks shape-import outcomes, parent cardinality,
hierarchy cycles, and the independence of external domain relations. Without pyshacl
these validation checks are explicitly skipped.

The [RDF-H test manifest](./manifest.ttl) tests the optional conversion and validation capabilities through the
suite's adapter protocol: 8 conversion tests (dataset to reifier, content not promoted into M, a blank-node holon's
derived mapping, assertion preservation, equal shared mappings, and three unrepresentable conversion errors) and 6 validation tests (direct, aggregated, and global outcomes, shapes not
inherited, and the missing-shapes-graph and ill-formed-shapes-graph errors). Run it with
`python tests/run_suite.py --manifest tests/rdf-h/manifest.ttl --adapter-config tests/reference-adapters.json --require-all`.

Run `python tests/rdf-h/check_query_scopes.py` for the published CONSTRUCT recipes.
This checks all scopes, graph-name mappings, cross-holon joins, shared blank nodes,
triple deduplication, empty holons, and default-only query datasets. These recipes
are tested for the dataset profile; RDF 1.2 reifier query fixtures remain future work.
