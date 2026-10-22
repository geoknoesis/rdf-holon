"""Execute the published SPARQL 1.1 scope recipes. Requires rdflib."""
from pathlib import Path
from rdflib import BNode, Dataset, Graph, Literal, Namespace
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[2]
EX = Namespace("https://example.org/")
H = Namespace("https://w3id.org/rdf-h#")
QUERY_DIR = ROOT / "examples/rdf-h/composition/queries"
QUERIES = {scope: (QUERY_DIR / (scope + ".rq")).read_text(encoding="utf-8")
           for scope in ["direct", "aggregated", "visible"]}
READ = (QUERY_DIR / "read-values.rq").read_text(encoding="utf-8")
EXPECTED = {
    "direct": {"city"},
    "aggregated": {"city", "district", "neighborhood"},
    "visible": {"city", "district", "neighborhood", "metro"},
}

def fixture():
    data = Dataset()
    data.parse(ROOT / "examples/rdf-h/composition/scopes.trig", format="trig")
    return data

def resolve(data, scope):
    return data.query(QUERIES[scope]).graph

def verify_values(data):
    for scope, expected in EXPECTED.items():
        graph = resolve(data, scope)
        assert {str(row[0]) for row in graph.query(READ)} == expected, scope

source = fixture()
verify_values(source)
# Explicit graph mappings must replace, not supplement, the holon-IRI default.
for holon in [EX.City, EX.District, EX.Metro]:
    replacement = EX[str(holon).rsplit("/", 1)[-1] + "Content"]
    for triple in list(source.graph(holon)):
        source.graph(replacement).add(triple)
    source.graph(holon).remove((None, None, None))
    source.graph(holon).add((holon, EX.value, Literal("decoy")))
    source.default_context.add((holon, H.contentGraph, replacement))
verify_values(source)
print("PASS: all published scope queries, including explicit content-graph mappings")

source = fixture()
shared = (EX.Common, EX.flag, Literal("shared"))
for name in [EX.City, EX.District, EX.Metro]:
    source.graph(name).add(shared)
source.graph(EX.City).add((EX.City, EX.hasDistrict, EX.District))
source.graph(EX.District).add((EX.District, EX.name, Literal("Central")))
owner = BNode("shared-owner")
source.graph(EX.City).add((owner, EX.label, Literal("Alice")))
source.graph(EX.District).add((EX.District, EX.owner, owner))
join = """PREFIX ex: <https://example.org/>
ASK { ex:City ex:hasDistrict ?district . ?district ex:name "Central" }
"""
blank_join = """PREFIX ex: <https://example.org/>
ASK { ex:District ex:owner ?owner . ?owner ex:label "Alice" }
"""
within_one_graph = """PREFIX ex: <https://example.org/>
ASK { GRAPH ?g { ex:City ex:hasDistrict ?district . ?district ex:name "Central" } }
"""
assert not source.query(within_one_graph).askAnswer
for scope in QUERIES:
    graph = resolve(source, scope)
    assert graph.query(join).askAnswer == (scope != "direct")
    assert graph.query(blank_join).askAnswer == (scope != "direct")
    count = graph.query("SELECT (COUNT(*) AS ?n) WHERE { ?s <https://example.org/flag> ?v }")
    assert int(next(iter(count))[0]) == 1, "The scope graph must deduplicate triples"
    # A default-only query dataset does not turn GRAPH City into a scope operation.
    query_dataset = Dataset()
    for triple in graph:
        query_dataset.default_context.add(triple)
    assert query_dataset.query(join).askAnswer == (scope != "direct")
    assert not query_dataset.query("ASK { GRAPH <https://example.org/City> { ?s ?p ?o } }").askAnswer
print("PASS: cross-holon joins, shared blank-node identity, triple deduplication, default-only query dataset")

# A validated empty holon contributes an empty scope graph.
empty = Dataset()
empty.default_context.add((EX.City, RDF.type, H.Holon))
for scope in QUERIES:
    assert len(resolve(empty, scope)) == 0
print("PASS: empty direct, aggregated, and visible scopes")
