# Turtle-H conformance tests

The RDF manifest contains 22 positive syntax, 14 negative syntax, 22 expansion, and 22
successful serialization tests plus one unrepresentable-context rejection. Every block registers its identifier in G and M, including empty blocks.
Expected `metadataGraph` results are compared jointly with data for shared blank nodes.
Collections, property lists, annotations, directional literals, and content-only
management predicates have explicit gold results.

Run `python tests/run_suite.py --manifest tests/turtle-h/manifest.ttl --validate-only`.
No Turtle-H parser is bundled; an external adapter executes the language tests. The RDF4J-based
[`rdf4j-rio-turtleh`](https://github.com/geoknoesis/rdf4j-rio-turtleh) parser and serializer pass all 81 cases (`./gradlew conformanceConfig` in that project writes an
adapter configuration for this runner).
Gold-result checks and the reference context model do not establish parser conformance.
See [the suite guide](../README.md) and [requirement trace](../requirements.ttl).
