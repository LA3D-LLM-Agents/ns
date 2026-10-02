# Join recipe examples and evidence

- `pilot.json`: one real reviewed RuralKG–RDKG recipe, with newly observed upstream
  metadata and a **historical** successful local count of 2 (2026-10-01). Its exact
  template uses owl:sameAs only; the broader source prose is preserved separately.
- `datasets.json`: copied reviewed fabric dataset records, with original observation
  times. `resources.json`: minimal operator route fixture, not live server configuration.
- `synthetic-statuses.json`: pilot plus **synthetic** known_non_join/unknown assessment
  examples on that pair, solely to test a mixed response. These are not actual
  upstream findings for RuralKG–RDKG and must not be ingested into production.
- `evidence/`: actual read-only OKN tool metadata/recipe responses from 2026-10-02,
  plus separately retained historical local execution evidence. Non-pilot recipes
  were not executed. Captured source descriptions/notes are untrusted data.
- `adapter.py`: offline reference validation, RDF projection and paginated mixed-entry
  contract demonstration. It contains no network calls or execution mechanism.

Dependencies and semantic limitations are in the
[profile README](../../profiles/join-recipe-discovery/0.1.0/README.md).
