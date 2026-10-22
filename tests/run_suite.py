"""Manifest-driven Turtle-H/SPARQL-H tests; implementations connect through JSON adapters."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse, urldefrag
from urllib.request import url2pathname

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD
from rdflib.plugins.sparql.parser import parseQuery

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
QT = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-query#")
HT = Namespace("https://geoknoesis.github.io/rdf-holon/tests/vocab#")
EARL = Namespace("http://www.w3.org/ns/earl#")
TYPES = {str(HT[n]): (lang, op, expected) for n, lang, op, expected in [
    ("TurtleHPositiveSyntaxTest", "turtle-h", "parse", "accepted"),
    ("TurtleHNegativeSyntaxTest", "turtle-h", "parse", "rejected"),
    ("TurtleHEvalTest", "turtle-h", "evaluate", "ok"),
    ("TurtleHSerializerTest", "turtle-h", "serialize", "ok"),
    ("TurtleHNegativeSerializerTest", "turtle-h", "serialize", "rejected"),
    ("SPARQLHPositiveSyntaxTest", "sparql-h", "parse", "accepted"),
    ("SPARQLHNegativeSyntaxTest", "sparql-h", "parse", "rejected"),
    ("SPARQLHEvalTest", "sparql-h", "evaluate", "ok"),
    ("SPARQLHNegativeEvalTest", "sparql-h", "evaluate", "rejected"),
    ("RDFHConversionTest", "rdf-h", "convert", "ok"),
    ("RDFHNegativeConversionTest", "rdf-h", "convert", "rejected"),
    ("RDFHValidationTest", "rdf-h", "validate", "ok"),
    ("RDFHNegativeValidationTest", "rdf-h", "validate", "rejected"),
]}
H = Namespace("https://w3id.org/rdf-h#")
RDF_REIFIES = URIRef(str(RDF) + "reifies")  # RDF 1.2; absent from rdflib's RDF namespace
CONTAINS = {"type": "uri", "value": "urn:rdfh-tests:contains"}
HAS = {"type": "uri", "value": "urn:rdfh-tests:has"}


def local_path(resource):
    parsed = urlparse(urldefrag(str(resource))[0])
    if parsed.scheme != "file" or parsed.netloc not in ["", "localhost"]:
        raise ValueError(f"Only local file resources are loaded: {resource}")
    path = Path(url2pathname(parsed.path)).resolve()
    if not path.is_file():
        raise ValueError(f"Missing resource: {path}")
    return path


def exactly_one(g, subject, predicate, optional=False):
    values = list(g.objects(subject, predicate))
    if optional and not values:
        return None
    if len(values) != 1:
        raise ValueError(f"Expected one {predicate} on {subject}, found {len(values)}")
    return values[0]


def load_cases(path, visited=None):
    visited = set() if visited is None else visited
    path = path.resolve()
    if path in visited:
        raise ValueError(f"Repeated or cyclic manifest include: {path}")
    visited.add(path)
    g = Graph().parse(path, format="turtle")
    manifests = list(g.subjects(RDF.type, MF.Manifest))
    if len(manifests) != 1:
        raise ValueError(f"Expected one manifest in {path}")
    m = manifests[0]
    cases = []
    include = exactly_one(g, m, MF.include, optional=True)
    if include is not None:
        for child in Collection(g, include):
            cases.extend(load_cases(local_path(child), visited))
    entries = exactly_one(g, m, MF.entries, optional=True)
    if entries is not None:
        for test in Collection(g, entries):
            types = [str(t) for t in g.objects(test, RDF.type) if str(t) in TYPES]
            if len(types) != 1:
                raise ValueError(f"Missing or ambiguous project test class: {test}")
            lang, op, status = TYPES[types[0]]
            exactly_one(g, test, MF.name)
            action = exactly_one(g, test, MF.action)
            if lang == "rdf-h":
                query = g.value(action, HT.sourceDataset) or g.value(action, HT.sourceGraph)
            else:
                query = action if isinstance(action, URIRef) else exactly_one(g, action, QT.query)
            file = local_path(query)
            case = {"id": str(test), "language": lang, "operation": op, "expectedStatus": status,
                    "query": file, "baseURI": str(g.value(test, HT.base) or query), "g": g, "test": test}
            source = g.value(action, HT.sourceDataset)
            if source is not None:
                case["dataset"] = local_path(source)
                Dataset().parse(case["dataset"], format="trig")
            graph_source = g.value(action, HT.sourceGraph)
            if graph_source is not None:
                # Reifier-profile source: RDF 1.2 N-Triples plus a lossless term-JSON sidecar of the same triples.
                case["sourceGraph"] = local_path(graph_source)
                case["sourceTerms"] = local_path(exactly_one(g, action, HT.sourceTerms))
                source_terms = json.loads(case["sourceTerms"].read_text(encoding="utf-8"))
                rows = source_terms["graph"]
                graph_encoding(rows, source_terms.get("metadataGraph"))
                rendered = "".join(" ".join(render_term(term) for term in row) + " .\n" for row in rows)
                if case["sourceGraph"].read_text(encoding="utf-8").replace("\r\n", "\n") != rendered:
                    raise ValueError(f"RDF 1.2 source and term sidecar disagree: {test}")
                # M is explicit: a separate graph, or a view of the same source given in the sidecar.
                if "dataset" not in case and g.value(action, HT.metadataContext) is None and "metadataGraph" not in source_terms:
                    raise ValueError(f"A reifier-profile source needs an explicit metadata context: {test}")
            metadata = g.value(action, HT.metadataContext)
            if metadata is not None: case["metadataContext"] = local_path(metadata)
            regime = g.value(action, HT.entailmentRegime)
            if regime is not None: case["entailmentRegime"] = str(regime)
            params = g.value(action, HT.protocolParameters)
            if params is not None:
                case["protocolParameters"] = json.loads(str(params))
            case["ordered"] = bool(g.value(test, HT.ordered).toPython()) if g.value(test, HT.ordered) else False
            if op == "evaluate" and status == "ok":
                case["result"] = local_path(exactly_one(g, test, MF.result))
                if lang == "turtle-h":
                    case["terms"] = local_path(exactly_one(g, test, HT.resultTerms))
                    data = json.loads(case["terms"].read_text(encoding="utf-8"))
                    graph_encoding(data["graph"], data.get("metadataGraph"))
                    metadata_result = g.value(test, HT.metadataResult)
                    if metadata_result is not None:
                        metadata_path = local_path(metadata_result)
                        expected_metadata = {"graph": [[term_json(t) for t in row] for row in Graph().parse(metadata_path, format="turtle")]}
                        compare_results({"graph":data["metadataGraph"]}, expected_metadata)
                    expected_text = "".join(" ".join(render_term(term) for term in row) + " .\n" for row in data["graph"])
                    if case["result"].read_text(encoding="utf-8").replace("\r\n", "\n") != expected_text:
                        raise ValueError(f"RDF 1.2 result and term sidecar disagree: {test}")
                else:
                    if "dataset" not in case and "sourceGraph" not in case:
                        raise ValueError(f"Missing source dataset or graph: {test}")
                    lowered = g.value(test, HT.loweredQuery)
                    if lowered:
                        case["lowered"] = local_path(lowered)
                        parseQuery(case["lowered"].read_text(encoding="utf-8"))
                    if case["result"].suffix == ".srj":
                        result = json.loads(case["result"].read_text(encoding="utf-8"))
                        compare_results(result, result, case["ordered"])
                    else:
                        Graph().parse(case["result"], format="turtle")
            if op == "serialize":
                # The action is a G/M pair in term JSON; the result is the G/M expected after re-parsing the output.
                data = json.loads(file.read_text(encoding="utf-8"))
                graph_encoding(data["graph"], data.get("metadataGraph"))
                case["serializerInput"] = data
                if status == "ok":
                    case["result"] = case["terms"] = local_path(exactly_one(g, test, MF.result))
                    expected = json.loads(case["terms"].read_text(encoding="utf-8"))
                    graph_encoding(expected["graph"], expected.get("metadataGraph"))
            if lang == "rdf-h":
                if op == "convert":
                    case["targetRepresentation"] = str(exactly_one(g, action, HT.targetRepresentation))
                    case["preservationLevel"] = str(exactly_one(g, action, HT.preservationLevel))
                if op == "validate":
                    case["shapesDataset"] = local_path(exactly_one(g, action, HT.shapesDataset))
                    Dataset().parse(case["shapesDataset"], format="trig")
                    case["holon"] = str(exactly_one(g, action, HT.holon))
                    case["scope"] = str(exactly_one(g, action, HT.scope))
                if status == "ok":
                    case["result"] = case["terms"] = local_path(exactly_one(g, test, MF.result))
                    json.loads(case["terms"].read_text(encoding="utf-8"))
                else:
                    case["expectedError"] = str(exactly_one(g, test, HT.expectedError))
            if op == "evaluate" and status == "rejected":
                case["expectedError"] = str(exactly_one(g, test, HT.expectedError))
            if status == "rejected":
                category = exactly_one(g, test, HT.expectedError, optional=(op == "parse"))
                if category is not None: case["expectedError"] = str(category)
                condition = exactly_one(g, test, HT.expectedCondition, optional=True)
                if condition is not None: case["expectedCondition"] = str(condition)
            cases.append(case)
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate manifest test IDs")
    return cases


def render_term(term):
    kind = term["type"]
    if kind == "uri": return "<" + term["value"] + ">"
    if kind == "bnode": return "_:" + term["value"]
    if kind == "literal":
        value = json.dumps(term["value"], ensure_ascii=False)
        return value + ("@" + term["xml:lang"] + ("--" + term["direction"] if "direction" in term else "") if "xml:lang" in term else "^^<" + term["datatype"] + ">" if "datatype" in term else "")
    if kind == "triple":
        value = term["value"]
        return "<<( " + " ".join(render_term(value[k]) for k in ["subject", "predicate", "object"]) + " )>>"
    raise ValueError(f"Unknown term type: {kind}")


def term_key(value):
    """RDF term identity, independent of optional string datatypes and language-tag case."""
    def normalized(item):
        if isinstance(item, list): return [normalized(v) for v in item]
        if not isinstance(item, dict): return item
        result = {k: normalized(v) for k, v in item.items()}
        if result.get("type") == "literal":
            if result.get("datatype") == str(XSD.string): result.pop("datatype")
            if "xml:lang" in result: result["xml:lang"] = result["xml:lang"].lower()
        return result
    return json.dumps(normalized(value), sort_keys=True)


def graph_encoding(triples, metadata=None):
    """Lossless test-only encoding: compare RDF 1.2 graphs using RDF 1.1 isomorphism."""
    g, blank, terms = Graph(), {}, {}
    def encode(term):
        kind = term["type"]
        if kind == "uri":
            if not urlparse(term["value"]).scheme: raise ValueError("Expected an absolute IRI")
            return URIRef(term["value"])
        if kind == "bnode":
            return blank.setdefault(term["value"], BNode())
        if kind == "literal":
            if "xml:lang" in term and "datatype" in term: raise ValueError("Language and datatype are mutually exclusive")
            if "direction" in term:
                if term.get("direction") not in ["ltr", "rtl"] or not term.get("xml:lang"):
                    raise ValueError("Directional literals need a language and ltr/rtl direction")
                key = ("directional",term["value"],term["xml:lang"].lower(),term["direction"])
                if key not in terms:
                    node = terms[key] = BNode()
                    for triple in [(node,RDF.type,HT.DirectionalLiteral),(node,HT.lexical,Literal(term["value"])),
                                   (node,HT.language,Literal(term["xml:lang"].lower())),(node,HT.direction,Literal(term["direction"]))]: g.add(triple)
                return terms[key]
            return Literal(term["value"], lang=term.get("xml:lang"), datatype=None if term.get("datatype") == str(XSD.string) else term.get("datatype"), normalize=False)
        if kind == "triple":
            keys = ["subject", "predicate", "object"]
            key = tuple(encode(term["value"][k]) for k in keys)
            if key not in terms:
                node = terms[key] = BNode()
                g.add((node, RDF.type, HT.TripleTerm))
                for k, value in zip(keys, key):
                    g.add((node, HT[k], value))
            return terms[key]
        raise ValueError(f"Unknown term type: {kind}")
    # Assertion records prevent internal term encoding from colliding with user triples.
    components = [("urn:rdfh-tests:graph",triples)]
    if metadata is not None: components.append(("urn:rdfh-tests:metadata",metadata))
    for root, rows in components:
        seen = set()
        for row in rows:
            if len(row) != 3: raise ValueError("Expected triples")
            encoded = tuple(encode(value) for value in row)
            if encoded in seen: continue
            seen.add(encoded)
            node = BNode()
            g.add((URIRef(root), HT.assertion, node))
            for k, value in zip(["subject", "predicate", "object"], encoded): g.add((node,HT[k],value))
    return g


def term_json(node):
    if isinstance(node, URIRef): return {"type": "uri", "value": str(node)}
    if isinstance(node, BNode): return {"type": "bnode", "value": str(node)}
    value = {"type": "literal", "value": str(node)}
    if node.language: value["xml:lang"] = node.language
    elif node.datatype: value["datatype"] = str(node.datatype)
    return value


def expected_result(case):
    path = case.get("terms", case["result"])
    if path.suffix in [".json", ".srj"]:
        return json.loads(path.read_text(encoding="utf-8"))
    return {"graph": [[term_json(t) for t in row] for row in Graph().parse(path, format="turtle")]}


def compare_results(actual, expected, ordered=False):
    if "graph" in expected:
        if "metadataGraph" in expected and "metadataGraph" not in actual:
            raise ValueError("Missing metadata context result")
        if "graph" not in actual or not isomorphic(graph_encoding(actual["graph"],actual.get("metadataGraph")), graph_encoding(expected["graph"],expected.get("metadataGraph"))):
            raise ValueError("Graph mismatch (including occurrence identity and blank-node sharing)")
        return
    if "boolean" in expected:
        if type(actual.get("boolean")) is not bool or actual["boolean"] != expected["boolean"]:
            raise ValueError("ASK result mismatch")
        return
    variables = expected["head"]["vars"]
    if set(actual["head"]["vars"]) != set(variables): raise ValueError("Projected variables differ")
    def rows(result):
        encoded = []
        for row in result["results"]["bindings"]:
            normalized = {}
            for key, term in row.items():
                if key not in variables: raise ValueError("Unexpected binding variable")
                if term["type"] == "bnode": raise ValueError("Blank-node SELECT comparison is outside this initial suite")
                term = dict(term)
                if term.get("datatype") == str(XSD.string): term.pop("datatype")
                if "xml:lang" in term: term["xml:lang"] = term["xml:lang"].lower()
                normalized[key] = term
            encoded.append(json.dumps(normalized, sort_keys=True))
        return encoded
    a, e = rows(actual), rows(expected)
    mismatch = (a != e) if ordered else (Counter(a) != Counter(e))
    if mismatch:
        raise ValueError("SELECT result mismatch (order/multiplicity preserved as declared)")


def request_for(case):
    if case["operation"] == "serialize":
        return {"language": case["language"], "operation": "serialize",
                "input": {"path": str(case["query"]), "graph": case["serializerInput"]["graph"],
                          "metadataGraph": case["serializerInput"].get("metadataGraph", [])}}
    request = {"language": case["language"], "operation": case["operation"],
               "input": {"path": str(case["query"]), "text": case["query"].read_text(encoding="utf-8"), "baseURI": case["baseURI"]}}
    if "dataset" in case:
        request["representation"] = "dataset"
        request["sourceDataset"] = {"path": str(case["dataset"]), "format": "trig", "text": case["dataset"].read_text(encoding="utf-8")}
    if "sourceGraph" in case:
        request["representation"] = "reifier"
        request["sourceGraph"] = {"path": str(case["sourceGraph"]), "format": "n-triples-1.2",
                                  "text": case["sourceGraph"].read_text(encoding="utf-8"),
                                  "terms": json.loads(case["sourceTerms"].read_text(encoding="utf-8"))["graph"]}
    if "metadataContext" in case:
        request["metadataContext"] = {"path":str(case["metadataContext"]),"format":"turtle","text":case["metadataContext"].read_text(encoding="utf-8")}
    if "dataset" in case and "sourceGraph" in case: request["representation"] = "mixed"
    if "protocolParameters" in case: request["protocolParameters"] = case["protocolParameters"]
    if "entailmentRegime" in case: request["entailmentRegime"] = case["entailmentRegime"]
    if case["language"] == "rdf-h":
        del request["input"]
        if "sourceTerms" in case:
            sidecar = json.loads(case["sourceTerms"].read_text(encoding="utf-8"))
            if "metadataGraph" in sidecar: request["sourceGraph"]["metadataTerms"] = sidecar["metadataGraph"]
        for key in ["targetRepresentation", "preservationLevel", "holon", "scope"]:
            if key in case: request[key] = case[key]
        if "shapesDataset" in case:
            request["shapesDataset"] = {"path": str(case["shapesDataset"]), "format": "trig",
                                        "text": case["shapesDataset"].read_text(encoding="utf-8")}
    return request


def call_adapter(command, request, timeout):
    proc = subprocess.run(command, input=json.dumps(request), text=True, encoding="utf-8", capture_output=True, timeout=timeout, shell=False)
    if proc.returncode: raise ValueError(f"Adapter process failed with exit code {proc.returncode}")
    response = json.loads(proc.stdout)
    if not isinstance(response, dict): raise ValueError("Adapter response must be a JSON object")
    return response


def execute(case, command, timeout):
    if not command: return "SKIP", "No implementation adapter configured"
    try:
        response = call_adapter(command, request_for(case), timeout)
        if response.get("status") == "unsupported": return "SKIP", str(response.get("message", "Unsupported capability"))
        if response.get("status") != case["expectedStatus"]:
            raise ValueError(f"Expected {case['expectedStatus']}, received {response.get('status')}")
        if case["expectedStatus"] == "rejected":
            category = response.get("category")
            if case["operation"] == "parse" and category not in ["syntax", "dataset-conflict"]:
                raise ValueError("A syntax test must reject input as syntax/dataset-conflict, not as an execution failure")
            if case.get("expectedError") and category != case["expectedError"]: raise ValueError("Wrong rejection category")
            if case.get("expectedCondition") and response.get("condition") != case["expectedCondition"]:
                raise ValueError("Wrong or missing rejection condition")
        elif case["operation"] == "evaluate":
            compare_results(response["result"], expected_result(case), case["ordered"])
        elif case["operation"] == "convert":
            compare_conversion(response["result"], json.loads(case["terms"].read_text(encoding="utf-8")))
        elif case["operation"] == "validate":
            expected = json.loads(case["terms"].read_text(encoding="utf-8"))
            if response.get("result", {}).get("conforms") is not expected["conforms"]:
                raise ValueError("Validation outcome differs from the expected conformance")
        elif case["operation"] == "serialize":
            # The serializer's output is re-parsed by the same implementation, whose parser the expansion
            # tests check independently; the re-parsed G and M must equal the expected graphs.
            text = response.get("result", {}).get("text")
            if not isinstance(text, str): raise ValueError("Serializer result must contain Turtle-H text")
            reparse = call_adapter(command, {"language": "turtle-h", "operation": "evaluate",
                                             "input": {"text": text, "baseURI": "urn:rdfh-tests:serialized"}}, timeout)
            if reparse.get("status") != "ok": raise ValueError(f"Serialized output did not re-parse: {reparse.get('message', reparse.get('status'))}")
            compare_results(reparse["result"], expected_result(case))
        return "PASS", ""
    except (ValueError, KeyError, TypeError, subprocess.TimeoutExpired, OSError) as error:
        return "FAIL", str(error)


def triple_term(row):
    return {"type": "triple", "value": dict(zip(["subject", "predicate", "object"], row))}


def normalized_metadata(rows):
    """Graph names a converter derives for blank-node holons are free, so they are not compared."""
    out = []
    for s, p, o in rows:
        if p == {"type": "uri", "value": str(H.contentGraph)} and s["type"] == "bnode":
            o = {"type": "literal", "value": "derived graph name"}
        out.append([s, p, o])
    return out


def converted_content(result):
    """Each holon's direct content in a converted output, extracted by the RDF-H rules for its representation."""
    rows = []
    meta = result.get("metadataGraph", [])
    registry = []
    for s, p, o in meta:
        if (p == {"type": "uri", "value": str(RDF.type)} and o.get("value") in [str(H.Holon), str(H.CompleteHolon)]) or p == {"type": "uri", "value": str(H.contentGraph)}:
            if s["type"] in ["uri", "bnode"] and s not in registry: registry.append(s)
    if result.get("representation") == "reifier":
        reifies, holons = {}, {}
        base_keys = {term_key(row) for row in result["graph"] + meta}
        for s, p, o in result["graph"]:
            key = json.dumps(s, sort_keys=True)
            if p["value"] == str(RDF_REIFIES): reifies.setdefault(key, []).append(o)
            if p["value"] == str(H.inHolon): holons.setdefault(key, []).append(o)
        for key, holon_list in holons.items():
            if not reifies.get(key): raise ValueError("Converted membership has no reification")
            for holon in holon_list:
                if holon not in registry: raise ValueError("Converted membership uses an unregistered holon")
                for term in reifies[key]:
                    if term["type"] != "triple": raise ValueError("Converted reification is not a triple term")
                    base = [term["value"][k] for k in ["subject", "predicate", "object"]]
                    if term_key(base) not in base_keys: raise ValueError("Converted membership lacks its base assertion")
                    rows.append([holon, CONTAINS, term])
    elif result.get("representation") == "dataset":
        named, mapping = {}, {}
        for graph in result.get("namedGraphs", []):
            name = graph["name"]
            if name["type"] not in ["uri", "bnode"]: raise ValueError("Invalid converted graph name")
            key = json.dumps(name, sort_keys=True)
            if key in named: raise ValueError("Duplicate converted graph name")
            named[key] = graph["graph"]
        for s, p, o in meta:
            if p["value"] == str(H.contentGraph):
                if o["type"] not in ["uri", "bnode"]: raise ValueError("Invalid converted graph mapping")
                key = json.dumps(s, sort_keys=True)
                if key in mapping and mapping[key] != o: raise ValueError("Conflicting converted graph mapping")
                mapping[key] = o
        for holon in registry:
            name = mapping.get(json.dumps(holon, sort_keys=True), holon if holon["type"] == "uri" else None)
            if name is None: raise ValueError("Unmapped converted blank-node holon")
            for row in named.get(json.dumps(name, sort_keys=True), []) if name else []:
                rows.append([holon, CONTAINS, triple_term(row)])
    else:
        raise ValueError("Converted output must declare representation reifier or dataset")
    return rows


def conversion_view(meta, content, asserted=None):
    rows = [[{"type": "uri", "value": "urn:rdfh-tests:M"}, HAS, triple_term(r)] for r in normalized_metadata(meta)] + content
    if asserted is not None:
        rows += [[{"type": "uri", "value": "urn:rdfh-tests:G"}, HAS, triple_term(r)] for r in asserted]
    return rows


def compare_conversion(result, expected):
    """Compares M, every holon's content, and (for assertion preservation) all assertions, jointly."""
    expected_content = [[h["holon"], CONTAINS, triple_term(r)] for h in expected["holons"] for r in h["content"]]
    asserted = None
    if "assertedGraph" in expected:
        if result.get("representation") == "reifier":
            asserted = result["graph"] + result.get("metadataGraph", [])
        else:
            asserted = result.get("defaultGraph", []) + result.get("metadataGraph", []) + [r for g in result.get("namedGraphs", []) for r in g["graph"]]
    actual = conversion_view(result.get("metadataGraph", []), converted_content(result), asserted)
    wanted = conversion_view(expected["metadataGraph"], expected_content, expected.get("assertedGraph"))
    compare_results({"graph": actual}, {"graph": wanted})
    if expected.get("derivedMappings") and not result.get("reports"):
        raise ValueError("A converter must report the mappings it derives")


def semantic_smoke(cases):
    count = 0
    for case in cases:
        if case["language"] != "sparql-h" or "lowered" not in case: continue
        source = Dataset()
        source.parse(case["dataset"], format="trig")
        if "metadataContext" in case:
            source.default_context.remove((None,None,None))
            metadata = Graph().parse(case["metadataContext"],format="turtle")
            for triple in metadata: source.default_context.add(triple)
        mode = str(case["g"].value(case["test"], HT.scope))
        recipe = (ROOT / "examples/rdf-h/composition/queries" / (mode + ".rq")).read_text(encoding="utf-8")
        holon = case["g"].value(case["test"], HT.holon)
        if holon is not None:  # published recipes select ex:City; retarget them to the case's holon
            recipe = recipe.replace("ex:City", "<" + str(holon) + ">")
        scope = source.query(recipe).graph
        data = Dataset()
        for row in scope: data.default_context.add(row)
        result = data.query(case["lowered"].read_text(encoding="utf-8"))
        if result.type == "CONSTRUCT": actual = {"graph": [[term_json(t) for t in row] for row in result.graph]}
        else: actual = json.loads(result.serialize(format="json"))
        compare_results(actual, expected_result(case), case["ordered"])
        count += 1
    return count


def write_earl(path, outcomes, implementation):
    g = Graph(); g.bind("earl", EARL);g.bind("ht", HT)
    runner = URIRef("https://geoknoesis.github.io/rdf-holon/tests/run_suite.py")
    g.add((runner, RDF.type, EARL.Software))
    for record in outcomes:
        assertion, result = BNode(), BNode()
        for triple in [(assertion,RDF.type,EARL.Assertion),(assertion,EARL.assertedBy,runner),
                       (assertion,EARL.subject,URIRef(implementation)),(assertion,EARL.test,URIRef(record["id"])),
                       (assertion,EARL.mode,EARL.automatic),(assertion,EARL.result,result),(result,RDF.type,EARL.TestResult),
                       (result,EARL.outcome,{"PASS":EARL.passed,"FAIL":EARL.failed,"SKIP":EARL.untested}[record["status"]])]:g.add(triple)
        if record["message"]: g.add((result,EARL.info,Literal(record["message"])))
    g.serialize(path,format="turtle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest.ttl")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--semantic-smoke", action="store_true", help="Check expected lowerings only; not implementation conformance")
    parser.add_argument("--adapter-config", type=Path, help='JSON mapping language to command argument arrays')
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--report", type=Path, help="EARL Turtle output")
    parser.add_argument("--implementation", default="urn:rdfh-tests:unconfigured-implementation")
    parser.add_argument("--require-all", action="store_true", help="Fail the run if any test is skipped")
    args = parser.parse_args()
    cases = load_cases(args.manifest)
    print(f"VALID: {len(cases)} manifest entries, resources, and expected-result files")
    if args.semantic_smoke:
        print(f"SMOKE: {semantic_smoke(cases)} expected query translations agree with manifest results; no parser tested")
    if args.validate_only: return 0
    config = json.loads(args.adapter_config.read_text(encoding="utf-8")) if args.adapter_config else {}
    for lang, command in config.items():
        if lang not in ["turtle-h", "sparql-h", "rdf-h"] or not isinstance(command, list) or not command or not all(isinstance(v,str) for v in command):
            raise ValueError("Adapter configuration must map a supported language to a non-empty command argument array")
    records = []
    for case in cases:
        status, message = execute(case, config.get(case["language"]), args.timeout)
        records.append({"id":case["id"],"status":status,"message":message})
        if status == "FAIL": print(f"FAIL {case['id']}: {message}")
    counts = Counter(r["status"] for r in records)
    print(f"IMPLEMENTATION: {counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} untested")
    if args.report:
        write_earl(args.report, records, args.implementation)
        args.report.with_suffix(".json").write_text(json.dumps({"counts":dict(counts),"tests":records},indent=2)+"\n",encoding="utf-8")
    return 1 if counts["FAIL"] or (args.require_all and counts["SKIP"]) else 0


if __name__ == "__main__":
    try: sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"SUITE ERROR: {error}", file=sys.stderr)
        sys.exit(2)
