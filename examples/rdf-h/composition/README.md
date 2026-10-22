# Composition example

`scopes.trig` distinguishes City query scopes:

| Scope | Values |
|---|---|
| Direct named-graph query | city |
| Aggregated | city, district, neighborhood |
| Visible | city, district, neighborhood, metro |

Ancestors, ancestors' and descendants' imports, recursive imports, and imported targets'
descendants are excluded. An explicit City import can add State's direct content.

`shapes.trig` is a separate validation dataset. City explicitly imports CityShapes;
StateShapes is not inherited. Combining both shapes graphs rejects the city fixture.

Run `python tests/rdf-h/check_composition.py` to check these results.

See [queries/](./queries/) for standard SPARQL recipes for all three scopes.
