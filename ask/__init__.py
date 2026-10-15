"""Ask the graph (slice 8): plain question -> typed query (DSL) -> rows with their claims.

Modules: normalise (name keys), index (the compact index built from build/graph.ttl),
dsl (parser, validator, executor, plain-language rendering), translate (question -> DSL,
refusal classifier), present (answer -> HTML), build_ask (writes site/dist/ask/).
No model is called anywhere in this package. See ask/DSL.md.
"""
