"""Regression checks for the review findings, independent of the published scope recipes."""
import copy
import json
from pathlib import Path
import unittest
from rdflib import Dataset,Graph,Literal,Namespace,URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF
from reference_model import ContextError,DatasetContext,MixedContext,ReifierContext,content_preserving_reifier_view,dataset_profile_view,effective_shapes
from reference_sparql_h import parse_source
from run_suite import graph_encoding

H=Namespace("https://w3id.org/rdf-h#")
EX=Namespace("https://example.org/")
ROOT=Path(__file__).resolve().parents[1]
PREFIX="@prefix h: <https://w3id.org/rdf-h#> . @prefix ex: <https://example.org/> . "

def source(text):
    d=Dataset();d.parse(data=PREFIX+text,format="trig");return d

class SemanticTests(unittest.TestCase):
    def test_base_assertions_use_rdf_term_equality(self):
        from run_suite import term_json, triple_term, converted_content
        meta = Graph(); meta.add((EX.A, RDF.type, H.Holon))
        for asserted, reified in [
            ({"type": "literal", "value": "x", "datatype": "http://www.w3.org/2001/XMLSchema#string"},
             {"type": "literal", "value": "x"}),
            ({"type": "literal", "value": "x", "xml:lang": "EN"},
             {"type": "literal", "value": "x", "xml:lang": "en"})]:
            base = [term_json(EX.s), term_json(EX.p), asserted]
            term = triple_term([term_json(EX.s), term_json(EX.p), reified])
            r = term_json(EX.occ)
            rows = [base, [r, term_json(URIRef(str(RDF)+"reifies")), term],
                    [r, term_json(H.inHolon), term_json(EX.A)]]
            context = ReifierContext(rows, meta)
            self.assertEqual(len(context.direct(EX.A)), 1)
            self.assertEqual(len(converted_content({"representation": "reifier", "graph": rows,
                                                   "metadataGraph": [[term_json(t) for t in triple] for triple in meta]})), 1)

    def test_conversion_retains_existing_blank_node_mapping(self):
        from rdflib import BNode
        from run_suite import term_json, triple_term
        holon = BNode("mapped-holon")
        meta = Graph(); meta.add((holon, H.contentGraph, EX.Existing))
        triple = [term_json(t) for t in (EX.s, EX.p, EX.o)]
        r = term_json(BNode("occurrence"))
        rows = [triple, [r, term_json(URIRef(str(RDF)+"reifies")), triple_term(triple)],
                [r, term_json(H.inHolon), term_json(holon)]]
        converted = dataset_profile_view(ReifierContext(rows, meta))
        self.assertEqual(converted.derived_mappings, {})
        self.assertEqual(set(converted.metadata), set(meta))
        self.assertEqual(converted.maps[holon], EX.Existing)
        self.assertEqual(set(converted.direct(holon)), {(EX.s, EX.p, EX.o)})

    def test_unfiled_output_graph_does_not_reuse_a_content_graph_name(self):
        from run_suite import term_json
        meta = Graph(); meta.add((EX.A, H.contentGraph, URIRef("urn:rdfh:unfiled")))
        unfiled = [[term_json(t) for t in (EX.s, EX.p, EX.o)]]
        converted = dataset_profile_view(ReifierContext(unfiled, meta))
        self.assertNotIn(converted.unfiled_graph, converted.maps.values())
        self.assertEqual(len(converted.direct(EX.A)), 0)
        self.assertEqual(converted.unfiled_rows, unfiled)

    def test_content_predicates_do_not_become_declarations_after_conversion(self):
        d=source('ex:A a h:Holon . ex:B a h:Holon . ex:A { ex:A h:parentHolon ex:B . ex:A ex:value "A" . }')
        named=DatasetContext(d);reified=content_preserving_reifier_view(named)
        self.assertTrue(isomorphic(named.metadata,reified.metadata))
        self.assertNotIn((EX.A,H.parentHolon,EX.B),reified.metadata)
        for scope in ["direct","aggregated","visible"]:
            for holon in [EX.A,EX.B]:self.assertTrue(isomorphic(named.resolve(holon,scope),reified.resolve(holon,scope)))
        self.assertEqual(len(reified.resolve(EX.B,"aggregated")),0)
        self.assertEqual(reified.preservation_level,"content-preserving")
        self.assertIn("unfiled-source-assertions",reified.loss_categories)

    def test_dataset_conversion_derives_blank_node_mappings_and_separates_unfiled(self):
        # Reifier source: IRI holon A, blank-node holon _:h, one unfiled provenance statement.
        from rdflib import BNode
        from run_suite import term_json
        h=BNode("h")
        metadata=Graph();metadata.add((EX.A,RDF.type,H.Holon));metadata.add((h,RDF.type,H.Holon))
        def row(s,p,o):return [term_json(s),term_json(p),term_json(o)]
        def member(n,holon,triple):
            r={"type":"bnode","value":"r"+str(n)}
            return [triple,[r,term_json(URIRef(str(RDF)+"reifies")),{"type":"triple","value":dict(zip(["subject","predicate","object"],triple))}],[r,term_json(H.inHolon),term_json(holon)]]
        rows=member(1,EX.A,row(EX.A,EX.value,Literal("a")))+member(2,h,row(EX.B,EX.value,Literal("b")))+[row(EX.A,EX.source,EX.Doc)]
        reified=ReifierContext(rows,metadata);converted=dataset_profile_view(reified)
        # derived mapping only for the blank-node holon, reported, and the only change to M
        self.assertEqual(set(converted.derived_mappings),{h})
        extra=set(converted.metadata)-set(reified.metadata)
        self.assertEqual(extra,{(h,H.contentGraph,converted.derived_mappings[h])})
        # content equality for both holons after conversion
        for holon in [EX.A,h]:self.assertTrue(isomorphic(reified.resolve(holon,"direct"),converted.resolve(holon,"direct")))
        # unfiled assertions and membership records are kept, but outside M and outside content graphs
        keys={ReifierContext.key(r) for r in converted.unfiled_rows}
        self.assertIn(ReifierContext.key(row(EX.A,EX.source,EX.Doc)),keys)
        self.assertTrue(any(r[1].get("value")==str(H.inHolon) for r in converted.unfiled_rows))
        self.assertNotIn((EX.A,EX.source,EX.Doc),converted.metadata)
        self.assertNotIn((EX.A,EX.source,EX.Doc),converted.resolve(EX.A,"direct"))
        # and back: content-preserving return trip keeps content, M equal up to the derived mapping
        back=content_preserving_reifier_view(converted)
        for holon in [EX.A,h]:self.assertTrue(isomorphic(reified.resolve(holon,"direct"),back.resolve(holon,"direct")))
        self.assertEqual(set(back.metadata)-set(reified.metadata),extra)

    def test_invalid_mapping_elsewhere_fails_direct_request(self):
        d=source('ex:A a h:Holon . ex:B a h:Holon ; h:contentGraph ex:One, ex:Two . ex:A { ex:A ex:value "a" . }')
        with self.assertRaises(ContextError):DatasetContext(d).resolve(EX.A,"direct")

    def test_mixed_blank_node_holon_may_have_membership_content_only(self):
        from rdflib import BNode
        from run_suite import term_json
        b=BNode("b"); d=Dataset(); d.default_context.add((b,RDF.type,H.Holon))
        base=[term_json(EX.s),term_json(EX.p),term_json(EX.o)]
        rows=[base,[{"type":"bnode","value":"r1"},term_json(URIRef(str(RDF)+"reifies")),{"type":"triple","value":dict(zip(["subject","predicate","object"],base))}],
              [{"type":"bnode","value":"r1"},term_json(H.inHolon),{"type":"bnode","value":"b"}]]
        mixed=MixedContext(d,rows)
        self.assertEqual(set(mixed.resolve(b,"direct")),{(EX.s,EX.p,EX.o)})
        with self.assertRaises(ContextError):DatasetContext(d).resolve(b,"direct")  # the dataset profile alone still requires a mapping

    def test_undeclared_descendant_is_rejected(self):
        c=DatasetContext(source('ex:A a h:Holon . ex:Missing h:parentHolon ex:A .'))
        c.resolve(EX.A,"direct")
        with self.assertRaises(ContextError):c.resolve(EX.A,"aggregated")

    def test_unknown_and_registered_empty_are_distinct(self):
        c=DatasetContext(source('ex:A a h:Holon .'))
        self.assertEqual(len(c.resolve(EX.A,"direct")),0)
        with self.assertRaises(ContextError):c.resolve(EX.Missing,"direct")

    def test_mode_specific_invalid_hierarchy(self):
        c=DatasetContext(source('ex:A a h:Holon . ex:B a h:Holon ; h:parentHolon ex:B .'))
        c.resolve(EX.A,"direct")
        with self.assertRaises(ContextError):c.resolve(EX.A,"aggregated")

    def test_unrelated_imports_do_not_fail_visible_scope(self):
        c=DatasetContext(source('ex:A a h:Holon . ex:B a h:Holon ; h:imports ex:Missing .'))
        c.resolve(EX.A,"visible")
        with self.assertRaises(ContextError):c.resolve(EX.B,"visible")

    def test_missing_and_nonterm_reification_rejected(self):
        meta=Graph().parse(data=PREFIX+'ex:H a h:Holon .',format="turtle")
        member=[{"type":"uri","value":str(EX.r)},{"type":"uri","value":str(H.inHolon)},{"type":"uri","value":str(EX.H)}]
        with self.assertRaises(ContextError):ReifierContext([member],meta)
        malformed=[member[0],{"type":"uri","value":str(URIRef(str(RDF)+"reifies"))},{"type":"uri","value":str(EX.notATriple)}]
        with self.assertRaises(ContextError):ReifierContext([member,malformed],meta)

    def test_missing_shapes_graph_is_an_error_and_imports_are_not_inherited(self):
        m=Graph().parse(data=PREFIX+'ex:State h:importsShapes ex:StateShapes . ex:City h:parentHolon ex:State ; h:importsShapes ex:CityShapes .',format="turtle")
        shapes=source('ex:CityShapes { ex:S a <http://www.w3.org/ns/shacl#NodeShape> . }')
        self.assertEqual(len(effective_shapes(m,shapes,EX.City)),1)
        self.assertEqual(len(effective_shapes(m,shapes,EX.Neighborhood)),0)  # nothing declared, nothing inherited
        with self.assertRaises(ContextError) as missing:effective_shapes(m,shapes,EX.State)
        self.assertEqual(str(missing.exception),"missing-shapes-graph")

    def test_shapes_union_can_be_a_definition_failure(self):
        try:from pyshacl import validate
        except ImportError:self.skipTest("pyshacl unavailable")
        p='@prefix ex: <https://example.org/> . @prefix sh: <http://www.w3.org/ns/shacl#> . '
        a=Graph().parse(data=p+'ex:P a sh:PropertyShape ; sh:path ex:value ; sh:minCount 1 .',format="turtle")
        b=Graph().parse(data=p+'ex:P a sh:PropertyShape ; sh:path ex:value ; sh:minCount 2 .',format="turtle")
        validate(Graph(),shacl_graph=a,meta_shacl=True);validate(Graph(),shacl_graph=b,meta_shacl=True)
        from pyshacl.errors import ReportableRuntimeError
        import logging
        previous=logging.root.manager.disable
        try:
            logging.disable(logging.CRITICAL)
            with self.assertRaises(ReportableRuntimeError):validate(Graph(),shacl_graph=a+b,meta_shacl=True)
        finally:logging.disable(previous)

    def test_mapping_shape_rejects_conflicts(self):
        try:from pyshacl import validate
        except ImportError:self.skipTest("pyshacl unavailable")
        ontology=Graph().parse(ROOT/'rdfh.ttl')
        metadata=Graph().parse(data=PREFIX+'ex:H h:contentGraph ex:One, ex:Two .',format="turtle")
        self.assertFalse(validate(metadata,shacl_graph=ontology,use_shapes=[H.ContentGraphMappingShape])[0])

    def test_membership_shape_requires_reification(self):
        try:from pyshacl import validate
        except ImportError:self.skipTest("pyshacl unavailable")
        data=Graph().parse(data=PREFIX+'ex:r h:inHolon ex:H .',format="turtle")
        self.assertFalse(validate(data,shacl_graph=Graph().parse(ROOT/'rdfh.ttl'),use_shapes=[H.ReifierMembershipShape])[0])

    def test_legacy_complete_type_only_registers(self):
        from rdflib.namespace import OWL
        c=DatasetContext(source('ex:H a h:CompleteHolon .'))
        self.assertEqual(c.registry,{EX.H})
        self.assertEqual(len(c.resolve(EX.H,"direct")),0)
        ontology=Graph().parse(ROOT/'rdfh.ttl')
        self.assertTrue(ontology.value(H.CompleteHolon,OWL.deprecated).toPython())

    def test_empty_turtle_block_preserves_registration(self):
        data=json.loads((ROOT/'tests/turtle-h/cases/empty.terms.json').read_text(encoding="utf-8"))
        self.assertEqual(len(data["graph"]),1)
        self.assertEqual(data["graph"],data["metadataGraph"])
        self.assertEqual(data["graph"][0][2]["value"],str(H.Holon))

    def test_turtle_generated_triples_are_filed_once(self):
        for name,n in [("collection",5),("property-list",2),("annotation",3)]:
            data=json.loads((ROOT/f'tests/turtle-h/cases/{name}.terms.json').read_text(encoding="utf-8"))
            members=[row for row in data["graph"] if row[1].get("value")==str(H.inHolon)]
            self.assertEqual(len(members),n)
            self.assertEqual(len(data["graph"]),n*3+1)

    def test_parser_preserves_tabs_comments_and_literal_tokens(self):
        query='PREFIX ex: <https://example.org/> SELECT\t?x\nFROM\tHOLON\tex:City\tSCOPE\tDIRECT\nWHERE { BIND("FROM HOLON ex:Other" AS ?x) } # FROM HOLON ex:Fake'
        holon,mode,lowered,_=parse_source(query)
        self.assertEqual((holon,mode),(EX.City,"direct"))
        self.assertIn('"FROM HOLON ex:Other"',lowered)
        self.assertIn('# FROM HOLON ex:Fake',lowered)
        self.assertNotIn('SCOPE',lowered)

if __name__=='__main__':unittest.main()
