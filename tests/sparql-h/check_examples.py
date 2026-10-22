"""Compatibility entry point: semantic smoke checks from the authoritative RDF manifest."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_suite import load_cases, semantic_smoke
cases = load_cases(Path(__file__).with_name("manifest.ttl"))
print(f"PASS: {semantic_smoke(cases)} expected standard-query translations on resolved scope datasets")
print("No language parser tested; use run_suite.py with an implementation adapter for conformance")
