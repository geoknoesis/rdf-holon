# RDF-H: A Holonic Modeling Pattern for RDF

This repository contains a draft specification for a proposed holonic extension to the Resource Description Framework (RDF), referred to as **RDF-H**. This document is a proposal by **Geoknoesis LLC** and is intended to gather community feedback for potential future standardization by the W3C.

**Current version: 0.7** (community draft) — see the [Change Log](https://geoknoesis.github.io/rdf-holon/#changelog) for what changed from 0.6.

> ⚠️ **w3id.org redirect not yet configured.** The vocabulary IRI `https://w3id.org/rdf-h#` referenced normatively throughout the spec depends on a redirect entry in [perma-id/w3id.org](https://github.com/perma-id/w3id.org) that has not yet been filed. Until that PR is merged, the vocabulary IRI does not resolve on the open web. This is tracked as [Open Issue 2](https://geoknoesis.github.io/rdf-holon/#issue-w3id-redirect) in the specification.

## Abstract

The increasing need to model complex, compositional systems (digital twins, cyber-physical systems, fine-grained access control policies) highlights a key limitation in existing graph data models. While RDF is excellent for linking data, it lacks a native, semantically grounded way to gather the relationships that describe a "whole" and to treat that whole as a part of larger wholes.

This specification proposes the **holon** as a first-class primitive in RDF. Each holon has a **content graph** `CG(H)` — the set of triples filed in it — which is a *view* over the single asserted graph (an *additive* semantics: every filed triple is also globally true). The content-graph model is defined abstractly and realized by two interoperable serialization **profiles** — a *reifier profile* (RDF 1.2 `rdf:reifies` + `h:inHolon`, single graph, per-occurrence metadata) and a *named-graph profile* (RDF datasets, `GRAPH`-queryable on today's tooling). Grounded in formal mereology and a content/composition coherence discipline, RDF-H aims to enable a faithful, powerful representation of complex, interconnected systems while remaining a conservative extension of RDF 1.2.

## Key Features

* **Holon = content graph.** A holon `h:Holon` has a content graph `CG(H)` — the triples filed in it — that is a queryable *view* over the asserted graph, governed by the **additive invariant** `CG(H) ⊆ G`. `h:CompleteHolon` marks a holon whose content graph is complete (a local completeness contract enabling integrity checks scoped to the holon); `h:contentGraph` names the content graph in the named-graph profile.
* **Dual serialization profiles.** The same `CG(H)` is realized either with RDF 1.2 reifiers via `h:inHolon` (single graph, per-occurrence metadata) or as a named graph in a dataset (`GRAPH`-queryable, inexpensive), with a stated equivalence and translation between the two.
* **Mereological hierarchy.** A formally grounded part-whole hierarchy: a single transitive top-level `h:partOf`, with non-transitive asymmetric/irreflexive sub-properties `h:componentOf` and `h:memberOf` (structural parthood and aggregate membership), and transitive sub-properties `h:substanceOf` and `h:portionOf` (material composition and continuous-whole segmentation). The vocabulary stays within OWL 2 DL; full-hierarchy acyclicity is enforced by SHACL.
* **Coherence discipline.** A holon's content graph should be *about* the holon: a part-of relation filed in `H` should describe `H`'s own composition, and any relation filed in `H` should touch `H` or one of its parts. These are advisory recommendations, surfaced by SHACL warnings.
* **Turtle-H.** A small syntactic sugar over Turtle 1.2 introducing the `@holon` directive (reifier profile), which lets authors write a holon's constituent triples once and have a Turtle-H-aware parser generate the corresponding `h:inHolon` annotations automatically.
* **SHACL shapes.** Five ready-to-run shapes using standard SPARQL-based constraints that carry their own targets, so loading `rdfh.ttl` as the shapes graph validates a data graph directly: `h:AcyclicPartShape` and `h:AssertedBaseTripleShape` (normative), and `h:HolonIntegrityShape`, `h:MereologicalCoherenceShape`, `h:ContextualCoherenceShape` (advisory, `sh:Warning`).
* **Standard SPARQL.** Holonic graphs are queried with plain SPARQL 1.1 — `GRAPH` (named-graph profile) or SPARQL 1.2 reified-triple patterns (reifier profile). No SPARQL extension is required.

## Repository Contents

| File | Purpose |
|---|---|
| [`index.html`](./index.html) | The specification document (rendered by ReSpec). |
| [`rdfh.css`](./rdfh.css) | Readability stylesheet for the specification (presentation only). |
| [`rdfh.ttl`](./rdfh.ttl) | The RDF-H vocabulary in Turtle, including OWL axioms and the SHACL shapes. |
| [`LICENSE`](./LICENSE) | Apache License, Version 2.0. |
| [`README.md`](./README.md) | This file. |

## Modularity

The specification is structured in three logically separable layers:

1. The **core vocabulary and content-graph model** (`h:Holon`, `h:inHolon`, `h:contentGraph`, `h:CompleteHolon`) — each holon's content graph and its reifier/named-graph serialization profiles.
2. The **mereology** (the `h:partOf` hierarchy).
3. **Turtle-H** (the `@holon` surface-syntax sugar).

For v0.7 the three layers remain bundled in this single document and share the `https://w3id.org/rdf-h#` namespace. Whether to extract layers (2) and (3) into companion specifications, and whether to split namespaces pre-emptively, are tracked as [Open Issues 1, 6, and 7](https://geoknoesis.github.io/rdf-holon/#open-issues).

## Viewing the Specification

The latest version of the draft specification can be viewed online, rendered directly from this repository via GitHub Pages:

**[https://geoknoesis.github.io/rdf-holon/](https://geoknoesis.github.io/rdf-holon/)**

## Contributing

Feedback and contributions are welcome. Please open an issue to discuss the proposal, suggest changes, or report errors. The specification's [Open Issues appendix](https://geoknoesis.github.io/rdf-holon/#open-issues) lists the design questions on which community input is most actively sought (mereology extraction, Turtle-H venue, namespace organization, closed-world holon contents, and the empty-holon question, among others).

## License

This repository — including the specification document, the RDF-H vocabulary (`rdfh.ttl`), and all examples — is published under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0). See [`LICENSE`](./LICENSE) for the full text.
