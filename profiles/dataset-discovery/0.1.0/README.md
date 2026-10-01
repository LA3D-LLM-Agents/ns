# Dataset discovery profile 0.1.0

Review candidate for independently discovering scientific knowledge graphs through
existing services. This adds a JSON contract and supplementary SHACL constraints;
it does not revise eco 0.3.0, its published aliases, or any existing release file.
The proposed immutable publication location is this versioned directory. Until
merged and deployed, its URLs are proposed identifiers, not published artifacts.

## Identity and model

A dataset has a stable local `id` and HTTPS `iri`; a separate `named_graph` records
the query graph even if it currently equals the dataset IRI. Dataset IDs are scoped
to the registry. Graph IRIs are identifiers, not endpoints to fetch. An upstream
IRI change requires explicit review, not silent reassignment of an existing ID.

The RDF projection types scientific datasets as `dcat:Dataset` and
`eco:Participant`. The service is the existing `eco:Connector`/`dcat:DataService`,
linked to each dataset with `dcat:servesDataset`. Its MCP endpoint stays separate.
This participant typing is intentional: `eco:hasSemanticEntrypoint` has that
domain. Datasets are neither wiki Bundles, Agents, Connectors nor service endpoints.
No new eco class, property, inverse, or domain change is introduced.

The reference example describes RuralKG and RDKG sharing one OKN service. Its
observations and version-tool arguments are **synthetic fixtures**, not a live
harvest or evidence of present upstream availability. Implementation must inspect
current MCP tool schemas before preparing production records.

## JSON contract

`schema.json` is Draft 2020-12. The envelope contains `profile_version: "0.1.0"`
and at most 1,000 dataset records. An empty registry is valid. Objects are closed.
Each record requires:

- id, iri, label, description, kind (`knowledge-graph`), named_graph and tags;
- one to sixteen access_bindings, each naming an existing resource_id and source
  shortname, one or more semantic inspections, and a version inspection;
- provenance with a curator and one or more timestamped source observations.

Tool references have exact `tool_name` and fixed `arguments`. Arguments are bounded
flat JSON objects of scalar values, deliberately excluding arrays/nested objects
in this initial profile. They are suggested calls, never permission grants.
The resource/tool allowlist and MCP's own argument schema remain authoritative.
No endpoint routing, credentials or policy expansion belongs in dataset records.
No schema can identify a secret disguised as an otherwise valid string: curators
must emit public metadata only. Do not dereference source or graph URLs during
validation. Standard JSON forbids NaN/Infinity; loaders must reject them.

An observation source is either a public HTTPS URL or a resource/tool invocation.
`observed_at` is an RFC 3339 timestamp and an optional payload_sha256 identifies
retained source bytes. Optional source_version and loaded_at each require their
own observation. Absent source version means unknown. Neither service build,
resource revision, dataset registry revision nor observation time is a graph
release version; loaded_at is not a dataset modification date.

Use JSON Schema **with format assertions enabled**. The test dependencies install
`jsonschema[format-nongpl]`, and the reference validator supplies FormatChecker.
Format checking must not silently become annotation-only in another implementation.

JSON Schema cannot express all cross-record relations. The reference validator
also rejects duplicate local IDs/IRIs, duplicate bindings to the same resource,
conflicting dataset identities for the same (resource, named_graph), missing
resources and unapproved inspection/observation tools. Multiple services may
serve the same dataset through separate bindings. Resource descriptors supplied
to the validator are trusted, already validated operator inputs, not dataset-
controlled routing. Changing identities over time requires a previous-registry
comparison in the future production loader; stateless validation cannot prove it.

## RDF projection and validation

Load the pinned eco 0.3.0 ontology, its discovery shapes, and `shapes.ttl` together.
Use RDFS inference for validation; tests also run OWL-RL to inspect inferred roles.
No remote ontology imports are required. `manifest.json` records dependency and
artifact digests for reproducible pinning after publication.

The supplementary shapes cover all served datasets and all non-wiki dcat:Dataset
nodes in the supplied graph. Wiki Bundles retain the base discovery constraints;
a wiki explicitly used as a served scientific dataset fails this profile. To
validate other dataset kinds, use a separately agreed profile rather than apply
these knowledge-graph constraints indiscriminately.

Checks include a serving connector, dataset identity/title/description, optional
version, inspection entrypoint, and a resource-side MCP route owned by a connector
serving that dataset. A connector may also expose other endpoint types. Dataset
identifiers must be unique. Duplicate source IRIs merge in RDF, so JSON validation
must precede projection; RDF alone cannot recover conflicting original records.

`examples/datasets/adapter.py` is an offline reference validator and mapper, not
the future fabric implementation. It retains all metadata in the JSON source and
projects dataset identity/labels/tags/observed version, servesDataset relations,
and semantic tool/endpoint links. It does **not** project named-graph selectors,
source shortnames, fixed tool arguments, version-inspection calls, curator details,
or observation records into RDF. In particular, the RDF projection cannot be used
alone to construct a parameterized invocation. These remain authoritative in JSON;
there is no round-trip claim and no invented RDF invocation vocabulary.

## Validation and publication

From the repository root:

```sh
uv run --with-requirements tests/requirements.txt python tests/validate.py
uv run --with-requirements tests/requirements.txt python tests/agent_cards.py
uv run --with-requirements tests/requirements.txt python tests/datasets.py
```

The dataset suite exercises positive records, generated negative fixture variants,
combined resource/wiki/agent/dataset graphs, role inference, missing and conflicting
metadata, provenance and routes. These are offline contract tests, not upstream
query or production-deployment evidence. CI runs all three suites for profile changes.

Review and merge through a namespace PR. After Pages deployment, verify artifact
bytes against the manifest before fabric pins this profile in the registry step.
Versioned artifacts become immutable at publication; incompatible revisions need
a new profile version. Existing eco aliases/releases remain byte-identical.

See [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) for the standard dataset/service
relationship and the [repository README](../../../README.md) for eco boundaries.
