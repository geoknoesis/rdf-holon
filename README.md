# RDF-H: Organizing RDF Content into Holons

RDF-H is a community draft by Geoknoesis LLC. A holon has an identifier and explicitly
filed RDF content. Putting a statement in a holon means claiming that it is true;
RDF-H does not verify whether the claim is correct.

**Current RDF-H version: 0.8 (working draft).** Turtle-H 0.1.0 and experimental SPARQL-H 0.1.0 target this draft.

## Specifications

- [Reviewer briefing](./reviewer-briefing.html) summarizes the current review scope and evidence.
- [RDF-H](https://geoknoesis.github.io/rdf-holon/) defines content, representations, validation, and optional administrative composition.
- [Turtle-H](https://geoknoesis.github.io/rdf-holon/turtle-h/) defines authoring syntax plus parser and serializer conformance.
- [SPARQL-H](https://geoknoesis.github.io/rdf-holon/sparql-h/) experimentally adds `FROM HOLON` with direct, aggregated, and visible scopes, and `FROM NAMED HOLONS` to attribute statements to holons.

Start with the named-graph example in RDF-H. Use the reifier representation when
occurrence identity or occurrence metadata is needed. Both use an explicit metadata context M. Representation, composition,
validation, conversion, Turtle-H, and optional SPARQL-H support are declared separately.

## Standardization status

RDF-H is a community draft. The specifications follow W3C document conventions (ReSpec,
BCP 14 keywords, conformance classes, security, privacy, and internationalization
sections, W3C-style test manifests with EARL reporting). Advancement would additionally
need two independent implementations per feature, a Turtle-H parser that executes the
Turtle-H suite, stable RDF 1.2 and SPARQL 1.2 dependencies, and a W3C-managed namespace;
the specification's open issues track these items.

## Metadata and registration

Every registry-aware operation uses a designated metadata context M. Dataset inputs
use the default graph by convention; reifier inputs supply M explicitly. Holons are
registered by explicit holon types or graph mappings in M. Parent/import endpoints
must be registered when checked; inferred types do not register missing resources.
Management predicates filed only as content have no operational effect.

Turtle-H now returns G and M and emits a holon declaration for every block, including
empty blocks. Generated declarations are not implicitly filed content. Conversion
preserves M (adding only reported derived blank-node mappings) and declares either content preservation or full assertion preservation. Unrepresentable conversions fail instead of changing content or activating retained memberships.
The legacy `h:CompleteHolon` class is deprecated; completeness requires a separate
application contract and is not implied by that class.

## Optional hierarchy and imports

`h:parentHolon` identifies an immediate administrative parent. It allows at most one
parent, must be acyclic, and does not require a single root. It does not assert
physical or ontological parthood.

Direct content contains only the statements filed in a holon. Aggregated content
combines that holon's direct content with all descendants' direct content. Visible
content adds the direct content of targets explicitly imported by the selected holon.
Ancestors are excluded unless explicitly imported. Imports on descendants or ancestors
are not inherited; imported targets' descendants and imports are not expanded.
A plain named-graph query remains direct; aggregation and visible scope require explicit resolution.

`h:importsShapes` explicitly selects validation shapes graphs. Shapes are not inherited
from ancestors, and importing content never imports constraints. Supply shapes as a
separate validation dataset; every graph in the declared data dataset enters the
asserted union.

## Querying the three scopes

No SPARQL syntax extension is needed. Resolve `direct`, `aggregated`, or `visible`
content into a single graph and query that graph using ordinary SPARQL. A convenience
API should default to direct scope. Named `GRAPH` patterns retain their standard meaning.

The [query guidance](https://geoknoesis.github.io/rdf-holon/#querying) explains the workflow,
graph mappings, joins, dataset selection, and the reifier representation. Runnable
[SPARQL 1.1 recipes](./examples/rdf-h/composition/queries/) build each scope graph.
Run `python tests/rdf-h/check_query_scopes.py` to verify them.

The optional [SPARQL-H draft](./sparql-h/index.html) offers self-contained query syntax:

```sparql
PREFIX ex: <https://example.org/>
SELECT ?value
FROM HOLON ex:City SCOPE AGGREGATED
WHERE { ?subject ex:value ?value }
```

This experimental clause needs a SPARQL-H front end; ordinary SPARQL endpoints do
not accept it. The front end resolves a default-only query dataset and delegates the
remaining query to a standard engine. Run `python tests/sparql-h/check_examples.py`
for expected translation semantics. A small source-parsing reference adapter for both RDF-H profiles is included for testing; it is not a production service.

## Language conformance suites

The [W3C-style RDF manifest](./tests/manifest.ttl) discovers 179 Turtle-H, SPARQL-H, and RDF-H
syntax, evaluation, and expected-error cases. See [the suite guide](./tests/README.md)
for implementation adapters and EARL reporting.

```text
python tests/run_suite.py --validate-only --semantic-smoke
python tests/test_runner.py
python tests/test_semantics.py
python tests/run_suite.py --manifest tests/sparql-h/manifest.ttl --adapter-config tests/reference-adapters.json --require-all
```

Manifest checks do not claim language implementation conformance. Without configured
adapters the runner reports tests as untested. A source-parsing reference adapter can
run the 84 SPARQL-H cases, including reifier-profile and mixed sources, and a second reference adapter runs the 14 RDF-H
conversion and validation cases. No Turtle-H parser is bundled; the RDF4J-based `rdf4j-rio-turtleh` codecs pass
all 81 Turtle-H cases (including 22 successful serializations and one representability rejection) through the adapter protocol, so the full suite runs
179 of 179 with these adapters.
The [requirement trace](./tests/requirements.ttl) links reviewed contracts to fixtures
and regression commands.

## Validation

- `h:AssertedBaseTripleShape`: required assertion check for reifier-filed statements.
- `h:HolonIntegrityShape`: advisory check for an explicit registry declaration on each holon used by `h:inHolon`.
- `h:ReifierMembershipShape`: membership node kinds and nonempty reification.
- `h:ContentGraphMappingShape`: mapping cardinality and graph-name kinds.
- `h:CompositionHierarchyShape`: parent cardinality and cycle checks for optional composition.

The shapes are partial checks. Registry resolution, triple-term validity, and mode-specific
validation also follow the normative processing algorithm. Imported shapes graphs are
checked for well-formedness before domain data validation.

Content-level validation parity excludes occurrence-specific and representation-specific
constraints. The reifier assertion shape requires triple-term query support or an equivalent procedure.

Run `python tests/rdf-h/check_composition.py` with rdflib installed. Install pyshacl
for the additional executable validation checks; otherwise those checks explicitly skip.

## Migration from 0.7

RDF-H 0.8 no longer defines the specialized part-whole vocabulary or its coherence
and cycle checks. Use an external vocabulary for domain parthood. `h:parentHolon`
is an administrative relation, not a replacement with equivalent meaning.
Aggregation now follows administrative descendants instead of domain mereology; it does not read ancestors. Prior drafts remain available in Git history.

## Repository contents

| Path | Purpose |
|---|---|
| [index.html](./index.html) | RDF-H ReSpec document. |
| [turtle-h/index.html](./turtle-h/index.html) | Turtle-H ReSpec document. |
| [sparql-h/index.html](./sparql-h/index.html) | Experimental SPARQL-H syntax and evaluation specification. |
| [rdfh.ttl](./rdfh.ttl) | Vocabulary and five partial SHACL checks. |
| [examples/](./examples/) | Representation and composition examples. |
| [tests/](./tests/) | Initial conformance fixtures. |
| [rdfh.css](./rdfh.css) | Legacy stylesheet; all specifications use standard W3C ReSpec styling. |

Each document maintains its own changelog. Release tags use `rdf-h-vX.Y.Z` and
`turtle-h-vX.Y.Z`, and `sparql-h-vX.Y.Z`. The vocabulary namespace remains `https://w3id.org/rdf-h#`;
its redirect publication remains tracked in the specification's open issues.

## Contributing and license

Use the [repository](https://github.com/geoknoesis/rdf-holon) for issues and contributions.
Specifications, vocabulary, and examples use the [Apache 2.0 license](./LICENSE).
