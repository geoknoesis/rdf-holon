# Turtle-H and SPARQL-H conformance suites

The [root manifest](./manifest.ttl) includes the [Turtle-H](./turtle-h/manifest.ttl)
and [SPARQL-H](./sparql-h/manifest.ttl) manifests using W3C `mf:Manifest`,
`mf:include`, `mf:entries`, `mf:action`, and `mf:result`. Entries are ordered RDF
lists. Query actions reuse `qt:query`; SELECT and ASK results use SPARQL Results
JSON (`.srj`), and CONSTRUCT results use Turtle. Graph outputs are compared up to
blank-node renaming; unordered SELECT results use bag comparison, not set comparison.

These are project-authored draft tests, not W3C-approved test suites. Their custom
language classes and source-dataset metadata are defined in [vocab.ttl](./vocab.ttl).
They do not pretend that Turtle-H or SPARQL-H input is standard Turtle or SPARQL.
Existing W3C runners need support for these project test classes and adapter contracts.
All manifest resources use relative IRIs for local or hosted discovery.

## Coverage and status

| Suite | Positive syntax | Negative syntax | Evaluation | Expected execution errors | Serialization | Total |
|---|---:|---:|---:|---:|---:|---:|
| Turtle-H | 22 | 14 | 22 | 1 | 22 | 81 |
| SPARQL-H | 17 | 13 | 37 | 17 | 0 | 84 |
| RDF-H conversion and validation | 0 | 0 | 9 | 5 | 0 | 14 |
| Total | 39 | 27 | 68 | 23 | 22 | 179 |

Turtle-H covers empty blocks, base assertions, nested blocks without implied parents,
object/predicate lists, separate and repeated occurrences, blank-node holons, base
resolution, literals, outside statements, comments, and malformed input.
SPARQL-H covers all scopes and the default scope; SELECT/ASK/CONSTRUCT/counts;
subqueries and trailing VALUES; literal/comment and `HOLON:` prefix boundaries; graph
mappings, shared content graphs, and empty holons; missing holons/imports; invalid parent hierarchies; and dataset conflicts.
Existing RDF-H scope checks additionally cover cross-holon joins and shared blank nodes.

An experimental SPARQL-H reference adapter for both RDF-H profiles parses original source
using a grammar extension and RDFLib base productions, resolves M and scopes with a
separate executable model, and evaluates queries without expected lowerings or results.
It is not a production service, a full RDF 1.2 query engine, or independent multi-vendor
interoperability evidence. Turtle-H syntax/expansion needs an external parser; the RDF4J-based
[`rdf4j-rio-turtleh`](https://github.com/geoknoesis/rdf4j-rio-turtleh) adapter passes all 81 Turtle-H cases. It shares the editors' organization, so it is not
independent interoperability evidence either.
Full language execution uses an implementation adapter. Missing or unsupported adapters produce SKIP/EARL untested,
never PASS. A passing fixture-integrity check is not language conformance.
This is an initial suite, not an exhaustive reproduction of the base W3C language suites.
Implementations must also satisfy the underlying Turtle/SPARQL specifications.

## Run checks

```text
python -m pip install -r tests/requirements.txt
python tests/run_suite.py --validate-only --semantic-smoke
python tests/test_runner.py
python tests/test_semantics.py
python tests/run_suite.py --report tmp/conformance.ttl
```

Create the report directory before the last command. Without adapters, that command
reports 0 passed and 179 untested. `--semantic-smoke` checks 22 expected standard-query
translations against the manifest result files; it does not parse SPARQL-H source.
The harness self-tests verify result comparison, failure handling, and EARL reporting.

For implementation testing, copy `adapter-config.example.json`, replace its commands,
and run:

```text
python tests/run_suite.py --adapter-config adapter-config.json --require-all --implementation urn:example:my-processor --report tmp/conformance.ttl
```

Each command is an argument array and runs without a shell. Adapter relative paths
are interpreted from the runner's working directory. Choose an implementation IRI
for the EARL subject. The report contains local test IRIs when manifests are loaded
locally; remap those IRIs to the hosted suite location before publishing reports.
The runner writes both EARL Turtle and a sibling JSON summary.

Exit codes: 0 for successful validation or a run with no failures; 1 for test failure
(or any skip with `--require-all`); 2 for suite/configuration errors. Review counts:
exit 0 without `--require-all` does not mean every test ran.

## Source-parsing reference adapter

```text
python tests/run_suite.py --manifest tests/sparql-h/manifest.ttl --adapter-config tests/reference-adapters.json --require-all --implementation urn:rdfh-tests:reference-sparql-h
```

This executes 84 SPARQL-H tests from their original source, 11 of them over reifier-profile sources and one over declared mixed data. The reference adapter
uses the source M and registry algorithm rather than the published CONSTRUCT recipes.
`test_semantics.py` separately checks conversion invariance, registered/unknown holons,
mode-specific validation, malformed reification, mapping checks, empty-block gold
results, advanced Turtle expansion golds, and shape-definition collisions. Install
pyshacl to execute the SHACL-specific regression checks; they otherwise skip.

The [requirement trace](./requirements.ttl) links 21 reviewed contract groups to
manifest cases or regression commands. It is an initial trace, not an assertion that
all inherited Turtle/SPARQL requirements are exhaustively covered.

## Adapter contract

The runner starts the configured command once per case, sends one JSON request on
stdin, and expects one JSON object on stdout. Put logs on stderr. The default timeout
is 10 seconds per case and can be set with `--timeout`. Crashes, timeouts, invalid JSON,
and malformed results are failures, including on negative tests.

A syntax request has this shape:

```json
{
  "language": "sparql-h",
  "operation": "parse",
  "input": {
    "path": "/absolute/path/query.srqh",
    "text": "PREFIX ex: <https://example.org/> SELECT * FROM HOLON ex:City WHERE { ?s ?p ?o }",
    "baseURI": "file:///absolute/path/query.srqh"
  }
}
```

Return `{"status":"accepted"}` for accepted SPARQL-H syntax, or
`{"status":"rejected","category":"syntax"}` for a syntax rejection. Input that an adapter would
run as ordinary SPARQL (no holon clause, for example `FROM HOLON:City`) is not SPARQL-H and is
reported as a syntax rejection here. Dataset-clause
conflicts may use category `dataset-conflict`. Runtime failures do not satisfy syntax
rejection tests. `{"status":"unsupported","message":"..."}` is an explicit skip.

Serialization requests use `"operation":"serialize"` and carry `"input":{"graph":[...],"metadataGraph":[...]}`
in the term encoding below. Return `{"status":"ok","result":{"text":"..."}}` with Turtle-H text. An unrepresentable G/M pair returns
`{"status":"rejected","category":"unrepresentable-context","condition":"unrepresentable-context"}`; it must not promote inactive management assertions into M. The runner
re-parses that text with the same adapter (an `evaluate` request) and compares the resulting G and M with the
expected graphs, so serializer tests rely on the parser that the expansion tests check. Most of the 22 inputs are
chosen so that the folding rules reproduce them exactly: the 18 original expansion results, an IRI reifier, a
reifier with occurrence metadata, and a triple with one foldable and one non-foldable occurrence. One input gives M
a non-management statement, and its expected result is M reduced to its management statements.

Evaluation requests use `"operation":"evaluate"`. SPARQL-H evaluation adds
`"representation":"dataset"` with `"sourceDataset":{"path":"...","format":"trig","text":"..."}`, or
`"representation":"reifier"` with `"sourceGraph":{"path":"...","format":"n-triples-1.2","text":"...","terms":[...]}`,
where `terms` is the same graph in the term encoding below for adapters without an RDF 1.2 parser. Reifier-profile
requests always carry an explicit `metadataContext`, since that profile never infers M. A request with both a
`sourceDataset` and a `sourceGraph` is `"representation":"mixed"`: the rows of `sourceGraph.terms` are additional
default-graph statements of the dataset, memberships among them file triples whose base assertion may be in any
graph, and M defaults to the dataset's default graph. Protocol conflict cases
add `"protocolParameters":{...}`. The source dataset is RDF-H input,
not the query's resolved default graph. Adapters must parse the holon clause and
resolve it themselves. An external M can be supplied as `metadataContext` with `path`, `format: "turtle"`,
and `text`. Without it, the dataset default graph is M. Expected scope, lowered query,
and expected results are not sent to adapters. Return `{"status":"ok","result":...}` for evaluation success.
Expected execution errors return `{"status":"rejected","category":"resolution"}`
or the manifest's other specified category. Fixtures with `ht:expectedCondition` additionally require a `"condition"` naming the
exact error condition (for example `parent-cycle`); both category and condition must match. All 15 named
processing conditions have such fixtures. Missing or wrong conditions fail.

SELECT and ASK `result` values are ordinary SPARQL Results JSON objects, including
`head` and `results`, or `head` and `boolean`. The current SELECT fixtures have no
blank-node bindings; the initial comparator rejects such bindings rather than
claiming an unsupported comparison. It preserves row multiplicity and checks order
only where `ht:ordered true` is declared. String literals may omit `xsd:string`.

## RDF-H conversion and validation requests

The `rdf-h` language tests the optional conversion and validation capabilities of RDF-H itself. The reference
adapter is `tests/reference_rdfh.py`. Requests carry a source exactly as SPARQL-H evaluation requests do
(`representation` with `sourceDataset`, or `sourceGraph` with `terms`); a reifier source whose M is a view of the
same source sends it as `sourceGraph.metadataTerms`, sharing blank-node labels with `terms`.

`"operation":"convert"` adds `targetRepresentation` (`dataset` or `reifier`) and `preservationLevel` (`content` or
`assertion`). Return `{"status":"ok","result":{...}}` where the result declares `representation` and gives
`metadataGraph`, plus `graph` for a reifier target or `defaultGraph` and `namedGraphs` (`[{"name":term,"graph":[...]}]`)
for a dataset target, and `reports` listing losses and derived mappings. If the target would be invalid or
change any holon's content, reject with category and condition `unrepresentable-conversion` instead of returning a target. The runner checks target membership and mapping validity, then extracts each holon's direct
content from the output by the RDF-H rules for that representation and compares M, that content, and, for
assertion preservation, the union of all output graphs, jointly with the expected graphs. Graph names derived for
blank-node holons are not compared, but a conversion that derives one must report it.

`"operation":"validate"` adds `shapesDataset` (TriG), `holon`, and `scope`. Return
`{"status":"ok","result":{"conforms":true}}` or `false`, or reject with the RDF-H error condition as the category,
for example `{"status":"rejected","category":"missing-shapes-graph"}`.

## RDF graph outputs, including RDF 1.2 triple terms

Turtle-H requires RDF 1.2 triple terms, which the runner's RDFLib dependency cannot
parse natively. Each expansion test therefore has an RDF 1.2 N-Triples expected file
(`mf:result`) plus a lossless JSON term sidecar (`ht:resultTerms`). `.nt12` and `.ttlh`
are repository filename conventions. Fixture validation checks that the sidecar and
RDF 1.2 expected text agree; it is not a substitute for a complete RDF 1.2 parser.

Adapters return graph results (also for SPARQL-H CONSTRUCT) as:

```json
{
  "status": "ok",
  "result": {
    "graph": [
      [
        {"type":"bnode","value":"occurrence1"},
        {"type":"uri","value":"http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies"},
        {"type":"triple","value":{
          "subject":{"type":"uri","value":"https://example.org/s"},
          "predicate":{"type":"uri","value":"https://example.org/p"},
          "object":{"type":"literal","value":"hello","xml:lang":"en"}
        }}
      ]
    ]
  }
}
```

This is a suite adapter format, not a new RDF or SPARQL result standard. Turtle-H evaluation additionally returns `metadataGraph` as an array of triples,
corresponding to `ht:metadataResult`; data and metadata are compared jointly to preserve
shared blank-node identity. Every block contributes registration to both graphs.
A graph is
an array of subject/predicate/object arrays. Terms use `uri`, `bnode`, `literal`, or
`triple`; literal lexical values are strings, with optional `datatype` or `xml:lang`.
The latter two are mutually exclusive. Directional literals additionally use
`"direction":"ltr"` or `"direction":"rtl"` with `xml:lang`; the expected RDF 1.2
text uses `@en--ltr` or the corresponding language/direction. Direction is preserved,
including within triple terms, rather than silently flattened to a string. IRIs are absolute. Blank-node labels are
local to the complete returned graph and must preserve sharing, including inside
triple terms. `triple.value` holds `subject`, `predicate`, and `object` terms.

The runner losslessly encodes assertions and triple terms for graph-isomorphism
comparison; it does not flatten triple terms to strings. Arbitrary blank-node
renaming is accepted, but collapsed occurrence identities, lost base statements,
extra memberships, and changed blank-node sharing fail.

## Maintenance

`manifest.ttl` files are authoritative. The earlier `sparql-h/manifest.json` is a
legacy fixture snapshot retained for compatibility; the compatibility checker now
reads the RDF manifest. Add new cases to the RDF manifests and their expected files.
All tests remain draft entries; no W3C approval is asserted. Expected results are
project-authored and use the repository Apache 2.0 license.

The design follows the [W3C RDF test manifest convention](https://w3c.github.io/rdf-tests/),
[SPARQL test manifests](https://github.com/w3c/rdf-tests/tree/main/sparql/sparql11),
and [EARL](https://www.w3.org/TR/EARL10-Schema/).

The reference RDF-H adapter supports conversion in both directions and domain validation
for dataset-profile inputs, including global G. Reifier or mixed validation requests
report `unsupported-capability`; this experimental adapter does not silently omit their assertions.
