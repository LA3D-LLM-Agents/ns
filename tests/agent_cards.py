"""Executable proposed card mapping, not the production enrollment/importer."""
import copy
import json
from pathlib import Path
from urllib.parse import quote

import yaml
from jsonschema import validate as validate_json, ValidationError
from owlrl import DeductiveClosure, OWLRL_Semantics
from pyshacl import validate
from rdflib import Graph, Namespace, RDF, RDFS, OWL, DCTERMS, XSD, Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
E = Namespace("https://la3d-llm-agents.github.io/ns/eco#")
schema = json.loads((ROOT / "examples/agent-card.schema.json").read_text())
ontology = Graph().parse(ROOT / "eco.ttl")
shapes = Graph().parse(ROOT / "eco-discovery-shapes.ttl")


def parse_card(text):
    record = yaml.safe_load(text.split("---", 2)[1])["x-fabric-card"]
    validate_json(record, schema)
    for field in ("skills", "knowledge_bundles", "interfaces"):
        ids = [i["id"] for i in record[field]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate identifiers")
    bundles = {i["id"] for i in record["knowledge_bundles"]}
    for interface in record["interfaces"]:
        if interface["kind"] == "clone-and-invoke" and interface["bundle_id"] not in bundles:
            raise ValueError("Unknown knowledge bundle")
    return record


def map_card(record):
    g = Graph()
    agent = URIRef("urn:fabric:agent:" + quote(record["id"], safe=""))
    card = URIRef(record["card_url"])
    def add(s, p, o): g.add((s, p, o))
    add(agent, RDF.type, E.Agent)
    add(agent, DCTERMS.identifier, Literal(record["id"]))
    add(agent, RDFS.label, Literal(record["name"]))
    add(agent, RDFS.comment, Literal(record["description"]))
    add(agent, E.hasCard, card)
    add(card, RDF.type, E.AgentCard)
    add(card, E.documentURL, Literal(record["card_url"], datatype=XSD.anyURI))
    add(card, DCTERMS.format, Literal("text/markdown"))
    add(card, DCTERMS.hasVersion, Literal(record["schema_version"]))
    for skill in record["skills"]:
        node = URIRef(str(agent) + ":skill:" + skill["id"])
        add(agent, E.hasCapability, node)
        add(node, RDF.type, E.Capability)
        add(node, DCTERMS.identifier, Literal(skill["id"]))
        add(node, RDFS.label, Literal(skill["name"]))
        add(node, RDFS.comment, Literal(skill["description"]))
        for tag in skill["tags"]: add(node, E.keyword, Literal(tag))
    for bundle in record["knowledge_bundles"]:
        node = URIRef(bundle["url"])
        add(node, RDF.type, E.Bundle)
        add(node, RDFS.label, Literal(bundle["id"]))
        add(agent, E.hasKnowledgeBundle, node)
    for interface in record["interfaces"]:
        node = URIRef(str(agent) + ":interface:" + interface["id"])
        kind = interface["kind"]
        add(agent, E.hasService, node)
        add(node, RDF.type, {"clone-and-invoke": E.CloneEndpoint,
                            "mcp": E.MCPEndpoint, "a2a": E.A2AEndpoint}[kind])
        add(node, E.serviceURL, Literal(interface["url"], datatype=XSD.anyURI))
        if kind == "clone-and-invoke":
            bundle = next(b for b in record["knowledge_bundles"] if b["id"] == interface["bundle_id"])
            add(URIRef(bundle["url"]), E.hasService, node)
            add(agent, E.consumptionMode, E.CloneAndInvoke)
        else:
            add(node, E.transport, Literal(interface["transport"]))
            if kind == "a2a": add(node, DCTERMS.hasVersion, Literal(interface["protocol_version"]))
    return g, agent, card


def materialize_inverses(graph):
    """Bounded declared inverse expansion on a copy; no network/full OWL closure."""
    result = Graph()
    for triple in graph: result.add(triple)
    for forward, reverse in ontology.subject_objects(OWL.inverseOf):
        for subject, obj in list(result.subject_objects(forward)):
            result.add((obj, reverse, subject))
        for subject, obj in list(result.subject_objects(reverse)):
            result.add((obj, forward, subject))
    return result


def conforms(graph):
    return validate(graph, ont_graph=ontology, shacl_graph=shapes,
                    inference="rdfs", do_owl_imports=False)[0]


def main():
    record = parse_card((ROOT / "examples/Card_llm-wiki-fabric.md").read_text())
    graph, agent, card = map_card(record)
    assert (card, E.describesAgent, agent) not in graph
    graph = materialize_inverses(graph)
    assert conforms(graph)
    assert set(materialize_inverses(graph)) == set(graph)
    closure = graph + ontology
    DeductiveClosure(OWLRL_Semantics).expand(closure)
    assert (agent, RDF.type, E.Bundle) not in closure
    assert (agent, RDF.type, E.Connector) not in closure
    assert (card, RDF.type, E.ServiceEndpoint) not in closure
    assert (card, RDF.type, E.SemanticEntrypoint) not in closure
    assert not list(closure.subjects(RDF.type, E.A2AEndpoint))
    questions = {
        "card-describes-agent": (card, E.describesAgent, agent) in graph,
        "four-grouped-skills": len(list(graph.objects(agent, E.hasCapability))) == 4,
        "card-not-invocation-url": not list(graph.objects(card, E.serviceURL)),
        "wiki-is-separate-bundle": all(n != agent for n in graph.objects(agent, E.hasKnowledgeBundle)),
        "reverse-service-to-agent": any((n, E.serviceOf, agent) in graph for n in graph.objects(agent, E.hasService)),
        "invocation-is-clone": any((n, RDF.type, E.CloneEndpoint) in graph for n in graph.objects(agent, E.hasService)),
    }
    assert all(questions.values())
    # Audit covers every object property, including both ends of every declared pair.
    audit = json.loads((ROOT / "tests/inverse-audit.json").read_text())
    covered = set(audit["without_named_inverse"])
    for f, inv in audit["paired"].items():
        assert (E[f], OWL.inverseOf, E[inv]) in ontology
        assert set(ontology.objects(E[f], RDFS.domain)) == set(ontology.objects(E[inv], RDFS.range))
        assert set(ontology.objects(E[f], RDFS.range)) == set(ontology.objects(E[inv], RDFS.domain))
        probe = Graph()
        probe.add((URIRef("urn:test:a"), E[f], URIRef("urn:test:b")))
        assert (URIRef("urn:test:b"), E[inv], URIRef("urn:test:a")) in materialize_inverses(probe)
        probe = Graph()
        probe.add((URIRef("urn:test:b"), E[inv], URIRef("urn:test:a")))
        assert (URIRef("urn:test:a"), E[f], URIRef("urn:test:b")) in materialize_inverses(probe)
        covered.update((f, inv))
    assert {E[n] for n in covered} == set(ontology.subjects(RDF.type, OWL.ObjectProperty))
    rejected = []
    for name, remove, add in [
        ("missing-card-subject", [(card, E.describesAgent, None)], []),
        ("card-used-as-service", [], [(agent, E.hasService, card)]),
        ("credential-card-url", [(card, E.documentURL, None)], [(card, E.documentURL, Literal("https://user:secret@example.org/card", datatype=XSD.anyURI))]),
        ("session-without-agent", [], [(URIRef("urn:test:session"), RDF.type, E.AgentSession)]),
        ("a2a-without-route", [], [(URIRef("urn:test:a2a"), RDF.type, E.A2AEndpoint)]),
    ]:
        bad = Graph()
        for triple in graph: bad.add(triple)
        for triple in remove: bad.remove(triple)
        for triple in add: bad.add(triple)
        assert not conforms(bad), name
        rejected.append(name)
    session_graph = Graph()
    for triple in graph: session_graph.add(triple)
    session_node = URIRef("urn:test:valid-session")
    session_graph.add((session_node, RDF.type, E.AgentSession))
    session_graph.add((session_node, E.sessionOfAgent, agent))
    session_graph = materialize_inverses(session_graph)
    assert conforms(session_graph)
    assert (agent, E.hasSession, session_node) in session_graph
    session_closure = session_graph + ontology
    DeductiveClosure(OWLRL_Semantics).expand(session_closure)
    assert (session_node, RDF.type, E.Agent) not in session_closure
    assert (session_node, RDF.type, E.Bundle) not in session_closure
    punctuation = copy.deepcopy(record)
    punctuation["description"] = 'Ask (/ask-db): read-only; quotes "and" unicode — safe.'
    assert parse_card("---\n" + yaml.safe_dump({"x-fabric-card": punctuation}) + "---\n") == punctuation
    # JSON schema plus semantic validation catches generator failures before RDF mapping.
    for name, mutate in [
        ("duplicate-skill", lambda c: c["skills"].append(copy.deepcopy(c["skills"][0]))),
        ("missing-description", lambda c: c.pop("description")),
        ("unknown-bundle", lambda c: c["interfaces"][0].update(bundle_id="missing")),
    ]:
        bad = copy.deepcopy(record); mutate(bad)
        try:
            parse_card("---\n" + yaml.safe_dump({"x-fabric-card": bad}) + "---\n")
        except (ValueError, ValidationError):
            rejected.append(name)
        else: raise AssertionError(name)
    # Exercise explicit A2A and MCP advertisements as synthetic variants only.
    for kind, fields in [("mcp", {"transport": "streamable-http"}),
                         ("a2a", {"transport": "example-transport", "protocol_version": "example-version"})]:
        variant = copy.deepcopy(record)
        variant["interfaces"] = [{"id": "synthetic", "kind": kind, "url": "https://example.org/invoke", **fields}]
        validate_json(variant, schema)
        mapped, _, _ = map_card(variant)
        assert conforms(materialize_inverses(mapped))
    graph.bind("eco", E)
    # Reproducible example, no timestamps or runtime announcements.
    expected = Graph().parse(ROOT / "examples/agent-card.ttl")
    from rdflib.compare import isomorphic
    assert isomorphic(graph, expected)
    print(json.dumps({"agent_questions": questions, "inverse_pairs": len(audit["paired"]),
                      "unpaired_facets": len(audit["without_named_inverse"]),
                      "negative_cases": rejected, "synthetic_interface_checks": ["mcp", "a2a"]}, indent=2))

if __name__ == "__main__":
    main()
