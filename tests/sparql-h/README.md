# SPARQL-H conformance tests

The authoritative RDF manifest contains 17 positive syntax, 13 negative syntax,
37 evaluation, and 17 expected execution-error cases: 84 tests total. `FROM NAMED HOLONS`
(attribution of statements to holons through `GRAPH ?h`) and declared mixed data are covered. Eleven tests use a
reifier-profile source (RDF 1.2 N-Triples with an explicit M): direct, aggregated, and visible
scopes, exclusion of membership bookkeeping and unfiled assertions, and the unknown-holon,
missing-base-assertion, unregistered-membership, non-triple-term, and missing-reification errors.
Additional cases check an assertion supplied only in M, ignored reifier-profile graph mappings, and attribution of a blank-node descendant.
Every RDF-H error condition raised by resolution has at least one test that checks the exact condition; the table of error
conditions in RDF-H names them. Requests may name an entailment regime with `entailmentRegime`.

The reference adapter covers both profiles and parses original source independently of the
expected lowerings and results. Run:

```text
python tests/run_suite.py --manifest tests/sparql-h/manifest.ttl --adapter-config tests/reference-adapters.json --require-all
```

`--validate-only --semantic-smoke` instead checks fixtures and 22 expected translations;
it does not exercise the source parser. `check_examples.py` is a compatibility command
for that smoke mode. The earlier JSON manifest is a legacy snapshot.

The reference adapter is not a production endpoint or full RDF 1.2 query implementation.
Independent implementation interoperability remains to be established. See the
[suite guide](../README.md) and [requirement trace](../requirements.ttl).
