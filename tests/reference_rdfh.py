"""Experimental RDF-H reference adapter for the Conversion and Validation conformance classes; not a product."""
import json
import sys
from rdflib import BNode, Dataset, Graph, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID
from rdflib.namespace import RDF
from reference_model import H, ContextError, ConversionError, DatasetContext, ReifierContext, check_conversion_content, dataset_profile_view, effective_shapes
from run_suite import term_json

KEYS = ["subject", "predicate", "object"]
RDF_REIFIES = URIRef(str(RDF) + "reifies")  # RDF 1.2; absent from rdflib's RDF namespace


def rows_of(graph):
    return [[term_json(t) for t in triple] for triple in graph]


def metadata_of(request):
    if "metadataContext" in request:
        return Graph().parse(data=request["metadataContext"]["text"], format="turtle")
    terms = request.get("sourceGraph", {}).get("metadataTerms")
    if terms is None:
        return None
    graph = Graph()
    for row in terms:
        graph.add(tuple(ReifierContext.native(t) for t in row))
    return graph


def dataset_source(request):
    source = Dataset()
    source.parse(data=request["sourceDataset"]["text"], format="trig")
    return DatasetContext(source, metadata_of(request)), source


def convert(request):
    target, level = request["targetRepresentation"], request["preservationLevel"]
    reports = []
    if request["representation"] == "dataset" and target == "reifier":
        context, source = dataset_source(request)
        rows = []
        for holon in context.registry:
            for triple in context.direct(holon):
                base = [term_json(t) for t in triple]
                reifier = term_json(BNode())
                rows += [base, [reifier, term_json(RDF_REIFIES), {"type": "triple", "value": dict(zip(KEYS, base))}],
                         [reifier, term_json(H.inHolon), term_json(holon)]]
        if level == "assertion":
            for graph in source.contexts():
                rows += rows_of(graph)
        else:
            reports.append("loss category: unfiled assertions and named-graph placement are not retained")
        try:
            target_context = ReifierContext(rows, context.metadata)
            check_conversion_content(context, target_context)
        except ContextError as error:
            if isinstance(error, ConversionError) or str(error) == "unsupported-capability":
                raise
            raise ConversionError(str(error)) from error
        return {"representation": "reifier", "graph": rows, "metadataGraph": rows_of(context.metadata), "reports": reports}
    if request["representation"] == "reifier" and target == "dataset":
        metadata = metadata_of(request)
        if metadata is None:
            raise ContextError("missing-metadata-context")
        converted = dataset_profile_view(ReifierContext(request["sourceGraph"]["terms"], metadata))
        named = [{"name": term_json(g.identifier), "graph": rows_of(g)}
                 for g in converted.dataset.contexts() if g.identifier != DATASET_DEFAULT_GRAPH_ID and len(g)]
        if level == "assertion":
            named.append({"name": term_json(converted.unfiled_graph), "graph": converted.unfiled_rows})
        else:
            reports.append("loss category: unfiled assertions and occurrence metadata are not retained")
        reports += [f"derived h:contentGraph mapping for {holon}" for holon in converted.derived_mappings]
        return {"representation": "dataset", "defaultGraph": [], "namedGraphs": named,
                "metadataGraph": rows_of(converted.metadata), "reports": reports}
    raise ContextError("unsupported-capability")


def validate(request):
    from pyshacl import validate as shacl
    from pyshacl.errors import ReportableRuntimeError
    if request.get("representation") != "dataset":
        raise ContextError("unsupported-capability")
    context, _ = dataset_source(request)
    holon = URIRef(request["holon"])
    data = context.resolve(holon, request["scope"])
    shapes_dataset = Dataset()
    shapes_dataset.parse(data=request["shapesDataset"]["text"], format="trig")
    shapes = effective_shapes(context.metadata, shapes_dataset, holon)
    if len(shapes):
        try:
            shacl(Graph(), shacl_graph=shapes, meta_shacl=True)
        except ReportableRuntimeError:
            raise ContextError("ill-formed-shapes-graph")
        conforms = shacl(data, shacl_graph=shapes)[0]
    else:
        conforms = True
    return {"conforms": bool(conforms)}


def respond(request):
    if request.get("language") != "rdf-h":
        return {"status": "unsupported", "message": "This reference adapter implements RDF-H conversion and validation"}
    try:
        if request["operation"] == "convert":
            return {"status": "ok", "result": convert(request)}
        if request["operation"] == "validate":
            return {"status": "ok", "result": validate(request)}
    except ContextError as error:
        return {"status": "rejected", "category": str(error), "condition": str(error),
                "message": getattr(error, "detail", str(error))}
    return {"status": "unsupported", "message": "Unknown operation"}


if __name__ == "__main__":
    try:
        print(json.dumps(respond(json.load(sys.stdin))))
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
