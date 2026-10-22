"""Checks the suite harness, not either language implementation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import run_suite as suite


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = suite.load_cases(Path(__file__).with_name("manifest.ttl"))

    def get_case(self, suffix):
        return next(c for c in self.cases if c["id"].endswith("#" + suffix))

    def command(self, response):
        return [sys.executable, "-c", "import json,sys; json.load(sys.stdin); print(" + repr(json.dumps(response)) + ")"]

    def test_manifest_counts(self):
        self.assertGreaterEqual(len(self.cases), 91)
        for p in [suite.HERE / "manifest.ttl", suite.HERE / "turtle-h/manifest.ttl", suite.HERE / "sparql-h/manifest.ttl", suite.HERE / "rdf-h/manifest.ttl"]:
            self.assertNotIn("file:", p.read_text(encoding="utf-8"))

    def test_serializer_output_is_reparsed_and_compared(self):
        case = self.get_case("basic-serialize")
        request = suite.request_for(case)
        self.assertEqual(request["operation"], "serialize")
        self.assertNotIn("text", request["input"])
        expected = suite.expected_result(case)
        # A fake adapter: any serialize request returns text, any evaluate request returns the parsed graphs.
        good = {"status": "ok", "result": {"text": "irrelevant", **expected}}
        self.assertEqual(suite.execute(case, self.command(good), 10)[0], "PASS")
        wrong = copy.deepcopy(good)
        wrong["result"]["graph"] = wrong["result"]["graph"][1:]
        self.assertEqual(suite.execute(case, self.command(wrong), 10)[0], "FAIL")
        no_text = {"status": "ok", "result": expected}
        self.assertEqual(suite.execute(case, self.command(no_text), 10)[0], "FAIL")

    def test_missing_adapter_is_untested(self):
        self.assertEqual(suite.execute(self.cases[0], None, 1)[0], "SKIP")

    def test_expected_condition_is_required_and_checked(self):
        case = self.get_case("parent-cycle")
        good = {"status": "rejected", "category": "resolution", "condition": "parent-cycle"}
        self.assertEqual(suite.execute(case, self.command(good), 10)[0], "PASS")
        for condition in [None, "unknown-holon"]:
            wrong = dict(good, condition=condition)
            self.assertEqual(suite.execute(case, self.command(wrong), 10)[0], "FAIL")

    def test_negative_serialization_requires_representability_error(self):
        case = self.get_case("inert-management-serialize-error")
        good = {"status": "rejected", "category": "unrepresentable-context", "condition": "unrepresentable-context"}
        self.assertEqual(suite.execute(case, self.command(good), 10)[0], "PASS")
        wrong = dict(good, category="syntax")
        self.assertEqual(suite.execute(case, self.command(wrong), 10)[0], "FAIL")

    def test_adapter_request_does_not_leak_oracle(self):
        request = suite.request_for(self.get_case("visible-eval"))
        self.assertNotIn("scope", request)
        self.assertNotIn("lowered", request)
        self.assertNotIn("expected", json.dumps(request))

    def test_conversion_compares_content_and_metadata(self):
        case = self.get_case("convert-dataset-to-reifier")
        request = suite.request_for(case)
        self.assertEqual(request["targetRepresentation"], "reifier")
        self.assertNotIn("input", request)
        expected = json.loads(case["terms"].read_text(encoding="utf-8"))
        def output(content_rows):
            rows = []
            for i, (holon, triple) in enumerate(content_rows):
                r = {"type": "bnode", "value": f"r{i}"}
                rows += [triple, [r, {"type": "uri", "value": str(suite.RDF_REIFIES)}, suite.triple_term(triple)],
                         [r, {"type": "uri", "value": str(suite.H.inHolon)}, holon]]
            return {"status": "ok", "result": {"representation": "reifier", "graph": rows, "metadataGraph": expected["metadataGraph"]}}
        good = [(h["holon"], t) for h in expected["holons"] for t in h["content"]]
        self.assertEqual(suite.execute(case, self.command(output(good)), 10)[0], "PASS")
        self.assertEqual(suite.execute(case, self.command(output(good[1:])), 10)[0], "FAIL")
        wrong_holon = [(good[1][0], good[0][1])] + good[1:]
        self.assertEqual(suite.execute(case, self.command(output(wrong_holon)), 10)[0], "FAIL")

    def test_conversion_rejects_invalid_membership_even_without_extra_content(self):
        case = self.get_case("convert-dataset-to-reifier")
        expected = json.loads(case["terms"].read_text(encoding="utf-8"))
        result = {"representation": "reifier", "metadataGraph": expected["metadataGraph"], "graph": []}
        for i, holon in enumerate(expected["holons"]):
            for j, triple in enumerate(holon["content"]):
                r = {"type": "bnode", "value": f"r{i}-{j}"}
                result["graph"] += [triple, [r, {"type": "uri", "value": str(suite.RDF_REIFIES)}, suite.triple_term(triple)],
                                    [r, {"type": "uri", "value": str(suite.H.inHolon)}, holon["holon"]]]
        suite.compare_conversion(result, expected)
        result["graph"].append([{"type": "bnode", "value": "inert-in-source"},
                                {"type": "uri", "value": str(suite.H.inHolon)}, expected["holons"][0]["holon"]])
        with self.assertRaisesRegex(ValueError, "no reification"):
            suite.compare_conversion(result, expected)

    def test_reifier_request_declares_representation_and_metadata(self):
        request = suite.request_for(self.get_case("reifier-visible"))
        self.assertEqual(request["representation"], "reifier")
        self.assertIn("terms", request["sourceGraph"])
        self.assertIn("metadataContext", request)
        self.assertNotIn("sourceDataset", request)
        self.assertNotIn("expected", json.dumps(request))
        self.assertEqual(suite.request_for(self.get_case("visible-eval"))["representation"], "dataset")

    def test_blank_node_renaming_is_accepted(self):
        case = self.get_case("blank-holon-eval")
        expected = suite.expected_result(case)
        actual = copy.deepcopy(expected)
        def rename(item):
            if isinstance(item, dict):
                if item.get("type") == "bnode": item["value"] = "renamed-" + item["value"]
                else:
                    for value in item.values(): rename(value)
            elif isinstance(item, list):
                for value in item: rename(value)
        rename(actual)
        suite.compare_results(actual, expected)

    def test_missing_base_statement_fails(self):
        expected = suite.expected_result(self.get_case("basic-eval"))
        actual = {"graph": expected["graph"][1:]}
        with self.assertRaises(ValueError): suite.compare_results(actual, expected)

    def test_collapsed_occurrences_fail(self):
        expected = suite.expected_result(self.get_case("repeat-occurrence-eval"))
        actual = json.loads(json.dumps(expected).replace('"r2"', '"r1"'))
        with self.assertRaises(ValueError): suite.compare_results(actual, expected)

    def test_changed_blank_node_sharing_fails(self):
        expected = suite.expected_result(self.get_case("blank-holon-eval"))
        actual = copy.deepcopy(expected)
        # Disconnect the subject inside the reified term from the asserted subject.
        actual["graph"][1][2]["value"]["subject"]["value"] = "different-subject"
        with self.assertRaises(ValueError): suite.compare_results(actual, expected)

    def test_graph_set_and_string_literal_equivalence(self):
        expected = suite.expected_result(self.get_case("outside-content-eval"))
        actual = copy.deepcopy(expected)
        for row in actual["graph"]:
            if row[2].get("type") == "literal":
                row[2]["datatype"] = "http://www.w3.org/2001/XMLSchema#string"
        actual["graph"].extend(copy.deepcopy(actual["graph"]))
        suite.compare_results(actual, expected)

    def test_directional_literal_direction_is_preserved(self):
        expected = suite.expected_result(self.get_case("directional-literal-eval"))
        actual = copy.deepcopy(expected)
        def change(value):
            if isinstance(value,dict):
                if "direction" in value: value["direction"] = "rtl"
                for child in value.values(): change(child)
            elif isinstance(value,list):
                for child in value: change(child)
        change(actual)
        with self.assertRaises(ValueError): suite.compare_results(actual,expected)

    def test_metadata_and_data_share_blank_node_identity(self):
        expected = suite.expected_result(self.get_case("blank-holon-eval"))
        actual = copy.deepcopy(expected)
        actual["metadataGraph"][0][0]["value"] = "wrong-holon"
        with self.assertRaises(ValueError): suite.compare_results(actual,expected)

    def test_result_multiplicity_is_preserved(self):
        row = {"x": {"type": "literal", "value": "same"}}
        expected = {"head": {"vars": ["x"]}, "results": {"bindings": [row, row]}}
        actual = {"head": {"vars": ["x"]}, "results": {"bindings": [row]}}
        with self.assertRaises(ValueError): suite.compare_results(actual, expected)

    def test_order_is_checked_only_when_declared(self):
        expected = suite.expected_result(self.get_case("aggregated-eval"))
        actual = copy.deepcopy(expected)
        actual["results"]["bindings"].reverse()
        suite.compare_results(actual, expected, ordered=False)
        with self.assertRaises(ValueError): suite.compare_results(actual, expected, ordered=True)

    def test_rejection_requires_structured_syntax_error(self):
        case = self.get_case("negative-missing-id")
        self.assertEqual(suite.execute(case, self.command({"status":"rejected", "category":"syntax"}), 3)[0], "PASS")
        self.assertEqual(suite.execute(case, self.command({"status":"rejected", "category":"execution"}), 3)[0], "FAIL")

    def test_crash_and_bad_json_are_not_negative_passes(self):
        case = self.get_case("negative-missing-id")
        for command in [[sys.executable,"-c","raise SystemExit(2)"], [sys.executable,"-c","print('not JSON')"], [sys.executable,"-c","print('[]')"]]:
            self.assertEqual(suite.execute(case, command, 3)[0], "FAIL")

    def test_timeout_is_failure(self):
        command = [sys.executable,"-c","import time; time.sleep(2)"]
        self.assertEqual(suite.execute(self.get_case("negative-missing-id"), command, 0.05)[0], "FAIL")

    def test_unsupported_is_skip(self):
        self.assertEqual(suite.execute(self.cases[0], self.command({"status":"unsupported"}), 3)[0], "SKIP")

    def test_graph_evaluation_adapter(self):
        case = self.get_case("basic-eval")
        response = {"status":"ok", "result":suite.expected_result(case)}
        self.assertEqual(suite.execute(case, self.command(response), 3)[0], "PASS")

    def test_earl_untested_is_not_passed(self):
        from rdflib import Graph, URIRef
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "earl.ttl"
            suite.write_earl(path, [{"id":self.cases[0]["id"],"status":"SKIP","message":"No adapter"}], "urn:test:implementation")
            report = Graph().parse(path)
            self.assertTrue(list(report.triples((None,suite.EARL.outcome,suite.EARL.untested))))
            self.assertFalse(list(report.triples((None,suite.EARL.outcome,suite.EARL.passed))))


if __name__ == "__main__":
    unittest.main()
