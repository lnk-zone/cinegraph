# CineGraphAgent System Architecture

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Web UI  │  Mobile App  │  CLI Tool  │  External APIs  │  WebSocket    │
│          │              │            │                 │  Clients      │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          │ HTTP/WebSocket
                          │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                    FASTAPI SERVICE LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │   API Gateway   │  │  Auth Service   │  │  WebSocket Manager     │  │
│  │   (Routing)     │  │   (Supabase)    │  │   (Event Streaming)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  Validation     │  │   Orchestration │  │     Logging &          │  │
│  │  Enforcement    │  │    Engine       │  │   Monitoring           │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
└─────────────────────────┬───────────────────────┬───────────────────────┘
                          │                       │
                          │                       │
            ┌─────────────▼─────────────┐        │
            │                           │        │
            │   CINEGRAPHAGENT         │        │
            │   (OpenAI Agent SDK)      │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Natural Language   │  │        │
            │  │    Interface        │  │        │
            │  └─────────────────────┘  │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Higher-Level      │  │        │
            │  │   Reasoning        │  │        │
            │  └─────────────────────┘  │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Alert Ranking &   │  │        │
            │  │  Prioritization    │  │        │
            │  └─────────────────────┘  │        │
            └─────────────┬─────────────┘        │
                          │                      │
                          │                      │
                          │                      │
            ┌─────────────▼─────────────┐        │
            │                           │        │
            │      GRAPHITI             │        │
            │      (Neo4j)              │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Graph Storage      │  │        │
            │  │   & Retrieval       │  │        │
            │  └─────────────────────┘  │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Temporal Reasoning │  │        │
            │  │   & Time Queries    │  │        │
            │  └─────────────────────┘  │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Entity Extraction  │  │        │
            │  │   & Management      │  │        │
            │  └─────────────────────┘  │        │
            │                           │        │
            │  ┌─────────────────────┐  │        │
            │  │  Contradiction      │  │        │
            │  │   Detection         │  │        │
            │  └─────────────────────┘  │        │
            └───────────────────────────┘        │
                                                 │
┌────────────────────────────────────────────────▼─────────────────────────┐
│                        EXTERNAL SERVICES                                 │
├───────────────────────────────────────────────────────────────────────────┤
│  Supabase Auth  │  Monitoring  │  Logging  │  Message Queue  │  Cache    │
│                 │   Services   │  Systems  │                 │  (Redis)  │
└───────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────┐    HTTP Request     ┌─────────────────────┐
│   Client    │ ──────────────────> │   FastAPI Service   │
│             │                     │      Layer          │
└─────────────┘                     └──────────┬──────────┘
                                               │
                                               │ Auth Check
                                               │
                                    ┌──────────▼──────────┐
                                    │   Supabase Auth     │
                                    │                     │
                                    └──────────┬──────────┘
                                               │
                                               │ Validated Request
                                               │
                                    ┌──────────▼──────────┐
                                    │  CineGraphAgent     │
                                    │                     │
                                    │  • NL Processing    │
                                    │  • Reasoning        │
                                    │  • Alert Ranking    │
                                    └──────────┬──────────┘
                                               │
                                               │ Graph Operations
                                               │
                                    ┌──────────▼──────────┐
                                    │     Graphiti        │
                                    │                     │
                                    │  • Storage          │
                                    │  • Temporal Logic   │
                                    │  • Entity Extraction│
                                    │  • Contradiction    │
                                    └──────────┬──────────┘
                                               │
                                               │ Response Data
                                               │
                                    ┌──────────▼──────────┐
                                    │   FastAPI Service   │
                                    │                     │
                                    │  • Format Response  │
                                    │  • Log Activity     │
                                    │  • Send WebSocket   │
                                    └──────────┬──────────┘
                                               │
                                               │ HTTP Response
                                               │
┌─────────────┐    Response Data     ┌─────────▼───────────┐
│   Client    │ <──────────────────── │   FastAPI Service   │
│             │                      │      Layer          │
└─────────────┘                      └─────────────────────┘
```

## Component Interaction Patterns

### 1. Request Processing Flow
```
Client → FastAPI → Auth → Validation → CineGraphAgent → Graphiti → Response
```

### 2. Event Streaming Flow
```
Graphiti → Event → FastAPI WebSocket → Client Real-time Updates
```

### 3. Contradiction Detection Flow
```
New Data → Graphiti → Contradiction Check → Alert → CineGraphAgent → Ranking → FastAPI → Client
```
