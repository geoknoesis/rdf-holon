# Query the three RDF-H scopes without extending SPARQL

The CONSTRUCT queries build direct, aggregated, and visible content for City.
Run each against `../scopes.trig`, using its default graph for declarations and
mappings. Queries follow explicit `h:contentGraph` mappings with a holon-IRI fallback.
Validate the selected root in K(M), mappings, and the mode-applicable parent/import checks first; these are query
recipes and do not replace validation.

Run `read-values.rq` on the constructed graph as a second step. The scope result
becomes the default graph for the application query; no named graphs are needed.
This supports joins across selected holons and deduplicates shared triples.

| Scope | Expected values |
|---|---|
| direct | city |
| aggregated | city, district, neighborhood |
| visible | city, district, metro, neighborhood |

A scoped application API is a convenience wrapper, not a SPARQL syntax or protocol
extension. `GRAPH ex:City` retains its ordinary explicit named-graph meaning.

Run `python tests/rdf-h/check_query_scopes.py` to execute these examples, including
explicit graph mappings, shared triples, shared blank nodes, and cross-holon joins.

These recipes use the source default graph as M. For an external M, supply a query
view whose default graph is M and whose named graphs are the source content graphs.
Management predicates filed only as content never supply operational edges.
