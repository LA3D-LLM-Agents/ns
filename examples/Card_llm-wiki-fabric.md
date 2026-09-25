---
type: agent
up: '[[Home_llm-wiki-fabric]]'
x-fabric-card:
  schema_version: '1.0'
  id: chrissweet/llm-wiki-fabric
  name: Fabric project agent
  description: Explains and maintains the llm-wiki fabric discovery architecture and
    recorded integrations.
  card_url: https://github.com/chrissweet/llm-wiki-fabric/wiki/Card_llm-wiki-fabric
  skills:
  - id: explain-fabric
    name: Explain fabric discovery
    description: Explain descriptor-driven discovery and direct resource access.
    tags:
    - fabric
    - discovery
  - id: maintain-fabric
    name: Maintain fabric integrations
    description: Document hosted discovery and direct resource connectors.
    tags:
    - mcp
    - operations
  - id: explain-validation
    name: Explain recorded validation
    description: Answer questions about recorded PAD and rare-disease integration
      checks.
    tags:
    - pad
    - rare-disease
  - id: explain-dashboard
    name: Explain the resource dashboard
    description: Explain graph relationships and dashboard deployment.
    tags:
    - graph
    - dashboard
  knowledge_bundles:
  - id: project-wiki
    url: https://github.com/chrissweet/llm-wiki-fabric/wiki
  interfaces:
  - id: wiki-ask
    kind: clone-and-invoke
    url: https://github.com/chrissweet/llm-wiki-fabric.wiki.git
    bundle_id: project-wiki
---

# Fabric project agent — proposed card

Schema example only, not a newly published enrollment. The card stays in the project wiki.
The clone-and-invoke interface describes the wiki ask route. The hosted fabric MCP
service is a separate discovery resource; it is not this agent’s A2A task endpoint.
