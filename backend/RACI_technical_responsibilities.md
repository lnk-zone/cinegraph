# RACI Chart: Technical Responsibilities

## Component-Level RACI Matrix

### Legend
- **R** = Responsible (does the work)
- **A** = Accountable (ensures completion)
- **C** = Consulted (provides input)
- **I** = Informed (kept updated)

| Technical Responsibility | Graphiti (Neo4j) | CineGraphAgent | FastAPI Layer | External Services |
|--------------------------|------------------|----------------|---------------|-------------------|
| **Data Storage & Retrieval** | R | C | A | I |
| **Graph Query Processing** | R | C | A | I |
| **Temporal Reasoning** | R | C | I | I |
| **Entity Extraction** | R | C | I | I |
| **Relationship Mapping** | R | C | I | I |
| **Contradiction Detection** | R | C | I | I |
| **Natural Language Processing** | I | R | A | C |
| **Intent Recognition** | I | R | A | C |
| **Higher-Level Reasoning** | C | R | A | I |
| **Alert Ranking** | C | R | A | I |
| **Alert Prioritization** | C | R | A | I |
| **Context Understanding** | C | R | A | I |
| **API Request Routing** | I | C | R | A |
| **Authentication** | I | C | R | A |
| **Authorization** | I | C | R | A |
| **WebSocket Management** | I | C | R | A |
| **Event Streaming** | I | C | R | A |
| **Request Validation** | I | C | R | A |
| **Response Formatting** | I | C | R | A |
| **Logging & Monitoring** | I | I | R | A |
| **Error Handling** | I | C | R | A |
| **Rate Limiting** | I | I | R | A |
| **Security Enforcement** | I | I | R | A |

## Detailed Component Responsibilities

### Graphiti (Neo4j) - Data Layer
**PRIMARY ROLE**: Data storage and primitive operations

| Function | Responsibility Level | Details |
|----------|---------------------|---------|
| Graph Storage | **Responsible** | Persist nodes, relationships, and properties |
| Temporal Queries | **Responsible** | Handle time-based graph queries and reasoning |
| Entity Extraction | **Responsible** | Extract and structure entities from raw data |
| Contradiction Detection | **Responsible** | Identify conflicting information in the graph |
| Data Consistency | **Responsible** | Maintain ACID properties and data integrity |
| Graph Algorithms | **Responsible** | Execute graph traversal and analysis algorithms |

### CineGraphAgent (OpenAI Agent SDK) - Intelligence Layer
**PRIMARY ROLE**: Natural language processing and cognitive reasoning

| Function | Responsibility Level | Details |
|----------|---------------------|---------|
| NL Understanding | **Responsible** | Parse and understand natural language queries |
| Intent Classification | **Responsible** | Determine user intent from natural language |
| Reasoning Engine | **Responsible** | Perform complex logical reasoning operations |
| Alert Ranking | **Responsible** | Rank alerts by importance and relevance |
| Context Management | **Responsible** | Maintain conversation context and state |
| Response Generation | **Responsible** | Generate natural language responses |

### FastAPI Service Layer - Orchestration Layer
**PRIMARY ROLE**: System coordination and external interface

| Function | Responsibility Level | Details |
|----------|---------------------|---------|
| Request Orchestration | **Responsible** | Coordinate requests between components |
| Authentication | **Responsible** | Integrate with Supabase auth system |
| API Gateway | **Responsible** | Route requests to appropriate handlers |
| WebSocket Management | **Responsible** | Manage real-time connections |
| Event Streaming | **Responsible** | Handle event distribution |
| Validation | **Responsible** | Validate input/output data |
| Logging | **Responsible** | Log system activities and errors |
| Monitoring | **Responsible** | Health checks and performance monitoring |

## Interface Contracts

### Graphiti ↔ CineGraphAgent Interface
```
- Graph queries (Cypher-like)
- Entity extraction requests
- Temporal reasoning queries
- Contradiction detection results
- Structured data responses
```

### CineGraphAgent ↔ FastAPI Interface
```
- Natural language requests
- Processed intelligence responses
- Alert rankings and priorities
- Context state management
- Reasoning results
```

### FastAPI ↔ External Services Interface
```
- Authentication tokens (Supabase)
- WebSocket connections
- Event streams
- Validation schemas
- Logging data
```

## Decision Making Authority

### Data Architecture Decisions
- **Accountable**: Graphiti component owner
- **Responsible**: Data architecture team
- **Consulted**: CineGraphAgent team, FastAPI team

### AI/ML Algorithm Decisions
- **Accountable**: CineGraphAgent component owner
- **Responsible**: AI/ML team
- **Consulted**: Data team, Product team

### API Design Decisions
- **Accountable**: FastAPI component owner
- **Responsible**: Backend team
- **Consulted**: Frontend team, DevOps team

### Security Decisions
- **Accountable**: Security team
- **Responsible**: All component teams
- **Consulted**: DevOps team, Compliance team
