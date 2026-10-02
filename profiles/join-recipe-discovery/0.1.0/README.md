# Join-recipe discovery profile 0.1.0

Review candidate for qualified join plans, source assessments and execution
observations. This directory is a proposed immutable publication unit. Its URLs
are proposed identifiers until PR merge and Pages publication. Published eco
0.3.0 and dataset-discovery 0.1.0 artifacts remain unchanged.

## Contract and semantic boundary

`schema.json` is a closed Draft 2020-12 registry contract; `search.schema.json`
is the mixed-entry search response contract. Format assertions are required.
Use the reference semantic validator as well as JSON Schema: hashes, graph scope,
references and measurement consistency cannot all be expressed in JSON Schema.

The registry has `profile_version`, `coverage: reviewed_subset`, `recipes` and
`assessments`. Each collection is bounded to 100 entries and total input to 2 MB.
Templates have a 64 KB UTF-8 byte limit (JSON Schema also bounds character length).
Each recipe has at most five distinct fixed SELECT templates and twenty local
observations/source assertions. Compaction or deletion is an explicit operator
review, not a side effect of loading. Production parsers must reject duplicate
mapping keys, aliases and non-JSON values before validation; the reference adapter
accepts already parsed JSON-native objects and does not implement a YAML loader.

Recipe identity, description, role-bearing participants, selection method,
ordered descriptive transformations, exact template bytes/digests, execution
binding, provenance, source assertions and local observations are independent
fields. Participants require one left and one right; any bridge must refer to
another declared dataset. An unordered pair search never reverses these roles.
Methods distinguish exact identifiers, normalization, directional taxonomy,
exact labels and other methods. These are classifications, not equivalence proofs.

Every dataset ID/IRI/named graph must match the supplied validated dataset registry.
All participants must be accessible through the declared single resource, and the
execution/source tools must belong to its operator-approved allowlist. This profile
supports `get_join_strategy(kg_a, kg_b)` evidence and `sparql_query(query, ...)`
execution metadata. Other publishers/tool contracts require a future profile.
Fixed arguments cannot replace the query. MCP input schemas and local policy remain
authoritative at invocation time. No URLs are fetched and no tool/query is executed.

### Source claims are not local execution results

Source assertions and standalone assessments use `verified`, `known_non_join` or
`unknown`, attributed to retained upstream response bytes with a retrieval timestamp
and canonical JSON SHA-256. Unknown means the source has no precomputed recipe;
known_non_join includes its diagnostic scope and does not establish universal
impossibility. The raw source's original prose is retained as data, not executable
instructions. Additional upstream fields are preserved in this bounded raw payload;
they are not automatically translated into contract fields.

`reported_date` on a source status preserves its date-only precision. A claimed
count has a separate metric and optional date, plus its original note. The source
status date must match the payload's `verified_on`. The pilot's count note names
June 14, while the top-level status date is September 2; neither substitutes for
the recorded October execution. A date extracted by human review from a count note
belongs to the metric, not to the top-level assertion.

Local observations use `matches_observed`, `no_matches_for_query` or `inconclusive`.
A positive or zero COUNT result must match the retained one-row aggregate response,
variable/unit, template hash and exact arguments. Failures require an error code
and carry no fabricated count. Versions and schema digests are timestamped per
dataset; unknown versions are explicit null values. These are observations near a
run, not an assertion of atomic version-pinned source contents. Historical data is
not silently reassigned when a query or participant identity changes; archive the
old record and review its replacement explicitly.

This first profile accepts only SELECT queries with explicit absolute GRAPH IRIs
matching declared participants; FROM and SERVICE are rejected. It does not prove
query cost, safety of an arbitrary future executor, equivalence of descriptive
transformations to text, or that an annotated count measures its intended scientific
concept. Curator review remains necessary. A source-verified template must match
the identified upstream recipe's exact skeleton and left/right orientation.
The production verification command remains a later fabric implementation restricted
to the reviewed pilot digest; the namespace adapter is not that executor.

### Actual upstream status observations

`examples/join-recipes/evidence/` contains read-only get_join_strategy observations
from 2026-10-02, including tool input/output schemas:

- ruralkg/rdkg: `verified`, with the DrugBank skeleton.
- ruralkg/spoke-okn: `verified`, multiple geography methods, with source orientation
  opposite to the requested pair for those methods. This is why pair lookup must
  not rewrite recipe direction. These counts were not executed in this work.
- ruralkg/sawgraph: `unknown`, with explanatory note/island context, not joins.
- evoweb/rdkg: `known_non_join`, with `non_joins` diagnostic records, not templates.
  Some diagnoses are scoped to a KG/key family, not a fully enumerated pair test.
  Retain that scope; do not infer stronger pair-wide absence claims.

The raw non-pilot responses validate source status shapes only. No new datasets,
recipes or live negative conclusions for those graphs are enrolled here. The
normalized mixed-status example is explicitly **synthetic** and uses the existing
pilot dataset fixtures; it must never be published as a production finding.

`pilot.json` combines recent real metadata with the retained historical query at
2026-10-01T23:48:27.330925+00:00 (count 2). It does not claim a new query run.
The original count response and nearby schema/version digests are retained under
`evidence/historical-local-query.json`. No SPARQL was run while preparing this PR.

## RDF projection

The vocabulary namespace is
`https://la3d-llm-agents.github.io/ns/profiles/join-recipe-discovery/0.1.0/vocab#`.
Load `vocab.ttl`, the pinned eco ontology, and all three sets of SHACL shapes
(eco, dataset and recipe), with RDFS inference and no remote imports.

| JSON concept | RDF projection |
| --- | --- |
| Recipe | jr:Recipe, subclass of prov:Plan and jr:JoinRecord/prov:Entity |
| Standalone source assessment | jr:Assessment, subclass of jr:JoinRecord/prov:Entity |
| Dataset role | jr:Participation with jr:dataset and literal left/right/bridge role |
| Query artifact | jr:QueryTemplate with exact template digest |
| Source assertion | jr:SourceAssertion with scope, status, source digest and dates |
| Actual attempted execution | jr:ExecutionObservation, subclass of prov:Activity |
| Returned result or recorded error | jr:Result, prov:wasGeneratedBy the execution |

Executions prov:used their recipe, template and participant datasets. This avoids
misusing prov:hadPlan directly on an activity (its domain is prov:Association).
No executor/agent identity is fabricated from curator text. No inverse, symmetric
or transitive properties are declared; inverse paths in shapes are traversal
constraints, not asserted inverse vocabulary. Combined OWL-RL tests check that
recipes do not acquire dataset, participant, agent, connector or endpoint roles.

The projection is structural: query text, descriptive transformations, exact fixed
arguments, raw source response, detailed schemas/versions and revision values stay
in authoritative JSON. There is no RDF-to-execution round-trip claim. No dataset
owl:sameAs or unqualified canJoin statements are generated. SHACL validates scopes,
role cardinalities, service relationships, template ownership and outcome/result
consistency, but JSON validation must precede mapping because RDF merges identities.

## Mixed search contract and revisions

The offline reference `search` illustrates the agreed contract; it is not an MCP
server. The future tools are fabric_search_join_recipes/fabric_identify_join_recipe.

Search emits one `entries` array of `{entry_type, record}`, with either complete
recipe or complete assessment records. `total = recipe_total + assessment_total`;
returned/offset/next_offset apply to that single sequence. Sort by entry_type then
ID, with limit 1–100 and offset 0–5000. Keywords use case-insensitive AND matching
across ID/label/description/tags. Other filters are exact; a missing method cannot
match a requested method. A dataset alone matches any role, while a pair matches
only the unordered left/right endpoints. Bridges do not become endpoint pairs.

Coverage is always reviewed_subset. For pair searches, pair_state is cataloged or
not_cataloged, computed **before** keyword/method/resource filters. Thus a filtered
zero-result view is not mistaken for absence. Explicit unknown assessments are
entries; missing coverage never manufactures an unknown/no-join record.

recipe_registry_revision hashes canonical persisted registry records sorted by ID
within each collection. dataset_revision follows the same canonical dataset order.
Resource revision is supplied by the validated resource catalog. view_revision
hashes the profile version and these three revisions. Pagination rejects any changed
dependency; timestamps aging alone do not alter stored records/revisions. Return
copies to prevent client mutation. Whole source responses are hashed with sorted,
compact JSON, ensure_ascii=True and no NaN/Infinity. Template hashes cover exact
UTF-8 query bytes, including whitespace. These are not hashes of HTTP wire bytes.

Freshness thresholds and recheck reminders are deployment policies, not normative
claims about upstream validity. The reference adapter does not compute them or
refresh metadata. The planned fabric implementation must display source age,
last success and latest attempt separately and mark missing/future times unknown.

## Validation and adoption

Run all four suites from the namespace repository root:

```sh
uv run --with-requirements tests/requirements.txt python tests/validate.py
uv run --with-requirements tests/requirements.txt python tests/agent_cards.py
uv run --with-requirements tests/requirements.txt python tests/datasets.py
uv run --with-requirements tests/requirements.txt python tests/join_recipes.py
```

All four suites passed locally on 2026-10-02 using the pinned requirements; the
new recipe suite reports 54 checks. CI runs them. Recipe tests cover actual
positive/historical fixtures, explicit
synthetic zero/failure/status cases, malformed records, graph scope, hashes,
source direction, date scope, combined RDF role inference, mixed pagination and
revision invalidation. Tests do not contact upstream services. `manifest.json`
pins all four normative artifacts and unchanged eco/dataset dependencies.

Merge and verify published bytes before fabric pins this profile. Registry loading,
refresh/verification commands, new MCP tools and dashboard changes belong to later
fabric PRs; this namespace PR changes no deployed runtime or resource policy.

References: [PROV-O](https://www.w3.org/TR/prov-o/),
[SPARQL 1.1](https://www.w3.org/TR/sparql11-query/), and
[dataset profile](../../dataset-discovery/0.1.0/README.md).
