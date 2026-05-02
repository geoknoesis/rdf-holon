# RDF-H: Holon Extensions for RDF

This repository contains a draft specification for a proposed holonic extension to the Resource Description Framework (RDF), referred to as **RDF-H**. This document is a proposal by **Geoknoesis LLC** and is intended to gather community feedback for potential future standardization by the W3C.

**Current version: 0.5** (community draft) — see the [Change Log](https://geoknoesis.github.io/rdf-holon/#changelog) for what changed from 0.4.

> ⚠️ **w3id.org redirect not yet configured.** The vocabulary IRI `https://w3id.org/rdf-h#` referenced normatively throughout the spec depends on a redirect entry in [perma-id/w3id.org](https://github.com/perma-id/w3id.org) that has not yet been filed. Until that PR is merged, the vocabulary IRI does not resolve on the open web. This is tracked as [Open Issue 2](https://geoknoesis.github.io/rdf-holon/#issue-w3id-redirect) in the specification.

## Abstract

The increasing need to model complex, compositional systems (like digital twins, supply chains, and cyber-physical systems) highlight a key limitation in existing graph data models. While RDF is excellent for linking data, it lacks a native primitive for structural containment—for representing "wholes" that are composed of "parts."

This specification proposes the **holon** as a new first-class primitive in RDF. A holon is a resource that is simultaneously a whole in itself and a part of a larger whole. By grounding this concept in formal mereology and providing a conservative, backward-compatible extension to RDF 1.2, this proposal aims to enable a more faithful and powerful representation of our complex, interconnected world.

## Key Features

* **Holon Primitive:** A new resource type, `h:Holon`, for defining compositional boundaries.
* **Mereological Hierarchy:** A formally grounded part-whole hierarchy with two top-level properties — a transitive `h:partOf` (for closure-style queries) and a non-transitive, asymmetric, irreflexive `h:directlyPartOf` (for the immediate-part relation) — together with sub-properties for components, members, substances, and portions. Acyclicity is enforced jointly by OWL DL axioms (on the strict properties) and by a SHACL constraint component (on the transitive ones).
* **Holonic Context:** The `h:inHolon` property links a triple-occurrence's *reifier* (in the RDF 1.2 sense — an IRI or blank node related to a triple term via `rdf:reifies`) to the holon that contains it, without leaving the single, unified RDF graph.
* **Turtle-H:** A small syntactic sugar over Turtle 1.2 introducing the `@holon` directive, which lets authors write a holon's constituent triples once and have a Turtle-H-aware parser generate the corresponding `h:inHolon` annotations automatically.
* **SHACL Constraint Components:** Two reusable SHACL components — `h:AcyclicPartConstraintComponent` and `h:HolonIntegrityConstraintComponent` — for validating holonic graphs.
* **Standard SPARQL:** Holonic graphs are queried with plain SPARQL 1.1, together with the SPARQL 1.2 reified-triple patterns and triple-term syntax that accompany the RDF 1.2 reifier model. No SPARQL extension is required.

## Viewing the Specification

The latest version of the draft specification can be viewed online, rendered directly from this repository via GitHub Pages:

**[https://geoknoesis.github.io/rdf-holon/](https://geoknoesis.github.io/rdf-holon/)**

## Contributing

Feedback and contributions are welcome! Please feel free to open an issue to discuss the proposal, suggest changes, or report errors. The specification's [Open Issues appendix](https://geoknoesis.github.io/rdf-holon/#open-issues) lists the design questions on which community input is most actively sought.

## License

This repository — including the specification document, the RDF-H vocabulary (`rdfh.ttl`), and all examples — is published under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0). See [`LICENSE`](LICENSE) for the full text.
