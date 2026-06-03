# RDF-H: A Holonic Modeling Pattern for RDF

This repository contains a draft specification for a proposed holonic extension to the Resource Description Framework (RDF), referred to as **RDF-H**. This document is a proposal by **Geoknoesis LLC** and is intended to gather community feedback for potential future standardization by the W3C.

**Current version: 0.6** (community draft, in progress) — see the [Change Log](https://geoknoesis.github.io/rdf-holon/#changelog) for what changed from 0.5.

> ⚠️ **w3id.org redirect not yet configured.** The vocabulary IRI `https://w3id.org/rdf-h#` referenced normatively throughout the spec depends on a redirect entry in [perma-id/w3id.org](https://github.com/perma-id/w3id.org) that has not yet been filed. Until that PR is merged, the vocabulary IRI does not resolve on the open web. This is tracked as [Open Issue 2](https://geoknoesis.github.io/rdf-holon/#issue-w3id-redirect) in the specification.

## Abstract

The increasing need to model complex, compositional systems (digital twins, cyber-physical systems, fine-grained access control policies) highlights a key limitation in existing graph data models. While RDF is excellent for linking data, it lacks a native primitive for structural containment — for representing "wholes" that are composed of "parts."

This specification proposes the **holon** as a new first-class primitive in RDF. A holon is a resource that is simultaneously a whole in itself and a part of a larger whole. By grounding this concept in formal mereology and providing a conservative, backward-compatible extension to RDF 1.2, this proposal aims to enable a more faithful and powerful representation of complex, interconnected systems.

## Key Features

* **Holon primitive.** A new resource type, `h:Holon`, for defining compositional boundaries.
* **Holonic context.** The `h:inHolon` property links a triple-occurrence's *reifier* (in the RDF 1.2 sense — an IRI or blank node related to a triple term via `rdf:reifies`) to the holon that contains it, without leaving the single, unified RDF graph.
* **Mereological hierarchy.** A formally grounded part-whole hierarchy: a single transitive top-level `h:partOf`, with non-transitive asymmetric/irreflexive sub-properties `h:componentOf` and `h:memberOf` (structural parthood and aggregate membership), and transitive sub-properties `h:substanceOf` and `h:portionOf` (material composition and continuous-whole segmentation). The vocabulary stays within OWL 2 DL; full-hierarchy acyclicity is enforced by SHACL.
* **Turtle-H.** A small syntactic sugar over Turtle 1.2 introducing the `@holon` directive, which lets authors write a holon's constituent triples once and have a Turtle-H-aware parser generate the corresponding `h:inHolon` annotations automatically.
* **SHACL shapes.** Three ready-to-run shapes — `h:AcyclicPartShape`, `h:AssertedBaseTripleShape`, and `h:HolonIntegrityShape` — for validating holonic graphs. They use standard SPARQL-based constraints and carry their own targets, so loading `rdfh.ttl` as the shapes graph validates a data graph directly. The first two are normative (operationalizing the conformance criteria for an RDF-H graph); the third is a portability check (`sh:Warning`).
* **Standard SPARQL.** Holonic graphs are queried with plain SPARQL 1.1, together with the SPARQL 1.2 reified-triple patterns and triple-term syntax that accompany the RDF 1.2 reifier model. No SPARQL extension is required.

## Repository Contents

| File | Purpose |
|---|---|
| [`index.html`](./index.html) | The specification document (rendered by ReSpec). |
| [`rdfh.ttl`](./rdfh.ttl) | The RDF-H vocabulary in Turtle, including OWL axioms and the SHACL constraint components. |
| [`LICENSE`](./LICENSE) | Apache License, Version 2.0. |
| [`README.md`](./README.md) | This file. |

## Modularity

The specification is structured in three logically separable layers:

1. The **core vocabulary** (`h:Holon`, `h:inHolon`).
2. The **mereology** (the `h:partOf` hierarchy).
3. **Turtle-H** (the `@holon` surface-syntax sugar).

For v0.6 the three layers remain bundled in this single document and share the `https://w3id.org/rdf-h#` namespace. Whether to extract layers (2) and (3) into companion specifications, and whether to split namespaces pre-emptively, are tracked as [Open Issues 1, 6, and 7](https://geoknoesis.github.io/rdf-holon/#open-issues).

## Viewing the Specification

The latest version of the draft specification can be viewed online, rendered directly from this repository via GitHub Pages:

**[https://geoknoesis.github.io/rdf-holon/](https://geoknoesis.github.io/rdf-holon/)**

## Contributing

Feedback and contributions are welcome. Please open an issue to discuss the proposal, suggest changes, or report errors. The specification's [Open Issues appendix](https://geoknoesis.github.io/rdf-holon/#open-issues) lists the design questions on which community input is most actively sought (mereology extraction, Turtle-H venue, namespace organization, closed-world holon contents, and the empty-holon question, among others).

## License

This repository — including the specification document, the RDF-H vocabulary (`rdfh.ttl`), and all examples — is published under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0). See [`LICENSE`](./LICENSE) for the full text.
