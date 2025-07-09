# Architecture Decision Record

## Title: Separation of Concerns in CineGraphAgent System

### Status
Accepted

### Context
The CineGraphAgent system is designed to provide advanced reasoning and alert ranking capabilities with a robust storage and processing backend. The architecture must ensure clear separation and definition of responsibilities among different components to enhance maintainability, scalability, and collaboration.

### Decision
A RACI chart is proposed to clearly define the roles and responsibilities across different components of the system:
- **Graphiti (Neo4j)**: Handles data storage, temporal reasoning, entity extraction, and contradiction detection.
- **CineGraphAgent (OpenAI Agent SDK)**: Manages natural language processing and higher-level reasoning with alert ranking.
- **FastAPI Service Layer**: Coordinates orchestration, authentication, WebSocket/event streaming, validation enforcement, and logging.

#### RACI Chart

| Component                  | Responsible          | Accountable         | Consulted               | Informed             |
|----------------------------|----------------------|---------------------|-------------------------|----------------------|
| Graphiti (Neo4j)           | Storage Team         | Data Architect      | DevOps Team             | Project Manager      |
| Temporal Reasoning         | Storage Team         | Data Architect      | Backend Engineers       | Project Manager      |
| Entity Extraction          | Storage Team         | Data Architect      | ML Team, Backend Team   | Project Manager      |
| Contradiction Detection    | ML Team              | Data Scientist      | Storage Team, Backend Team| Project Manager      |
| CineGraphAgent             | AI Team              | Chief AI Officer    | Backend Engineers       | Product Manager      |
| NL Interface               | AI Team              | Chief AI Officer    | UI/UX Team              | Product Manager      |
| Alert Ranking              | AI Team              | Chief AI Officer    | Domain Experts          | Product Manager      |
| FastAPI Orchestration      | Backend Team         | Lead Developer      | DevOps Team             | Project Manager      |
| Auth (Supabase)            | DevOps Team          | Security Officer    | Backend Team            | Project Manager      |
| WebSocket/Event Streaming  | Backend Team         | Lead Developer      | Frontend Team           | Project Manager      |
| Validation Enforcement     | Backend Team         | Lead Developer      | QA Team, DevOps Team    | Project Manager      |
| Logging                    | DevOps Team          | Lead Developer      | All Teams               | Project Manager      |

### Consequences
- **Advantages**: Better separation of responsibilities leads to improved code quality, maintainability, and collaboration.
- **Drawbacks**: Communication overhead may increase slightly to coordinate between teams.

### Related Documentation
- *Architecture Diagram*
- *Data Flow Diagram*

### Notes
This ADR will be revisited every 6 months to ensure it aligns with the ongoing project needs.
