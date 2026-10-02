"""Offline recipe contract checks; no tools, queries or network are invoked."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from owlrl import DeductiveClosure, OWLRL_Semantics
from pyshacl import validate
from rdflib import DCAT, RDF, Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "recipe_adapter", ROOT / "examples/join-recipes/adapter.py"
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
p = ROOT / "examples/join-recipes"


def load(name):
    return json.loads((p / name).read_text())


pilot = load("pilot.json")
mixed = load("synthetic-statuses.json")
ds = load("datasets.json")
rs = load("resources.json")
passed = []
Draft202012Validator.check_schema(a.SCHEMA)
Draft202012Validator.check_schema(a.SEARCH_SCHEMA)
ontology = Graph().parse(ROOT / "versions/0.3.0/eco.ttl")
ontology.parse(a.PROFILE / "vocab.ttl")
shapes = Graph().parse(ROOT / "versions/0.3.0/eco-discovery-shapes.ttl")
shapes.parse(ROOT / "profiles/dataset-discovery/0.1.0/shapes.ttl")
shapes.parse(a.PROFILE / "shapes.ttl")


def check(data, expected, name):
    try:
        a.validate_registry(data, ds, rs)
        ok = True
    except (ValueError, ValidationError):
        ok = False
    assert ok == expected, name
    passed.append(name)


def graphcheck(graph, expected, name):
    ok, _, report = validate(
        graph, shacl_graph=shapes, ont_graph=ontology, inference="rdfs", do_owl_imports=False
    )
    assert ok == expected, name + "\n" + report
    passed.append(name)


check(pilot, True, "Historical live pilot and recent metadata")
check(mixed, True, "Explicitly synthetic source-status examples")
check(
    {"profile_version": "0.1.0", "coverage": "reviewed_subset", "recipes": [], "assessments": []},
    True,
    "Empty is not universal no-join",
)
mutations = [
    ("unknown field", lambda r: r.update(secret="x")),
    ("version", lambda r: r.update(profile_version="9")),
    ("duplicate id", lambda r: r["recipes"].append(copy.deepcopy(r["recipes"][0]))),
    ("dangling dataset", lambda r: r["recipes"][0]["participants"][0].update(dataset_id="missing")),
    (
        "changed named graph",
        lambda r: r["recipes"][0]["participants"][0].update(
            named_graph="https://example.org/other"
        ),
    ),
    ("role collision", lambda r: r["recipes"][0].update(iri=ds["datasets"][0]["iri"])),
    ("missing right", lambda r: r["recipes"][0]["participants"][1].update(role="left")),
    (
        "bad source date",
        lambda r: r["recipes"][0]["provenance"]["observation"].update(observed_at="yesterday"),
    ),
    ("query edit", lambda r: r["recipes"][0]["templates"][0].update(query="SELECT * WHERE {}")),
    (
        "transferred verification",
        lambda r: r["recipes"][0]["local_observations"][0].update(template_sha256="a" * 64),
    ),
    (
        "invented positive count",
        lambda r: r["recipes"][0]["local_observations"][0]["metric"].update(value=0),
    ),
    (
        "invented zero status",
        lambda r: r["recipes"][0]["local_observations"][0].update(outcome="no_matches_for_query"),
    ),
    (
        "error masquerades as match",
        lambda r: r["recipes"][0]["local_observations"][0].update(error={"code": "timeout"}),
    ),
    (
        "source status conflation",
        lambda r: r["recipes"][0]["source_assertions"][0].update(status="unknown"),
    ),
    (
        "source pair remap",
        lambda r: r["recipes"][0]["provenance"]["observation"]["arguments"].update(kg_b="evoweb"),
    ),
    (
        "unapproved execution",
        lambda r: r["recipes"][0]["execution_binding"].update(resource_id="missing"),
    ),
    (
        "query argument injection",
        lambda r: r["recipes"][0]["execution_binding"]["arguments"].update(query="ASK {}"),
    ),
    (
        "missing schema observation",
        lambda r: r["recipes"][0]["local_observations"][0]["schemas"].pop(),
    ),
    (
        "duplicate version observation",
        lambda r: r["recipes"][0]["local_observations"][0]["versions"].append(
            copy.deepcopy(r["recipes"][0]["local_observations"][0]["versions"][0])
        ),
    ),
    (
        "unbound transformation",
        lambda r: r["recipes"][0]["method"]["transformations"][0].update(role_id="missing"),
    ),
    ("missing upstream id", lambda r: r["recipes"][0]["upstream"].update(id="fake")),
    (
        "non JSON NaN",
        lambda r: r["recipes"][0]["provenance"]["observation"]["payload"].update(
            extra=float("nan")
        ),
    ),
]
for name, mutate in mutations:
    bad = copy.deepcopy(pilot)
    mutate(bad)
    check(bad, False, name)
for status in ["zero", "error"]:
    candidate = copy.deepcopy(pilot)
    o = candidate["recipes"][0]["local_observations"][0]
    o["id"] = "synthetic-" + status
    if status == "zero":
        o["outcome"] = "no_matches_for_query"
        o["metric"]["value"] = 0
        o["response"]["rows"] = [{"n": 0}]
    else:
        o["outcome"] = "inconclusive"
        o.pop("metric")
        o["error"] = {"code": "timeout"}
        o["response"] = {"error": "synthetic timeout"}
    o["response_sha256"] = a.digest(o["response"])
    check(candidate, True, "Synthetic " + status + " is distinct")
    graphcheck(a.project(candidate, ds, rs), True, "RDF synthetic " + status)

base = a.project(mixed, ds, rs)
graphcheck(base, True, "Combined resources/datasets/recipes/assessments")
recipe = URIRef(pilot["recipes"][0]["iri"])
jr = a.JR
run = next(base.objects(recipe, jr.hasObservation))
result = next(base.subjects(a.PROV.wasGeneratedBy, run))
for name, mutate in [
    ("recipe cannot be participant", lambda g: g.add((recipe, RDF.type, a.ECO.Participant))),
    ("recipe cannot be dataset", lambda g: g.add((recipe, RDF.type, DCAT.Dataset))),
    ("missing route", lambda g: g.remove((recipe, jr.executionResource, None))),
    (
        "missing participant role",
        lambda g: g.remove((next(g.objects(recipe, jr.hasParticipation)), jr.role, None)),
    ),
    ("bad result outcome", lambda g: g.set((run, jr.outcome, Literal("inconclusive")))),
    ("missing result digest", lambda g: g.remove((result, jr.payloadDigest, None))),
    ("wrong execution plan", lambda g: g.remove((run, a.PROV.used, recipe))),
    (
        "illegal source status",
        lambda g: g.set(
            (next(g.objects(recipe, jr.hasSourceAssertion)), jr.status, Literal("maybe"))
        ),
    ),
]:
    g = base + Graph()
    mutate(g)
    graphcheck(g, False, name)
inferred = base + ontology
DeductiveClosure(OWLRL_Semantics).expand(inferred)
assert (recipe, RDF.type, a.PROV.Plan) in inferred
assert (run, RDF.type, a.PROV.Activity) in inferred
for cls in (
    a.ECO.Participant,
    a.ECO.Connector,
    a.ECO.Agent,
    a.ECO.Bundle,
    a.ECO.ServiceEndpoint,
    DCAT.Dataset,
):
    assert (recipe, RDF.type, cls) not in inferred
passed.append("OWL-RL roles: plan is not service/dataset/agent")
# Combine actual existing agent-card fixture with new graph.
agent = Graph().parse(ROOT / "examples/agent-card.ttl")
graphcheck(base + agent, True, "Combined existing agent-card graph")

rev = "b" * 64
first = a.search(mixed, ds, rs, rev, dataset_id="okn-rdkg", with_dataset_id="okn-ruralkg", limit=1)
assert first["total"] == 3 and first["recipe_total"] == 1 and first["assessment_total"] == 2
all_entries = first["entries"]
offset = first["next_offset"]
while offset is not None:
    page = a.search(
        mixed,
        ds,
        rs,
        rev,
        dataset_id="okn-ruralkg",
        with_dataset_id="okn-rdkg",
        limit=1,
        offset=offset,
        revision=first["view_revision"],
    )
    all_entries += page["entries"]
    offset = page["next_offset"]
assert len({(e["entry_type"], e["record"]["id"]) for e in all_entries}) == 3
assert (
    next(e for e in all_entries if e["entry_type"] == "recipe")["record"]["participants"]
    == pilot["recipes"][0]["participants"]
)
filtered = a.search(
    mixed, ds, rs, rev, dataset_id="okn-rdkg", with_dataset_id="okn-ruralkg", query="no-such-label"
)
assert filtered["total"] == 0 and filtered["coverage"]["pair_state"] == "cataloged"
empty = a.search(
    {"profile_version": "0.1.0", "coverage": "reviewed_subset", "recipes": [], "assessments": []},
    ds,
    rs,
    rev,
    dataset_id="okn-rdkg",
    with_dataset_id="okn-ruralkg",
)
assert empty["coverage"]["pair_state"] == "not_cataloged"
assert "pair_state" not in a.search(pilot, ds, rs, rev)["coverage"]
assert a.search(mixed, ds, rs, rev, match_kind="identifier_normalization")["total"] == 1
passed.append("Mixed pagination, reverse pair, absent versus filtered and missing methods")
for changed_data, changed_ds, changed_resource in [
    (pilot, ds, rev),
    (mixed, ds, "c" * 64),
    (mixed, {**ds, "datasets": [{**d, "label": d["label"] + "!"} for d in ds["datasets"]]}, rev),
]:
    try:
        a.search(changed_data, changed_ds, rs, changed_resource, revision=first["view_revision"])
    except ValueError as e:
        assert str(e) == "stale_recipes"
    else:
        raise AssertionError("stale view accepted")
passed.append("Recipe/dataset/resource dependency invalidation")
for args in [
    {"with_dataset_id": "okn-rdkg"},
    {"dataset_id": "missing"},
    {"limit": False},
    {"limit": 101},
    {"offset": 5001},
]:
    try:
        a.search(pilot, ds, rs, rev, **args)
    except ValueError:
        pass
    else:
        raise AssertionError(args)
passed.append("Bounded invalid filters")
for filename in ["ruralkg-rdkg.json", "ruralkg-sawgraph.json", "evoweb-rdkg.json"]:
    payload = load("evidence/" + filename)["result"]
    assert payload["status"] in ["verified", "unknown", "known_non_join"]
passed.append("All three actual upstream status fixtures retained")
# Mutated templates and source responses below are synthetic rejection fixtures.
for name, query in [
    (
        "undeclared graph",
        "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <https://example.org/other> {?s ?p ?o} }",
    ),
    ("variable graph", "SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g {?s ?p ?o} }"),
    (
        "external service",
        "SELECT (COUNT(*) AS ?n) WHERE { SERVICE <https://example.org/sparql> {?s ?p ?o} }",
    ),
    ("from clause", "SELECT (COUNT(*) AS ?n) FROM <https://example.org/other> WHERE {?s ?p ?o}"),
    ("ask not count template", "ASK { ?s ?p ?o }"),
]:
    bad = copy.deepcopy(pilot)
    r = bad["recipes"][0]
    r["local_observations"] = []
    t = r["templates"][0]
    t["query"] = query
    t["sha256"] = hashlib.sha256(query.encode()).hexdigest()
    source = r["provenance"]["observation"]
    source["payload"]["joins"][0]["skeleton_query"] = query
    source["payload_sha256"] = a.digest(source["payload"])
    check(bad, False, name)
bad = copy.deepcopy(pilot)
r = bad["recipes"][0]
r["local_observations"] = []
r["participants"][0]["role"] = "right"
r["participants"][1]["role"] = "left"
check(bad, False, "Explicit source orientation cannot silently reverse")
bad = copy.deepcopy(pilot)
o = bad["recipes"][0]["local_observations"][0]
o["response"]["rows"] = [{"n": True}]
o["response_sha256"] = a.digest(o["response"])
o["metric"]["value"] = 1
check(bad, False, "Boolean result is not an integer measurement")
bad = copy.deepcopy(pilot)
bad["recipes"][0]["source_assertions"][0]["reported_date"] = "2026-06-14"
check(bad, False, "Count date cannot replace source status date")
reordered = copy.deepcopy(mixed)
reordered["assessments"].reverse()
assert a.search(reordered, ds, rs, rev)["view_revision"] == first["view_revision"]
returned = a.search(pilot, ds, rs, rev)
returned["entries"][0]["record"]["participants"].clear()
assert len(pilot["recipes"][0]["participants"]) == 2
passed.append("Stable top-level order and copy-on-return")

manifest = json.loads((a.PROFILE / "manifest.json").read_text())
for name, sha in manifest["artifacts"].items():
    assert hashlib.sha256((a.PROFILE / name).read_bytes()).hexdigest() == sha
for name, sha in manifest["dependencies"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
passed.append("Pinned artifacts and dependencies")
print(json.dumps({"passed": len(passed), "checks": passed}, indent=2))
