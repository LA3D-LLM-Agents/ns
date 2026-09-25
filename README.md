# eco: discovery ontology — 0.3.0

Canonical vocabulary: https://la3d-llm-agents.github.io/ns/eco.ttl

Term namespace: `https://la3d-llm-agents.github.io/ns/eco#`

Pinned release: https://la3d-llm-agents.github.io/ns/versions/0.3.0/eco.ttl

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

## Earlier discovery additions (0.2.0)

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

The 0.2 terms and controlled values are retained, with the card modeling changes documented below. `hasCapability` is intentionally
less restrictive; consumers relying on its old Connector inference should select
Connector explicitly. `requiresCredential`, CredentialRequirement and trustedIssuer
retain their original **verifiable credential** semantics. `requiresAccess` is a
separate relation for ordinary access prerequisites, not a grant or proof that a
caller possesses credentials. Missing prerequisites mean unknown, not anonymous.
The profile accepts missing maturity: discovery must not fabricate trust metadata.
Legacy authority/visibility vocabulary is retained; no new policy is adopted here.

## Validation profile

- `eco-discovery-shapes.ttl`: the new discovery-only profile, also pinned under
  `versions/0.3.0/`. Checks stable participant/capability IRIs, original capability
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
.venv/bin/python tests/agent_cards.py
```

Eight discovery ASK queries, agent-card mapping checks, inverse audits, OWL role-separation checks, and malformed-descriptor tests cover
this release. No network or source-data queries occur during validation. The
GitHub workflow repeats these checks for namespace changes. GitHub Pages publishes
from main; local validation precedes release pushes.

## Adoption

Updating this ontology does not alter deployed discovery snapshots. Consumers
should pin 0.3.0 and migrate descriptor-to-RDF mappings explicitly, preserving
existing resource IDs, direct-access routing and client permission restrictions.
Capability IDs and descriptions should come from the publisher; tags remain
keywords. Advertising a capability is distinct from local connector support and
per-user authorization. Do not equate a hosted resource with its publisher DID,
or infer a live A2A endpoint from an agent card.


## Agent cards and inverse relationships (0.3.0)

The card is a **document describing an agent**. It can remain a Markdown/YAML page
in the project's wiki. The publication location does not make its subject a Bundle.
Agent is a Participant and PROV SoftwareAgent; AgentSession is a PROV Activity.
hasKnowledgeBundle relates the agent to separately identified published knowledge.
The schema does not create a separate project entity; project-scoped agent IDs can
remain owner/repository IDs while graph identities use escaped stable URNs.

AgentCard now subclasses PROV Entity, **not ServiceEndpoint**. hasCard/describesAgent
links it to Agent. Its URL uses documentURL, whose old SemanticEntrypoint domain
was removed to avoid inferring that card documents are source semantic entrypoints.
This is an intentional semantic change, not an additive-only release.
No global Agent/Bundle/Connector disjointness is asserted: correct explicit
multiple roles are possible, but publication location alone must not infer them.

A2AEndpoint means an explicitly advertised task-invocation interface, with URL,
transport and protocol version metadata. It is distinct from MCPEndpoint,
CloneEndpoint and the card document. These structural checks do not certify an
official A2A wire-protocol implementation. The proposed wiki-card schema is an
llm-wiki enrollment format, not an official A2A JSON AgentCard schema.

### Concrete example and migration

- [Proposed wiki card](examples/Card_llm-wiki-fabric.md) uses a versioned
  x-fabric-card frontmatter block with agent identity, four structured skills,
  a separate knowledge bundle and clone-and-invoke interface.
- [JSON Schema](examples/agent-card.schema.json) validates that block;
  additional parser checks enforce unique skill/bundle/interface IDs and valid
  bundle references. YAML is serialized safely, including punctuation.
- [Mapped RDF](examples/agent-card.ttl) is checked against the executable example
  adapter in tests/agent_cards.py. It preserves skill IDs, names, descriptions,
  grouped tags and the card's publication URL.
- The real project card, enrollment generator, federation index and hosted fabric
  have **not** been migrated by this namespace release. The sample is a proposed
  replacement, not a published enrollment or a claim of live invocation testing.

For 0.2 graphs: replace participant hasService card with agent hasCard card;
replace card serviceURL with documentURL; add describesAgent, card format/version
and explicit agent identity. Do not mechanically convert a Bundle into Agent:
retain the bundle and link a distinct agent with hasKnowledgeBundle when warranted.
Legacy endpoint-shaped card assertions are rejected by the 0.3 discovery profile,
so they must not be dual-written into the same graph.

The hosted fabric remains pinned to **0.2.0** until an explicit runtime migration.
Both immutable 0.2.0 files remain unchanged. Legacy eco-shapes.ttl also remains
unchanged and is not combined with the new profile. Enrollment/index migration
should accept both card formats at the boundary, translating each to one canonical
graph representation.

### Inverse policy and complete audit

A missing named inverse is not inherently an error. Every object property is
accounted for by tests/inverse-audit.json: 14 inverse pairs and five facets without
named inverses. Datatype properties (literal strings, URLs, booleans) do not have
OWL object-property inverses.

| Relationship | Inverse | Reverse question |
| --- | --- | --- |
| hasCapability | providedBy | Who advertises this capability? |
| hasCard | describesAgent | Which agent does this document describe? |
| hasKnowledgeBundle | knowledgeBundleOf | Which agents reference this knowledge bundle? |
| sessionOfAgent | hasSession | Which sessions are associated with this agent? |
| hasService | serviceOf | Which participants advertise this binding? |
| memberOf | hasMember | Which participants belong to this federation? |
| hasSemanticEntrypoint | semanticEntrypointOf | Which participants expose these semantics? |
| hasOntology | ontologyOf | Which participants link this ontology? |
| invokedThrough | exposesSemanticEntrypoint | Which semantic tools use this MCP binding? |
| requiresAccess | requiredFor | Which participants advertise this prerequisite? |
| reachableVia | providesRouteTo | Which connectors use this broker? |
| filedInto | containsAnswer | Which answers are filed into this bundle? |
| requiresCredential | credentialRequiredBy | Which capabilities require this VC condition? |
| trustedIssuer | trustedForRequirement | Which VC requirements trust this issuer? |

hasMaturity, hasVisibility, consumptionMode, executionLocation and accessMechanism
remain classification facets. Reverse lookup uses their existing predicates;
a second name adds no distinct discovery meaning. Broad inverse coverage does not
activate legacy answer provenance, VC enforcement, or telemetry functionality.

Tests check both directions of every declared pair and mirrored domain/range.
ontologyOf specializes semanticEntrypointOf consistently with the forward
subproperty hierarchy. AccessRequirement shapes accept the typed requiredFor
inverse while continuing to reject extra credential fields.

Authors supply canonical forward fields. The **example adapter** expands only
declared inverse pairs into a copied graph before RDFS/SHACL validation. This is
explicit, bounded and idempotent; declaring owl:inverseOf alone does not populate
an RDFLib graph. Separate OWL-RL tests exercise type effects. Ordinary consumers
may instead use reverse SPARQL patterns; production materialization is still a
runtime implementation task. Dashboard rendering should avoid duplicate visual
edges if forward/inverse assertions are both stored.

### Validation evidence

The offline suite checks six agent discovery questions, all 14 inverse pairs in
both directions, eight malformed card/schema/agent variants and synthetic explicit
MCP/A2A advertisements. The original eight discovery ASK questions and ten negative
discovery fixtures also pass against 0.3. No source data was queried. Test results
establish structural mapping behavior, not successful enrollment, authentication,
live A2A execution or a deployed fabric migration.
