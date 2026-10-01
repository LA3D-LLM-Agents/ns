"""Offline reference validator/structural mapper; no production loader or network calls."""

import json
from pathlib import Path
from urllib.parse import quote

from jsonschema import Draft202012Validator, FormatChecker
from rdflib import DCAT, DCTERMS, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profiles/dataset-discovery/0.1.0"
ECO = Namespace("https://la3d-llm-agents.github.io/ns/eco#")
SCHEMA = json.loads((PROFILE / "schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def validate_registry(registry, resources):
    VALIDATOR.validate(registry)
    ids, iris, routes = set(), set(), set()
    for dataset in registry["datasets"]:
        for value, seen in [(dataset["id"], ids), (dataset["iri"], iris)]:
            if value in seen:
                raise ValueError("Duplicate dataset identity")
            seen.add(value)
        services = set()
        for binding in dataset["access_bindings"]:
            resource_id = binding["resource_id"]
            if resource_id not in resources:
                raise ValueError("Unknown access resource")
            if resource_id in services:
                raise ValueError("Duplicate resource binding")
            services.add(resource_id)
            route = resource_id, dataset["named_graph"]
            if route in routes:
                raise ValueError("Named graph assigned to multiple dataset identities")
            routes.add(route)
            inspections = binding["semantic_inspections"] + [
                binding["version_inspection"]
            ]
            if any(
                i["tool_name"] not in resources[resource_id]["allowed_tools"]
                for i in inspections
            ):
                raise ValueError("Inspection tool not approved by access resource")
        # Observation tools can have their own resource, but never an unrecognized route/tool.
        observations = list(dataset["provenance"]["observations"])
        observations += [
            dataset[k]["observation"]
            for k in ["source_version", "loaded_at"]
            if k in dataset
        ]
        for observation in observations:
            source = observation["source"]
            if "resource_id" in source and (
                source["resource_id"] not in resources
                or source["tool"]["tool_name"]
                not in resources[source["resource_id"]]["allowed_tools"]
            ):
                raise ValueError("Unknown observation resource or tool")
    return registry


def map_registry(registry, resources):
    validate_registry(registry, resources)
    graph = Graph()
    for dataset in registry["datasets"]:
        node = URIRef(dataset["iri"])
        for cls in [DCAT.Dataset, ECO.Participant]:
            graph.add((node, RDF.type, cls))
        for predicate, value in [
            (DCTERMS.identifier, dataset["id"]),
            (DCTERMS.title, dataset["label"]),
            (RDFS.label, dataset["label"]),
            (DCTERMS.description, dataset["description"]),
        ]:
            graph.add((node, predicate, Literal(value)))
        for tag in dataset["tags"]:
            graph.add((node, DCAT.keyword, Literal(tag)))
        if "source_version" in dataset:
            graph.add(
                (
                    node,
                    URIRef("http://www.w3.org/ns/dcat#version"),
                    Literal(dataset["source_version"]["value"]),
                )
            )
        for binding in dataset["access_bindings"]:
            resource = resources[binding["resource_id"]]
            service, endpoint = (
                URIRef(resource["iri"]),
                URIRef(resource["endpoint_iri"]),
            )
            for cls in [ECO.Connector, DCAT.DataService]:
                graph.add((service, RDF.type, cls))
            graph.add((service, RDFS.label, Literal(binding["resource_id"])))
            graph.add((service, DCAT.servesDataset, node))
            graph.add((service, ECO.hasService, endpoint))
            graph.add((endpoint, RDF.type, ECO.MCPEndpoint))
            graph.add((endpoint, ECO.transport, Literal("streamable-http")))
            graph.add(
                (
                    endpoint,
                    ECO.serviceURL,
                    Literal(resource["url"], datatype=XSD.anyURI),
                )
            )
            for number, tool in enumerate(binding["semantic_inspections"]):
                inspection = URIRef(
                    "urn:dataset-inspection:"
                    + quote(dataset["id"], safe="")
                    + ":"
                    + quote(binding["resource_id"], safe="")
                    + ":"
                    + str(number)
                )
                graph.add((node, ECO.hasSemanticEntrypoint, inspection))
                graph.add((inspection, RDF.type, ECO.SemanticEntrypoint))
                graph.add((inspection, ECO.toolName, Literal(tool["tool_name"])))
                graph.add((inspection, ECO.invokedThrough, endpoint))
                graph.add((inspection, ECO.executionLocation, ECO.ResourceSide))
    return graph
