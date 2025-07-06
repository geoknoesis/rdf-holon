# RDF 2.0 Holon Extensions: A Proposal

This repository contains a draft specification for a proposed holonic extension to the Resource Description Framework (RDF), referred to as **RDF 2.0**. This document is a proposal by **Geoknoesis LLC** and is intended to gather community feedback for potential future standardization by the W3C.

## Abstract

The Spatial Web and the increasing need to model complex, compositional systems (like digital twins, supply chains, and cyber-physical systems) highlight a key limitation in existing graph data models. While RDF is excellent for linking data, it lacks a native primitive for structural containment—for representing "wholes" that are composed of "parts."

This specification proposes the **holon** as a new first-class primitive in RDF. A holon is a resource that is simultaneously a whole in itself and a part of a larger whole. By grounding this concept in formal mereology and providing a conservative, backward-compatible extension to RDF 1.2, this proposal aims to enable a more faithful and powerful representation of our complex, interconnected world.

## Key Features

* **Holon Primitive:** A new resource type, `h:Holon`, for defining compositional boundaries.
* **Primitive Containment:** A native, acyclic, and transitive containment relation (`⊂`) built into the data model.
* **Turtle-H:** A simple extension to the Turtle syntax with an `@holon` block for defining contents.
* **SPARQL-H:** A corresponding extension to SPARQL with a `CONTAINS` property path for intuitive traversal of holonic structures.

## Viewing the Specification

The latest version of the draft specification can be viewed online, rendered directly from this repository via GitHub Pages:

**[https://geoknoesis.github.io/rdf-holon-spec/](https://geoknoesis.github.io/rdf-holon-spec/)**


## Contributing

Feedback and contributions are welcome! Please feel free to open an issue to discuss the proposal, suggest changes, or report errors.

---
