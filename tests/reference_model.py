"""Small executable model of RDF-H dataset contexts; not a production store."""
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
H = Namespace("https://w3id.org/rdf-h#")

class ContextError(ValueError):
    """Message is an RDF-H error-condition identifier from the processing algorithm."""
    category = "resolution"

class ConversionError(ContextError):
    """Valid source data cannot meet the target's preservation contract."""
    category = "unrepresentable-conversion"

    def __init__(self, detail):
        super().__init__("unrepresentable-conversion")
        self.detail = detail


def check_conversion_content(source, target):
    if source.registry != target.registry:
        raise ConversionError("The target changes the holon registry")
    for holon in source.registry:
        if set(source.direct(holon)) != set(target.direct(holon)):
            raise ConversionError("The target changes direct content for " + str(holon))


class DatasetContext:
    def __init__(self, dataset, metadata=None, require_graph_names=True, validate_mappings=True):
        self.dataset = dataset
        self.metadata = metadata if metadata is not None else dataset.default_context
        self.registry = set()
        for kind in [H.Holon, H.CompleteHolon]:
            self.registry.update(self.metadata.subjects(RDF.type, kind))
        self.registry.update(self.metadata.subjects(H.contentGraph, None))
        self.maps = {}
        for holon in self.registry:
            if not isinstance(holon, (URIRef, BNode)):
                raise ContextError("Invalid holon identifier")
            if not validate_mappings:
                continue  # Reifier-profile mappings register holons but select no graph.
            names = set(self.metadata.objects(holon, H.contentGraph))
            if len(names) > 1:
                raise ContextError("conflicting-mapping")
            if any(not isinstance(n, (URIRef, BNode)) for n in names):
                raise ContextError("invalid-graph-name")
            if names:
                self.maps[holon] = next(iter(names))
            elif isinstance(holon, BNode) and require_graph_names:
                raise ContextError("unmapped-blank-node-holon")
            else:
                self.maps[holon] = holon

    def direct(self, holon):
        if holon not in self.registry:
            raise ContextError("unknown-holon")
        return self.dataset.graph(self.maps[holon])

    def parents(self):
        parents = {}
        for child, parent in self.metadata.subject_objects(H.parentHolon):
            if child not in self.registry or parent not in self.registry:
                raise ContextError("unregistered-parent-endpoint")
            if child in parents and parents[child] != parent:
                raise ContextError("multiple-parents")
            parents[child] = parent
        for node in parents:
            seen = set()
            while node in parents:
                if node in seen: raise ContextError("parent-cycle")
                seen.add(node)
                node = parents[node]
        return parents

    def selected(self, holon, mode):
        self.direct(holon)
        if mode not in ["direct", "aggregated", "visible"]:
            raise ContextError("Unknown scope")
        chosen = {holon}
        if mode != "direct":
            parents = self.parents()
            while True:
                expanded = chosen | {child for child, parent in parents.items() if parent in chosen}
                if expanded == chosen: break
                chosen = expanded
        if mode == "visible":
            imports = set(self.metadata.objects(holon, H.imports))
            if not imports <= self.registry:
                raise ContextError("unresolved-import")
            chosen |= imports
        return chosen

    def asserted_graph(self):
        result = Graph()
        for graph in self.dataset.contexts():
            for triple in graph: result.add(triple)
        for triple in self.metadata: result.add(triple)
        return result

    def resolve(self, holon, mode):
        if mode == "global":
            self.direct(holon)  # Registration and representation checks still apply.
            return self.asserted_graph()
        result = Graph()
        for selected in self.selected(holon, mode):
            for triple in self.direct(selected): result.add(triple)
        return result


def effective_shapes(metadata, shapes_dataset, holon):
    """Union of the shapes graphs that M declares with h:importsShapes for holon; never inherited or transitive."""
    from rdflib import Graph as _Graph
    names = set(metadata.objects(holon, H.importsShapes))
    available = {context.identifier for context in shapes_dataset.contexts()}
    result = _Graph()
    for name in names:
        if name not in available:
            raise ContextError("missing-shapes-graph")
        for triple in shapes_dataset.graph(name):
            result.add(triple)
    return result


class ReifierContext(DatasetContext):
    """RDF 1.2 term-JSON source; ordinary-content reference extraction for tests."""
    def __init__(self, rows, metadata):
        from rdflib import Dataset
        super().__init__(Dataset(),metadata,require_graph_names=False,validate_mappings=False)
        self.rows = rows
        self.members = {}
        self.reifications = {}
        from run_suite import term_json
        self.base = {self.key(row) for row in rows}
        self.base.update(self.key([term_json(t) for t in triple]) for triple in self.metadata)
        for row in rows:
            subject,predicate,obj = row
            if predicate.get("value") == str(H.inHolon):
                holon = self.native(obj)
                if holon not in self.registry: raise ContextError("unregistered-membership-holon")
                self.members.setdefault(self.key(subject),set()).add(holon)
            if predicate.get("value") == str(URIRef(str(RDF)+"reifies")):
                self.reifications.setdefault(self.key(subject),[]).append(obj)
        for reifier in self.members:
            values = self.reifications.get(reifier,[])
            if not values: raise ContextError("missing-reification")
            for term in values:
                if term.get("type") != "triple": raise ContextError("non-triple-term-reification")
                row = [term["value"][k] for k in ["subject","predicate","object"]]
                if self.key(row) not in self.base: raise ContextError("missing-base-assertion")

    @staticmethod
    def key(value):
        from run_suite import term_key
        return term_key(value)

    @staticmethod
    def native(term):
        if term["type"] == "uri": return URIRef(term["value"])
        if term["type"] == "bnode": return BNode(term["value"])
        if term["type"] == "literal" and "direction" not in term:
            return Literal(term["value"],lang=term.get("xml:lang"),datatype=term.get("datatype"),normalize=False)
        raise ContextError("unsupported-capability")

    def direct(self,holon):
        if holon not in self.registry: raise ContextError("unknown-holon")
        result = Graph()
        for reifier,holons in self.members.items():
            if holon in holons:
                for term in self.reifications[reifier]:
                    result.add(tuple(self.native(term["value"][k]) for k in ["subject","predicate","object"]))
        return result

    def asserted_graph(self):
        result = Graph()
        for row in self.rows:
            result.add(tuple(self.native(term) for term in row))
        for triple in self.metadata: result.add(triple)
        return result


class MixedContext(DatasetContext):
    """Declared mixed data: a holon's named-graph content plus triples filed by reifier memberships found in any
    graph of the dataset (supplied here as term-JSON rows, since rdflib cannot parse triple terms)."""
    def __init__(self, dataset, rows, metadata=None):
        # In mixed data a blank-node holon may hold reifier-filed content only, so no mapping is required.
        super().__init__(dataset, metadata, require_graph_names=False)
        from run_suite import term_json
        everywhere = list(rows) + [[term_json(t) for t in triple] for g in dataset.contexts() for triple in g]
        self.reified = ReifierContext(everywhere, self.metadata)

    def direct(self, holon):
        result = Graph()
        for triple in super().direct(holon): result.add(triple)
        for triple in self.reified.direct(holon): result.add(triple)
        return result

    def asserted_graph(self):
        return self.reified.asserted_graph()


def content_preserving_reifier_view(context):
    """Test-model conversion: M is retained, unfiled data loss explicitly declared."""
    from run_suite import term_json
    rows = []
    for holon in context.registry:
        for triple in context.direct(holon):
            row = [term_json(t) for t in triple]
            occurrence = term_json(BNode())
            rows.extend([row,[occurrence,term_json(URIRef(str(RDF)+"reifies")),{"type":"triple","value":dict(zip(["subject","predicate","object"],row))}],
                         [occurrence,term_json(H.inHolon),term_json(holon)]])
    metadata = Graph()
    for triple in context.metadata: metadata.add(triple)
    try:
        result = ReifierContext(rows,metadata)
        check_conversion_content(context, result)
    except ContextError as error:
        if isinstance(error, ConversionError) or str(error) == "unsupported-capability":
            raise
        raise ConversionError(str(error)) from error
    result.preservation_level = "content-preserving"
    result.loss_categories = ["unfiled-source-assertions", "source-occurrence-structure"]
    return result


def dataset_profile_view(context):
    """Test-model conversion to the dataset profile. Blank-node holons receive a reported derived
    mapping; unfiled rows (including source membership records) are kept apart from M."""
    from rdflib import Dataset
    from run_suite import term_json
    from uuid import uuid4
    metadata = Graph()
    for triple in context.metadata: metadata.add(triple)
    derived = {}
    for holon in sorted(context.registry, key=str):
        if isinstance(holon, BNode) and metadata.value(holon, H.contentGraph) is None:
            derived[holon] = URIRef("urn:uuid:" + str(uuid4()))
            metadata.add((holon, H.contentGraph, derived[holon]))
    data = Dataset()
    for triple in metadata: data.default_context.add(triple)
    try:
        target = DatasetContext(data, metadata)
    except ContextError as error:
        raise ConversionError(str(error)) from error
    graph_contents = {}
    filed = set()
    for holon in context.registry:
        name = target.maps[holon]
        content = set(context.direct(holon))
        if name in graph_contents and graph_contents[name] != content:
            raise ConversionError("Different holon contents select the same target graph")
        graph_contents[name] = content
        for triple in content:
            data.graph(name).add(triple)
            filed.add(ReifierContext.key([term_json(t) for t in triple]))
    metadata_keys = {ReifierContext.key([term_json(t) for t in triple]) for triple in metadata}
    unfiled = [row for row in context.rows if ReifierContext.key(row) not in filed and ReifierContext.key(row) not in metadata_keys]
    result = DatasetContext(data, metadata)
    check_conversion_content(context, result)
    result.preservation_level = "assertion-preserving"
    result.derived_mappings = derived
    result.unfiled_rows = unfiled          # kept outside M and outside every content graph
    result.unfiled_graph = URIRef("urn:uuid:" + str(uuid4()))
    return result
