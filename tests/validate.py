"""Offline ontology/profile checks. Examples are proposed metadata, not live results."""

import json
import hashlib
from pathlib import Path

from owlrl import DeductiveClosure, OWLRL_Semantics
from pyshacl import validate
from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[1]
ECO = Namespace("https://la3d-llm-agents.github.io/ns/eco#")
EX = Namespace("urn:eco:example:")
ontology = Graph().parse(ROOT / "eco.ttl")
shapes = Graph().parse(ROOT / "eco-discovery-shapes.ttl")
example = Graph().parse(ROOT / "tests/discovery-example.ttl")
assert (ROOT / "eco").read_bytes() == (ROOT / "eco.ttl").read_bytes()
assert (ROOT / "versions/0.3.0/eco.ttl").read_bytes() == (ROOT / "eco.ttl").read_bytes()
assert (ROOT / "versions/0.3.0/eco-discovery-shapes.ttl").read_bytes() == (
    ROOT / "eco-discovery-shapes.ttl"
).read_bytes()
assert list(ontology.objects(None, OWL.versionInfo)) == [Literal("0.3.0")]
assert not list(ontology.triples((None, OWL.imports, None)))
for name, digest in {
    "eco.ttl": "b3e2263425c99758515980ad0f71737991882f72771ed064c0b5303b3304a70a",
    "eco-discovery-shapes.ttl": "2a45a1ce3ef23f04fc3570438a120d61d2156b1d94ca2de9e167b6ad10b6a8ea",
}.items():
    assert hashlib.sha256((ROOT / "versions/0.2.0" / name).read_bytes()).hexdigest() == digest
# No PAD domain classes or properties are copied into fabric.
assert not any(str(s).startswith("https://pad.crc.nd.edu/") for s in ontology.subjects())
assert (ECO.hasCapability, RDFS.domain, ECO.Participant) in ontology
assert (ECO.hasCapability, OWL.inverseOf, ECO.providedBy) in ontology


def check(graph, expected, name):
    conforms, _, report = validate(
        graph, shacl_graph=shapes, ont_graph=ontology, inference="rdfs", do_owl_imports=False
    )
    assert conforms == expected, name + "\n" + report
    return name


passed = [check(example, True, "valid-discovery-with-unknown-maturity")]
# Full OWL-RL test catches unintended inverse/domain classification.
closure = example + ontology
DeductiveClosure(OWLRL_Semantics).expand(closure)
assert (EX.wiki, RDF.type, ECO.Participant) in closure
assert (EX.wiki, RDF.type, ECO.Connector) not in closure
assert (EX.dictionary, RDF.type, ECO.Ontology) not in closure
assert (EX.schema, RDF.type, ECO.Ontology) not in closure
assert (EX.ssh, RDF.type, ECO.CredentialRequirement) not in closure
assert (EX.card, RDF.type, ECO.ServiceEndpoint) not in closure
assert (EX.agent, RDF.type, ECO.Bundle) not in closure
assert (EX.agent, RDF.type, ECO.Connector) not in closure
passed.append("owl-role-separation")
query_results = {}
for path in sorted((ROOT / "tests/queries").glob("*.rq")):
    result = closure.query(path.read_text())
    assert bool(result), path.name
    query_results[path.name] = True

assert len(query_results) == 8

mutations = [
    (
        "contradictory-stdio-execution",
        [(EX.schema, ECO.executionLocation, None)],
        [(EX.schema, ECO.executionLocation, ECO.ResourceSide)],
    ),
    ("missing-provider", [(EX.cards, ECO.providedBy, EX.pad)], []),
    ("http-mcp-without-url", [(EX["pad-mcp"], ECO.serviceURL, None)], []),
    (
        "stdio-with-fake-url",
        [],
        [
            (
                EX["local-direct"],
                ECO.serviceURL,
                Literal("https://localhost/mcp", datatype=XSD.anyURI),
            )
        ],
    ),
    (
        "wrong-transport",
        [(EX["pad-mcp"], ECO.transport, None)],
        [(EX["pad-mcp"], ECO.transport, Literal("unknown"))],
    ),
    ("missing-semantic-invocation-context", [(EX.schema, ECO.invokedThrough, None)], []),
    ("semantic-entrypoint-with-no-route", [(EX.schema, ECO.toolName, None)], []),
    ("missing-access-mechanism", [(EX.ssh, ECO.accessMechanism, None)], []),
    (
        "credential-property-in-prerequisite",
        [],
        [(EX.ssh, URIRef("urn:example:password"), Literal("test-placeholder"))],
    ),
    (
        "credential-bearing-url",
        [(EX["pad-mcp"], ECO.serviceURL, None)],
        [
            (
                EX["pad-mcp"],
                ECO.serviceURL,
                Literal("https://user:secret@example.org/mcp", datatype=XSD.anyURI),
            )
        ],
    ),
]
for name, removals, additions in mutations:
    graph = Graph()
    for triple in example:
        graph.add(triple)
    for triple in removals:
        graph.remove(triple)
    for triple in additions:
        graph.add(triple)
    passed.append(check(graph, False, name))

# Legacy vocabulary remains loadable; its separate maturity/answer policy is not
# silently applied to the new discovery-only profile.
Graph().parse(ROOT / "eco-shapes.ttl")
print(
    json.dumps(
        {
            "version": "0.3.0",
            "ontology_triples": len(ontology),
            "classes": len(set(ontology.subjects(RDF.type, OWL.Class))),
            "checks": passed,
            "competency_queries": query_results,
        },
        indent=2,
    )
)
