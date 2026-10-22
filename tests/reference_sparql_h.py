"""Experimental source-parsing SPARQL-H dataset adapter; uses RDFLib for SPARQL."""
import json
import sys
from dataclasses import dataclass

from pyparsing import CaselessKeyword, Keyword, Located, Optional, ParseBaseException, StringEnd, pythonStyleComment
from rdflib import Dataset, Graph, URIRef
from rdflib.plugins.sparql import parser as p
from rdflib.plugins.sparql.algebra import translateQuery
from reference_model import ContextError, DatasetContext, MixedContext, ReifierContext
from run_suite import term_json

@dataclass
class HolonClause:
    start: int
    end: int
    term: object
    mode: str
    named: bool = False

def parse_source(text, base=None):
    # Reuse the base language productions; token-aware parsing protects literals/comments.
    # "HOLON:" starts a prefixed name (ordinary FROM), so ':' may not follow the keyword.
    holon_keyword = CaselessKeyword("HOLON", ident_chars=Keyword.DEFAULT_KEYWORD_CHARS + ":")
    expression = Located(CaselessKeyword("FROM") + holon_keyword + p.iri +
                         Optional(CaselessKeyword("SCOPE") +
                                  (CaselessKeyword("DIRECT") | CaselessKeyword("AGGREGATED") | CaselessKeyword("VISIBLE"))) +
                         Optional(CaselessKeyword("FROM") + CaselessKeyword("NAMED") + CaselessKeyword("HOLONS")))
    # Located returns named fields directly in pyparsing 3.
    def capture(tokens):
        value = list(tokens.value)
        words = [v for v in value if isinstance(v, str)]
        mode = words[words.index("SCOPE") + 1].lower() if "SCOPE" in words else "direct"
        return HolonClause(tokens.locn_start, tokens.locn_end, value[2], mode, "HOLONS" in words)
    expression.set_parse_action(capture)
    grammar = p.Prologue + ((p.SelectClause + expression + p.WhereClause + p.SolutionModifier) |
                           (CaselessKeyword("CONSTRUCT") + p.ConstructTemplate + expression + p.WhereClause + p.SolutionModifier) |
                           (CaselessKeyword("ASK") + expression + p.WhereClause + p.SolutionModifier)) + p.ValuesClause + StringEnd()
    grammar.ignore(pythonStyleComment)
    grammar.parse_with_tabs()
    parsed = grammar.parse_string(text, parse_all=True)
    clauses = [value for value in parsed if isinstance(value, HolonClause)]
    if len(clauses) != 1: raise ValueError("Expected one outer holon clause")
    clause = clauses[0]
    lowered = text[:clause.start] + text[clause.end:]
    translated = translateQuery(p.parseQuery(lowered), base=base)
    try:
        holon = translated.prologue.absolutize(clause.term)
    except Exception as error:
        if str(error).startswith("Unknown namespace prefix"): raise ValueError(str(error)) from error
        raise
    if not isinstance(holon, URIRef): raise ValueError("Holon must resolve to an IRI")
    return holon, clause.mode, lowered, clause.named

def respond(request):
    if request.get("language") != "sparql-h":
        return {"status":"unsupported", "message":"This reference adapter supports SPARQL-H inputs"}
    try:
        holon, scope, lowered, named = parse_source(request["input"]["text"], request["input"].get("baseURI"))
    except (ParseBaseException, ValueError, KeyError, TypeError) as error:
        return {"status":"rejected", "category":"syntax", "message":str(error)}
    if request["operation"] == "parse": return {"status":"accepted"}
    if request.get("protocolParameters"):
        if any(k in request["protocolParameters"] for k in ["default-graph-uri", "named-graph-uri"]):
            return {"status":"rejected", "category":"dataset-conflict"}
    regime = request.get("entailmentRegime")
    if regime is not None and regime != "http://www.w3.org/ns/entailment/Simple":
        return {"status":"rejected", "category":"unsupported-capability", "condition":"unsupported-capability", "message":"Only simple entailment is supported"}
    try:
        metadata = None
        if "metadataContext" in request:
            metadata = Graph().parse(data=request["metadataContext"]["text"],format="turtle")
        if request.get("representation") == "reifier":
            # The reifier profile never infers M from the data.
            if metadata is None: raise ContextError("missing-metadata-context")
            context = ReifierContext(request["sourceGraph"]["terms"], metadata)
        elif request.get("representation") == "mixed":
            source = Dataset()
            source.parse(data=request["sourceDataset"]["text"], format="trig", publicID=request["sourceDataset"].get("baseURI"))
            context = MixedContext(source, request["sourceGraph"]["terms"], metadata)
        else:
            source = Dataset()
            source.parse(data=request["sourceDataset"]["text"], format="trig", publicID=request["sourceDataset"].get("baseURI"))
            context = DatasetContext(source, metadata)
        graph = context.resolve(holon, scope)
        data = Dataset()
        for triple in graph: data.default_context.add(triple)
        if named:  # attributed scope dataset: one named graph per selected holon
            for selected in context.selected(holon, scope):
                selected_graph = data.graph(selected)  # Empty selected holons still name graphs.
                for triple in context.direct(selected): selected_graph.add(triple)
        result = data.query(lowered, base=request["input"].get("baseURI"))
        if result.type == "CONSTRUCT": payload = {"graph":[[term_json(t) for t in row] for row in result.graph]}
        else: payload = json.loads(result.serialize(format="json"))
        return {"status":"ok", "result":payload}
    except ContextError as error:
        category = "unsupported-capability" if str(error) == "unsupported-capability" else error.category
        return {"status":"rejected", "category":category, "condition":str(error), "message":str(error)}

if __name__ == "__main__":
    try:
        print(json.dumps(respond(json.load(sys.stdin))))
    except Exception as error:
        # An unexpected implementation error is a runner failure, not a successful syntax rejection.
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
