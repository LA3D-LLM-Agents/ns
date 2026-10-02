"""Offline reference contract/mapper, not a production loader, harvester or executor."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import quote

from jsonschema import Draft202012Validator, FormatChecker
from rdflib import DCTERMS, RDF, RDFS, XSD, Literal, Namespace, URIRef
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profiles/join-recipe-discovery/0.1.0"
JR = Namespace("https://la3d-llm-agents.github.io/ns/profiles/join-recipe-discovery/0.1.0/vocab.ttl#")
PROV = Namespace("http://www.w3.org/ns/prov#")
ECO = Namespace("https://la3d-llm-agents.github.io/ns/eco#")
SCHEMA = json.loads((PROFILE / "schema.json").read_text())
SEARCH_SCHEMA = json.loads((PROFILE / "search.schema.json").read_text())
spec = importlib.util.spec_from_file_location(
    "join_dataset_adapter", ROOT / "examples/datasets/adapter.py"
)
dataset_adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dataset_adapter)


def canonical(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if json.loads(encoded) != value:
        raise ValueError("Only JSON-native types and string object keys are supported")
    return encoded


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def unique(values):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate identity")


def check_source(source, resources):
    if source["payload_sha256"] != digest(source["payload"]):
        raise ValueError("Source digest mismatch")
    if source["tool_name"] not in resources.get(source["resource_id"], {}).get("allowed_tools", []):
        raise ValueError("Unapproved source tool")
    status = source["payload"].get("status")
    if status not in ("verified", "known_non_join", "unknown"):
        raise ValueError("Unrecognized source status")
    field = {"verified": "joins", "known_non_join": "non_joins", "unknown": "note"}[status]
    if field not in source["payload"]:
        raise ValueError("Missing source status detail")
    detail = source["payload"][field]
    if status == "unknown":
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("Missing unknown explanation")
    elif not isinstance(detail, list) or not detail or not all(isinstance(v, dict) for v in detail):
        raise ValueError("Invalid source status detail")
    return status


def check_participants(parts, datasets):
    unique([p["role_id"] for p in parts])
    unique([p["dataset_id"] for p in parts])
    if [p["role"] for p in parts].count("left") != 1 or [p["role"] for p in parts].count(
        "right"
    ) != 1:
        raise ValueError("Exactly one left and right required")
    for p in parts:
        d = datasets.get(p["dataset_id"])
        if not d or any(p[k] != d[k] for k in ("iri", "named_graph")):
            raise ValueError("Dangling or remapped dataset")


def check_query(template, parts):
    if hashlib.sha256(template["query"].encode()).hexdigest() != template["sha256"]:
        raise ValueError("Template digest mismatch")
    if len(template["query"].encode()) > 65536:
        raise ValueError("Template byte limit")
    unique(template["named_graphs"])
    expected = {p["named_graph"] for p in parts}
    if set(template["named_graphs"]) != expected:
        raise ValueError("Graph declarations differ from participants")
    parsed = parseQuery(template["query"])
    if parsed[1].name != "SelectQuery":
        raise ValueError("Only SELECT templates in this profile")
    graphs = set()

    def walk(value):
        if isinstance(value, CompValue):
            if value.name == "ServiceGraphPattern":
                raise ValueError("External SERVICE outside this profile")
            if value.name == "GraphGraphPattern":
                term = value["term"]
                if not isinstance(term, URIRef):
                    raise ValueError("Explicit absolute GRAPH IRI required")
                graphs.add(str(term))
            if value.name == "DatasetClause":
                raise ValueError("FROM outside this fixed GRAPH profile")
            for child in value.values():
                walk(child)
        elif isinstance(value, (list, tuple)) or type(value).__name__ == "ParseResults":
            for child in value:
                walk(child)

    walk(parsed)
    if graphs != expected:
        raise ValueError("Query graph scope differs from declared participants")


def validate_registry(data, dataset_registry, resources):
    if len(canonical(data)) > 2_000_000:
        raise ValueError("Registry byte limit")
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(data)
    dataset_adapter.validate_registry(dataset_registry, resources)
    ds = {d["id"]: d for d in dataset_registry["datasets"]}
    records = data["recipes"] + data["assessments"]
    unique([r["id"] for r in records])
    unique([r["iri"] for r in records])
    reserved = {d["iri"] for d in ds.values()} | {
        r[k] for r in resources.values() for k in ("iri", "endpoint_iri")
    }
    for record in records:
        if record["iri"] in reserved or record["iri"].startswith("urn:join-profile:"):
            raise ValueError("Role identity collision")
        check_participants(record["participants"], ds)
        source = record.get("source") or record["provenance"]["observation"]
        status = check_source(source, resources)
        # Source request pair is unordered; authored participant orientation is preserved.
        source_resource = source["resource_id"]
        expected_shortnames = set()
        for p in record["participants"]:
            if p["role"] in ("left", "right"):
                bindings = [
                    b
                    for b in ds[p["dataset_id"]]["access_bindings"]
                    if b["resource_id"] == source_resource
                ]
                if len(bindings) != 1:
                    raise ValueError("Unmapped source participant")
                expected_shortnames.add(bindings[0]["source_shortname"])
        if set(source["arguments"].values()) != expected_shortnames:
            raise ValueError("Source pair differs from assessed endpoints")
        if record in data["assessments"]:
            if "reported_date" in record and record["reported_date"] != source["payload"].get(
                "verified_on"
            ):
                raise ValueError("Assessment date differs from source")
            if record["status"] != status:
                raise ValueError("Assessment differs from source status")
            continue
        if record["upstream"]["resource_id"] != source_resource:
            raise ValueError("Upstream publisher mismatch")
        assertions = record["source_assertions"]
        if any(
            "reported_date" in a and a["reported_date"] != source["payload"].get("verified_on")
            for a in assertions
        ):
            raise ValueError(
                "Source status date differs from source; count dates belong to metrics"
            )
        if any(a["status"] != status for a in assertions):
            raise ValueError("Assertion differs from source status")
        if status == "verified":
            joins = [
                j for j in source["payload"]["joins"] if j.get("id") == record["upstream"]["id"]
            ]
            if len(joins) != 1:
                raise ValueError("Missing upstream recipe identity")
            for p in record["participants"]:
                if p["role"] in ("left", "right"):
                    shortname = next(
                        b["source_shortname"]
                        for b in ds[p["dataset_id"]]["access_bindings"]
                        if b["resource_id"] == source_resource
                    )
                    if joins[0].get(p["role"] + "_kg") != shortname:
                        raise ValueError("Source orientation changed")
            if any(t["query"] != joins[0].get("skeleton_query") for t in record["templates"]):
                raise ValueError("Source status cannot verify a changed template")
        binding = record["execution_binding"]
        rid = binding["resource_id"]
        if binding["tool_name"] not in resources.get(rid, {}).get("allowed_tools", []):
            raise ValueError("Unapproved execution binding")
        if binding["query_argument"] in binding["arguments"]:
            raise ValueError("Fixed arguments cannot replace query")
        if any(
            not any(b["resource_id"] == rid for b in ds[p["dataset_id"]]["access_bindings"])
            for p in record["participants"]
        ):
            raise ValueError("One service must serve all participants")
        roles = {p["role_id"] for p in record["participants"]}
        if any(not s["predicates"] and not s["types"] for s in record["method"]["selections"]):
            raise ValueError("A selection needs a predicate or type")
        if {s["role_id"] for s in record["method"]["selections"]} != roles:
            raise ValueError("Missing selection roles")
        unique([s["role_id"] for s in record["method"]["selections"]])
        if any(t["role_id"] not in roles for t in record["method"]["transformations"]):
            raise ValueError("Unknown transformation role")
        templates = {t["id"]: t for t in record["templates"]}
        unique([t["id"] for t in record["templates"]])
        unique([t["sha256"] for t in record["templates"]])
        for t in templates.values():
            check_query(t, record["participants"])
        unique([o["id"] for o in record["local_observations"]])
        for obs in record["local_observations"]:
            t = templates.get(obs["template_id"])
            if not t or t["sha256"] != obs["template_sha256"]:
                raise ValueError("Observation belongs to another template")
            if obs["participants"] != record["participants"]:
                raise ValueError("Historical participant identity mismatch")
            if obs["arguments"] != {**binding["arguments"], binding["query_argument"]: t["query"]}:
                raise ValueError("Observation arguments differ")
            if obs["response_sha256"] != digest(obs["response"]):
                raise ValueError("Response digest mismatch")
            for field in ("versions", "schemas"):
                unique([v["dataset_id"] for v in obs[field]])
                if {v["dataset_id"] for v in obs[field]} != {
                    p["dataset_id"] for p in record["participants"]
                }:
                    raise ValueError("Missing schema/version observation")
            if obs["outcome"] != "inconclusive":
                response = obs["response"]
                variable = t["measurement"]["variable"]
                value = obs["metric"]["value"]
                if (
                    not isinstance(response.get("rows"), list)
                    or len(response["rows"]) != 1
                    or not isinstance(response["rows"][0], dict)
                    or type(response["rows"][0].get(variable)) is not int
                    or response.get("error")
                    or response.get("vars") != [variable]
                    or response.get("rows") != [{variable: value}]
                    or response.get("row_count") != 1
                ):
                    raise ValueError("Metric must match single aggregate response")
                if obs["metric"]["unit"] != t["measurement"]["unit"]:
                    raise ValueError("Metric unit differs")
                if (value > 0) != (obs["outcome"] == "matches_observed"):
                    raise ValueError("Outcome does not match count")
    return data


def project(data, dataset_registry, resources):
    validate_registry(data, dataset_registry, resources)
    graph = dataset_adapter.map_registry(dataset_registry, resources)

    def lit(node, predicate, value, datatype=None):
        graph.add((node, predicate, Literal(value, datatype=datatype)))

    for record in data["recipes"] + data["assessments"]:
        node = URIRef(record["iri"])
        is_recipe = record in data["recipes"]
        graph.add((node, RDF.type, JR.Recipe if is_recipe else JR.Assessment))
        lit(node, DCTERMS.identifier, record["id"])
        lit(node, RDFS.label, record["label"])
        lit(node, DCTERMS.description, record["description"])
        base = "urn:join-profile:" + quote(record["id"], safe="") + ":"
        for p in record["participants"]:
            part = URIRef(base + "participant:" + quote(p["role_id"], safe=""))
            graph.add((node, JR.hasParticipation, part))
            graph.add((part, RDF.type, JR.Participation))
            graph.add((part, JR.dataset, URIRef(p["iri"])))
            lit(part, JR.role, p["role"])
        if not is_recipe:
            lit(node, JR.status, record["status"])
            lit(node, JR.scope, record["scope"])
            lit(node, JR.observedAt, record["source"]["observed_at"], XSD.dateTime)
            lit(node, JR.payloadDigest, record["source"]["payload_sha256"])
            if "reported_date" in record:
                lit(node, JR.reportedDate, record["reported_date"], XSD.date)
            continue
        graph.add(
            (
                node,
                JR.executionResource,
                URIRef(resources[record["execution_binding"]["resource_id"]]["iri"]),
            )
        )
        source = record["provenance"]["observation"]
        for i, a in enumerate(record["source_assertions"]):
            assertion = URIRef(base + "assertion:" + str(i))
            graph.add((node, JR.hasSourceAssertion, assertion))
            graph.add((assertion, RDF.type, JR.SourceAssertion))
            lit(assertion, JR.status, a["status"])
            lit(assertion, JR.scope, a["scope"])
            lit(assertion, JR.observedAt, source["observed_at"], XSD.dateTime)
            lit(assertion, JR.payloadDigest, source["payload_sha256"])
            if "reported_date" in a:
                lit(assertion, JR.reportedDate, a["reported_date"], XSD.date)
        for t in record["templates"]:
            template = URIRef(base + "template:" + quote(t["id"], safe=""))
            graph.add((node, JR.hasTemplate, template))
            graph.add((template, RDF.type, JR.QueryTemplate))
            lit(template, JR.templateDigest, t["sha256"])
        for o in record["local_observations"]:
            run = URIRef(base + "observation:" + quote(o["id"], safe=""))
            graph.add((run, RDF.type, JR.ExecutionObservation))
            graph.add((node, JR.hasObservation, run))
            graph.add((run, PROV.used, node))
            graph.add(
                (run, PROV.used, URIRef(base + "template:" + quote(o["template_id"], safe="")))
            )
            for p in o["participants"]:
                graph.add((run, PROV.used, URIRef(p["iri"])))
            lit(run, JR.outcome, o["outcome"])
            lit(run, JR.observedAt, o["observed_at"], XSD.dateTime)
            result = URIRef(str(run) + ":result")
            graph.add((result, RDF.type, JR.Result))
            graph.add((result, PROV.wasGeneratedBy, run))
            lit(result, JR.payloadDigest, o["response_sha256"])
            if "metric" in o:
                lit(result, JR["count"], o["metric"]["value"], XSD.integer)
                lit(result, JR.unit, o["metric"]["unit"])
            else:
                lit(result, JR.errorCode, o["error"]["code"])
    return graph


def search(
    data,
    datasets,
    resources,
    resource_revision,
    *,
    dataset_id=None,
    with_dataset_id=None,
    query="",
    resource_id=None,
    match_kind=None,
    limit=20,
    offset=0,
    revision=None,
):
    """Reference pagination contract only; no MCP server, persistence or network."""
    validate_registry(data, datasets, resources)
    ids = {d["id"] for d in datasets["datasets"]}
    if (
        type(limit) is not int
        or not 1 <= limit <= 100
        or type(offset) is not int
        or not 0 <= offset <= 5000
    ):
        raise ValueError("Invalid pagination")
    if not isinstance(query, str) or len(query) > 1000:
        raise ValueError("Invalid query")
    for value in (dataset_id, with_dataset_id, resource_id, match_kind):
        if value is not None and (
            not isinstance(value, str) or not value.strip() or len(value) > 200
        ):
            raise ValueError("Invalid filter")
    if (dataset_id is not None and dataset_id not in ids) or (
        with_dataset_id is not None
        and (not dataset_id or with_dataset_id not in ids or dataset_id == with_dataset_id)
    ):
        raise ValueError("Invalid dataset pair")
    stable = copy.deepcopy(data)
    for key in ("recipes", "assessments"):
        stable[key].sort(key=lambda r: r["id"])
    ds = copy.deepcopy(datasets)
    ds["datasets"].sort(key=lambda r: r["id"])
    revisions = {
        "profile_version": "0.1.0",
        "recipe_registry_revision": digest(stable),
        "dataset_revision": digest(ds),
        "resource_revision": resource_revision,
    }
    view = digest(revisions)
    if revision is not None and revision != view:
        raise ValueError("stale_recipes")
    entries = []
    pair_records = []
    for kind, key in [("assessment", "assessments"), ("recipe", "recipes")]:
        for r in sorted(data[key], key=lambda r: r["id"]):
            participants = r["participants"]
            if with_dataset_id:
                if {p["dataset_id"] for p in participants if p["role"] in ("left", "right")} != {
                    dataset_id,
                    with_dataset_id,
                }:
                    continue
            elif dataset_id and not any(p["dataset_id"] == dataset_id for p in participants):
                continue
            pair_records.append(r)
            rid = (
                r["execution_binding"]["resource_id"]
                if kind == "recipe"
                else r["source"]["resource_id"]
            )
            method = r["method"]["kind"] if kind == "recipe" else r.get("method_kind")
            text = " ".join([r["id"], r["label"], r["description"], *r.get("tags", [])]).casefold()
            if resource_id is not None and rid != resource_id:
                continue
            if match_kind is not None and method != match_kind:
                continue
            if not all(t in text for t in query.casefold().split()):
                continue
            entries.append({"entry_type": kind, "record": copy.deepcopy(r)})
    page = entries[offset : offset + limit]
    coverage = {"scope": "reviewed_subset"}
    if with_dataset_id:
        coverage["pair_state"] = "cataloged" if pair_records else "not_cataloged"
    result = {
        **revisions,
        "view_revision": view,
        "coverage": coverage,
        "entries": page,
        "total": len(entries),
        "recipe_total": sum(e["entry_type"] == "recipe" for e in entries),
        "assessment_total": sum(e["entry_type"] == "assessment" for e in entries),
        "returned": len(page),
        "offset": offset,
        "next_offset": offset + len(page) if offset + len(page) < len(entries) else None,
    }
    Draft202012Validator(SEARCH_SCHEMA, format_checker=FormatChecker()).validate(result)
    return result
