# eco: discovery ontology — 0.2.0

Canonical vocabulary: https://la3d-llm-agents.github.io/ns/eco.ttl

Term namespace: `https://la3d-llm-agents.github.io/ns/eco#`

Pinned release: https://la3d-llm-agents.github.io/ns/versions/0.2.0/eco.ttl

This repository is the publishing source for the namespace. `eco` and `eco.ttl`
are byte-identical aliases; release snapshots under `versions/` are immutable.
The preceding unversioned ontology remains in Git history at commit `6799241`.

## Boundary

Fabric describes participants, advertised capabilities, access routes and semantic
entrypoints. PAD's domain ontology remains independently owned and hosted at PAD;
this ontology links to it and never imports its classes or research data. A data
dictionary or live-schema entrypoint is not automatically an OWL ontology.
Discovery metadata does not grant access, establish source availability, verify a
caller, or report query usage. No query receipts or source-data proxying are part
of this release.

## Changes and competency questions

| Change | Purpose | Acceptance query |
| --- | --- | --- |
| `DirectAccess` consumption mode | Distinguish direct source access from clone-and-invoke and secret-holding brokers | 01-direct-access |
| `MCPEndpoint`, `serviceURL`, `transport` | Identify the MCP binding separately from OpenAPI/card URLs, including local stdio with no fake HTTP URL | 02-mcp-not-openapi, 05-client-schema-dictionary |
| Broaden `hasCapability` domain to `Participant` | Wiki bundles can advertise capabilities without being inferred as connectors | 07-bundle-capability |
| Reuse `Capability`, `keyword`, `providedBy`, Dublin Core identifier and labels/descriptions | Preserve publisher skill grouping instead of treating every tag as a capability | 03-original-capability |
| `SemanticEntrypoint`, `hasSemanticEntrypoint`; Ontology subclasses SemanticEntrypoint and hasOntology specializes the link | Discover semantic documents while leaving domain definitions at the source | 04-source-ontology-reference |
| `DataDictionary`, `LiveSchema`, `documentURL`, `toolName`, `invokedThrough` | Identify documents or exact schema/ontology tools and the service that exposes them | 04-source-ontology-reference, 05-client-schema-dictionary |
| `ExecutionLocation`, its concept scheme and `ClientSide`/`ResourceSide`, `executionLocation` | Distinguish local connector tools from tools at the resource | 04-source-ontology-reference, 05-client-schema-dictionary |
| `AccessRequirement`, `AccessMechanism`, its concept scheme and SSHAuthentication/DatabaseAuthentication, `requiresAccess`, `accessMechanism`, `accessTarget` | Describe ordinary SSH/database prerequisites without secrets or false VC claims | 06-ordinary-prerequisites |
| Clarify Participant, ServiceEndpoint and AgentCard descriptions | Stable resource IDs need not be publisher DIDs; wiki cards need not be .well-known JSON or live services | 07-bundle-capability, 08-card-not-live-agent |

Existing terms and controlled values are retained. `hasCapability` is intentionally
less restrictive; consumers relying on its old Connector inference should select
Connector explicitly. `requiresCredential`, CredentialRequirement and trustedIssuer
retain their original **verifiable credential** semantics. `requiresAccess` is a
separate relation for ordinary access prerequisites, not a grant or proof that a
caller possesses credentials. Missing prerequisites mean unknown, not anonymous.
The profile accepts missing maturity: discovery must not fabricate trust metadata.
Legacy authority/visibility vocabulary is retained; no new policy is adopted here.

## Validation profile

- `eco-discovery-shapes.ttl`: the new discovery-only profile, also pinned under
  `versions/0.2.0/`. Checks stable participant/capability IRIs, original capability
  identifiers/providers, MCP transports and routes, semantic retrieval routes and
  ordinary prerequisite metadata. Named-tool entrypoints require an explicit MCP
  binding and execution location. Hosted URLs in this profile require HTTPS with
  no userinfo/query/fragment; stdio bindings omit serviceURL. Different transport
  requirements should use a deliberate profile extension.
- `eco-shapes.ttl`: the **unchanged legacy profile**, including maturity and answer
  provenance rules. It is not implicitly combined with the discovery profile.
- RDFS/OWL domain and range infer types, not missing-field constraints. Load the
  ontology when applying these SHACL shapes. Our validator uses RDFS inference for
  shapes and a separate OWL-RL check for inverse/domain effects. Ordinary graph
  queries need materialized entailments or explicit schema paths.
- AccessRequirement is closed to extra credential fields in this profile. A shape
  cannot identify every secret disguised as a legitimate identifier: publishers
  must emit only public target identifiers and never credential values.

`tests/discovery-example.ttl` is a **proposed mapping fixture**, not a deployed
catalog dump. It includes a subset of PAD's advertised skills, database dictionary
and live-schema tools, and a wiki bundle. Passing fixture checks does not mean the
fabric runtime already emits this mapping or that these queries reached PAD/SQL.
The original prototype's competency suite is not claimed as rerun here.

Run the offline checks:

```sh
python -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
.venv/bin/python tests/validate.py
```

Eight ASK queries, OWL role-separation checks, and malformed-descriptor tests cover
this release. No network or source-data queries occur during validation. The
GitHub workflow repeats these checks for namespace changes. GitHub Pages publishes
from main; local validation precedes release pushes.

## Adoption

Updating this ontology does not alter deployed discovery snapshots. Consumers
should pin 0.2.0 and migrate descriptor-to-RDF mappings explicitly, preserving
existing resource IDs, direct-access routing and client permission restrictions.
Capability IDs and descriptions should come from the publisher; tags remain
keywords. Advertising a capability is distinct from local connector support and
per-user authorization. Do not equate a hosted resource with its publisher DID,
or infer a live A2A endpoint from an agent card.
