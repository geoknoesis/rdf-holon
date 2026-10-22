"""Executable scope fixtures; requires rdflib. Run from any directory."""
from pathlib import Path
from rdflib import Dataset, Graph, Namespace

ROOT = Path(__file__).resolve().parents[2]
dataset = Dataset()
dataset.parse(ROOT / "examples/rdf-h/composition/scopes.trig", format="trig")
H = Namespace("https://w3id.org/rdf-h#")
EX = Namespace("https://example.org/")
metadata = dataset.default_context

def values(holons):
    return {str(value) for holon in holons for value in dataset.graph(holon).objects(None, EX.value)}

def selected(query):
    return {row[0] for row in metadata.query(query, initNs={"h": H, "ex": EX})}

# A standard GRAPH query is direct, despite parent links and imports.
assert {str(row[0]) for row in dataset.query(
    "SELECT ?v WHERE { GRAPH ex:City { ?s ex:value ?v } }", initNs={"ex": EX}
)} == {"city"}
assert values({EX.City}) == {"city"}
aggregated = selected("SELECT ?h WHERE { ?h h:parentHolon* ex:City }")
assert values(aggregated) == {"city", "district", "neighborhood"}
visible_query = """SELECT ?h WHERE {
    { ?h h:parentHolon* ex:City }
    UNION { ex:City h:imports ?h }
}"""
visible = selected(visible_query)
assert values(visible) == {"city", "district", "neighborhood", "metro"}
# No ancestors, ancestor/descendant imports, recursive imports, or imported descendants.
assert not ({"state", "root", "regulator", "remote", "metro-child", "local-authority"} & values(visible))
# An ancestor becomes visible only when City explicitly imports it.
metadata.add((EX.City, H.imports, EX.State))
assert values(selected(visible_query)) == {"city", "district", "neighborhood", "metro", "state"}
metadata.remove((EX.City, H.imports, EX.State))
# Cyclic and self imports do not trigger recursive scope expansion.
metadata.add((EX.Metro, H.imports, EX.City))
metadata.add((EX.City, H.imports, EX.City))
assert values(selected(visible_query)) == {"city", "district", "neighborhood", "metro"}
metadata.remove((EX.Metro, H.imports, EX.City))
metadata.remove((EX.City, H.imports, EX.City))
assert (EX.District, H.parentHolon, EX.City) in metadata
ontology = Graph().parse(ROOT / "rdfh.ttl", format="turtle")
assert (H.parentHolon, Namespace("http://www.w3.org/2000/01/rdf-schema#").subPropertyOf, H.partOf) not in ontology
print("PASS: direct graph query; recursive descendants; explicit imports; ancestors excluded; import boundaries")

# Shape imports are explicit, not inherited from the administrative parent.
shape_names = selected("SELECT ?s WHERE { ex:City h:importsShapes ?s }")
assert shape_names == {EX.CityShapes}
shapes_dataset = Dataset()
shapes_dataset.parse(ROOT / "examples/rdf-h/composition/shapes.trig", format="trig")
from rdflib.namespace import RDF, SH
assert (EX.CityShape, RDF.type, SH.NodeShape) not in dataset.graph(EX.CityShapes)
assert (EX.CityShape, RDF.type, SH.NodeShape) in shapes_dataset.graph(EX.CityShapes)
assert not any(True for _ in dataset.quads((EX.CityShape, None, None, None)))
print("PASS: explicit shape imports; shapes remain outside asserted data")

# Optional executable SHACL checks require pyshacl.
try:
    from pyshacl import validate
except ImportError:
    print("SKIP: install pyshacl to run validation checks")
else:
    effective_shapes = Graph()
    for name in shape_names:
        for triple in shapes_dataset.graph(name):
            effective_shapes.add(triple)
    valid, _, report = validate(dataset.graph(EX.City), shacl_graph=effective_shapes)
    assert valid, report
    all_shapes = Graph()
    for context in shapes_dataset.contexts():
        for triple in context:
            all_shapes.add(triple)
    valid, _, _ = validate(dataset.graph(EX.City), shacl_graph=all_shapes)
    assert not valid, "Accidentally inherited StateShapes must change this fixture's outcome"
    for body, expected in [
        ("ex:A h:parentHolon ex:B .", True),
        ("ex:A h:parentHolon ex:B, ex:C .", False),
        ("ex:A h:parentHolon ex:B . ex:B h:parentHolon ex:A .", False),
    ]:
        data = Graph().parse(data="@prefix h: <https://w3id.org/rdf-h#> . @prefix ex: <https://example.org/> . " + body, format="turtle")
        valid, _, report = validate(data, shacl_graph=ontology, use_shapes=[H.CompositionHierarchyShape])
        assert valid == expected, report
    print("PASS: explicit shape validation, parent cardinality, and cycle rejection")

# The current vocabulary must not define retired domain mereology or deep-content shapes.
for name in ["partOf", "hasPart", "componentOf", "hasComponent", "memberOf", "hasMember", "substanceOf", "hasSubstance", "portionOf", "hasPortion", "AcyclicPartShape", "MereologicalCoherenceShape", "ContextualCoherenceShape"]:
    assert not list(ontology.triples((H[name], None, None))), name
if "validate" in globals():
    # Domain cycles are outside RDF-H administrative hierarchy validation.
    data = Graph().parse(data="@prefix ex: <https://example.org/> . ex:A ex:componentOf ex:B . ex:B ex:componentOf ex:A .", format="turtle")
    valid, _, report = validate(data, shacl_graph=ontology, use_shapes=[H.CompositionHierarchyShape])
    assert valid, report
print("PASS: retired vocabulary absent; domain relations impose no RDF-H hierarchy constraints")
