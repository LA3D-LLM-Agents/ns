"""Offline dataset profile contract tests; fixtures are synthetic, not live observations."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from owlrl import DeductiveClosure, OWLRL_Semantics
from pyshacl import validate
from rdflib import DCAT, DCTERMS, RDF, Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "dataset_adapter", ROOT / "examples/datasets/adapter.py"
)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
E = adapter.ECO
registry = json.loads((ROOT / "examples/datasets/registry.json").read_text())
resources = json.loads((ROOT / "examples/datasets/resources.json").read_text())
Draft202012Validator.check_schema(adapter.SCHEMA)
ontology = Graph().parse(ROOT / "versions/0.3.0/eco.ttl")
shapes = Graph().parse(ROOT / "versions/0.3.0/eco-discovery-shapes.ttl")
shapes.parse(adapter.PROFILE / "shapes.ttl")
passed = []
manifest = json.loads((adapter.PROFILE / "manifest.json").read_text())
for name, digest in manifest["artifacts"].items():
    assert hashlib.sha256((adapter.PROFILE / name).read_bytes()).hexdigest() == digest
for name, digest in manifest["dependencies"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
passed.append("pinned profile and eco digests")


def valid_json(candidate, expected, name):
    try:
        adapter.validate_registry(candidate, resources)
        success = True
    except (ValueError, ValidationError):
        success = False
    assert success == expected, name
    passed.append(name)


def check_graph(g, expected, name):
    ok, _, report = validate(
        g,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference="rdfs",
        do_owl_imports=False,
    )
    assert ok == expected, name + "\n" + report
    passed.append(name)


valid_json(registry, True, "two datasets sharing service")
valid_json({"profile_version": "0.1.0", "datasets": []}, True, "empty registry")
for field, value in [("profile_version", "9.0")]:
    bad = copy.deepcopy(registry)
    bad[field] = value
    valid_json(bad, False, "unsupported version")
mutations = [
    ("unknown field", lambda d: d.update(secret="no")),
    (
        "credential-bearing IRI",
        lambda d: d.update(iri="https://user:pass@example.org/kg"),
    ),
    ("blank label", lambda d: d.update(label=" ")),
    ("missing provenance", lambda d: d.pop("provenance")),
    (
        "invalid observation time",
        lambda d: d["provenance"]["observations"][0].update(observed_at="yesterday"),
    ),
    (
        "unknown resource",
        lambda d: d["access_bindings"][0].update(resource_id="unknown"),
    ),
    (
        "unapproved tool",
        lambda d: d["access_bindings"][0]["version_inspection"].update(
            tool_name="delete"
        ),
    ),
    (
        "nested arguments",
        lambda d: d["access_bindings"][0]["semantic_inspections"][0].update(
            arguments={"x": {"y": 1}}
        ),
    ),
    (
        "missing fixed arguments",
        lambda d: d["access_bindings"][0]["semantic_inspections"][0].pop("arguments"),
    ),
    (
        "duplicate bindings",
        lambda d: d["access_bindings"].append(copy.deepcopy(d["access_bindings"][0])),
    ),
    ("unqualified version", lambda d: d.update(source_version={"value": "v1"})),
    (
        "unqualified loaded time",
        lambda d: d.update(loaded_at={"value": "2026-01-01T00:00:00Z"}),
    ),
]
for name, mutate in mutations:
    bad = copy.deepcopy(registry)
    mutate(bad["datasets"][0])
    valid_json(bad, False, name)
for field in ["id", "iri", "named_graph"]:
    bad = copy.deepcopy(registry)
    bad["datasets"][1][field] = bad["datasets"][0][field]
    valid_json(bad, False, "conflicting " + field)
versioned = copy.deepcopy(registry)
d = versioned["datasets"][0]
d["source_version"] = {
    "value": "fixture-v1",
    "observation": copy.deepcopy(d["provenance"]["observations"][0]),
}
d["loaded_at"] = {
    "value": "2026-01-01T00:00:00Z",
    "observation": copy.deepcopy(d["provenance"]["observations"][0]),
}
valid_json(versioned, True, "qualified optional version and load time")

graph = adapter.map_registry(registry, resources)
check_graph(graph, True, "valid served dataset mapping")
combined = (
    graph
    + Graph().parse(ROOT / "tests/discovery-example.ttl")
    + Graph().parse(ROOT / "examples/agent-card.ttl")
)
check_graph(combined, True, "combined resource wiki card and dataset profile")
closure = combined + ontology
DeductiveClosure(OWLRL_Semantics).expand(closure)
for d in registry["datasets"]:
    node = URIRef(d["iri"])
    assert (node, RDF.type, DCAT.Dataset) in closure and (
        node,
        RDF.type,
        E.Participant,
    ) in closure
    for cls in [E.Bundle, E.Agent, E.Connector, E.ServiceEndpoint]:
        assert (node, RDF.type, cls) not in closure
passed.append("OWL inferred role separation")
node = URIRef(registry["datasets"][0]["iri"])
service = URIRef(resources["okn"]["iri"])
for cls in [E.Bundle, E.Agent, E.Connector, E.ServiceEndpoint]:
    bad = graph + Graph()
    bad.add((node, RDF.type, cls))
    check_graph(bad, False, "reject dataset role " + str(cls))
for predicate in [DCTERMS.identifier, DCTERMS.title, E.hasSemanticEntrypoint]:
    bad = graph + Graph()
    bad.remove((node, predicate, None))
    check_graph(bad, False, "missing " + str(predicate))
bad = graph + Graph()
bad.remove((service, DCAT.servesDataset, node))
check_graph(bad, False, "orphan dataset")
bad = graph + Graph()
inspection = bad.value(node, E.hasSemanticEntrypoint)
bad.set((inspection, E.invokedThrough, URIRef("urn:unrelated:endpoint")))
check_graph(bad, False, "inspection outside serving service")
bad = graph + Graph()
second = URIRef(registry["datasets"][1]["iri"])
bad.set((second, DCTERMS.identifier, Literal(registry["datasets"][0]["id"])))
check_graph(bad, False, "duplicate RDF identifier")
# Existing service may expose other endpoint types; only one MCP binding is required.
extra = graph + Graph()
endpoint = URIRef("urn:example:openapi")
extra.add((service, E.hasService, endpoint))
extra.add((endpoint, RDF.type, E.OpenAPI))
check_graph(extra, True, "other service endpoints allowed")
assert len(list(graph.objects(service, DCAT.servesDataset))) == 2
assert all(
    len(list(graph.objects(URIRef(d["iri"]), E.hasSemanticEntrypoint))) == 1
    for d in registry["datasets"]
)
# Version is a fact only if explicitly observed; timestamps/arguments are retained in JSON.
assert not list(
    graph.triples((None, URIRef("http://www.w3.org/ns/dcat#version"), None))
)
assert not list(graph.triples((None, DCTERMS.modified, None)))
assert (
    node,
    URIRef("http://www.w3.org/ns/dcat#version"),
    Literal("fixture-v1"),
) in adapter.map_registry(versioned, resources)
passed.append("version absence and observation scope")
print(
    json.dumps(
        {"profile_version": "0.1.0", "passed": len(passed), "checks": passed}, indent=2
    )
)
