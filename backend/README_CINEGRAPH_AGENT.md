# CineGraphAgent OpenAI SDK Integration

This document outlines the implementation of Step 7 of the CineGraph project: **Integrate CineGraphAgent (OpenAI Agent SDK)**.

## Overview

The CineGraphAgent is an AI-powered agent that uses OpenAI's SDK for story analysis, consistency validation, and temporal reasoning. It integrates with the knowledge graph via GraphitiManager and handles real-time alerts through Redis and Supabase.

## Features Implemented

### 1. Tool Schema Definition
- **graph_query**: Executes Cypher queries via GraphitiManager
- **narrative_context**: Returns raw scene text for analysis

### 2. System Prompt with Temporal Examples
- Specialized system prompt for story analysis and consistency validation
- Temporal query examples (e.g., "What did X know at Y?")
- Few-shot examples for improved agent performance

### 3. Core Agent Methods
- `analyze_story()`: Analyzes story content using OpenAI SDK
- `detect_inconsistencies()`: Detects story inconsistencies with AI reasoning
- `query_story()`: Answers natural language questions about stories
- `validate_story_consistency()`: Comprehensive story validation

### 4. Redis Alerts Integration
- Listens to Redis "alerts" channel for contradiction notifications
- Enriches alerts with AI-generated explanations and severity levels
- Stores enriched alerts in Supabase realtime table

## File Structure

```
backend/
├── agents/
│   ├── cinegraph_agent.py      # Main agent implementation
│   ├── agent_factory.py        # Factory for creating agents
│   └── __init__.py
├── examples/
│   └── cinegraph_agent_example.py  # Usage examples
├── tests/
│   └── test_cinegraph_agent.py     # Unit tests
├── sql/
│   └── create_alerts_table.sql     # Supabase table schema
├── test_agent.py                   # Simple test script
└── README_CINEGRAPH_AGENT.md      # This file
```

## Environment Variables Required

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# Neo4j Aura Configuration
NEO4J_URI=your_neo4j_uri_here
NEO4J_USERNAME=your_neo4j_username_here
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Installation

1. Install required dependencies:
```bash
pip install openai-agents graphiti-core supabase redis celery
```

2. Set up the Supabase alerts table:
```sql
-- Run the SQL script in sql/create_alerts_table.sql
```

3. Configure your environment variables in `.env`

## Usage

### Basic Usage

```python
from agents.agent_factory import create_cinegraph_agent, initialize_cinegraph_agent

# Create and initialize agent
agent = create_cinegraph_agent()
agent = await initialize_cinegraph_agent(agent)

# Analyze a story
story_content = "Your story content here..."
extracted_data = {"story_id": "story_001", "entities": [...]}
analysis = await agent.analyze_story(story_content, extracted_data)

# Query the story
response = await agent.query_story("story_001", "What happened to the character?")

# Detect inconsistencies
inconsistencies = await agent.detect_inconsistencies("story_001")
```

### Running Tests

```bash
# Run the simple test
python test_agent.py

# Run comprehensive examples
python examples/cinegraph_agent_example.py

# Run unit tests
pytest tests/test_cinegraph_agent.py
```

## Key Components

### CineGraphAgent Class

The main agent class that:
- Integrates with OpenAI SDK for AI-powered analysis
- Uses GraphitiManager for knowledge graph operations
- Handles Redis alerts for real-time contradiction detection
- Stores enriched alerts in Supabase for real-time updates

### Tool Functions

1. **graph_query(cypher_query, params)**: Executes Cypher queries
2. **narrative_context(story_id, scene_id)**: Retrieves scene text

### Redis Alert Handler

- Listens to Redis "alerts" channel
- Enriches alerts with AI explanations
- Assesses severity levels automatically
- Stores in Supabase realtime table for frontend consumption

## System Prompt Features

The agent uses a specialized system prompt that includes:
- Tool definitions and usage examples
- Temporal query patterns
- Consistency validation guidelines
- Few-shot examples for common tasks

## Error Handling

The agent includes comprehensive error handling:
- Connection failures to external services
- OpenAI API errors
- GraphitiManager query failures
- Redis/Supabase integration issues

## Health Checks

The agent provides health check functionality:
- Tests OpenAI connection
- Verifies Supabase connectivity
- Checks GraphitiManager status
- Monitors Redis alert listener

## Future Enhancements

1. **Enhanced Tool Schema**: Add more specialized tools for complex story analysis
2. **Batch Processing**: Support for analyzing multiple stories simultaneously
3. **Custom Models**: Integration with fine-tuned models for story-specific tasks
4. **Advanced Alerts**: More sophisticated alert classification and routing
5. **Performance Optimization**: Caching and connection pooling improvements

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Connection Failures**: Check environment variables and service availability
3. **OpenAI API Errors**: Verify API key and usage limits
4. **Neo4j Connection**: Ensure Aura instance is running and accessible

### Debug Mode

Enable debug logging by setting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Architecture

The CineGraphAgent follows a modular architecture:
- **Agent Layer**: OpenAI SDK integration and reasoning
- **Tool Layer**: GraphitiManager and narrative context tools
- **Data Layer**: Neo4j knowledge graph and Supabase storage
- **Communication Layer**: Redis pub/sub for real-time alerts

This implementation provides a robust foundation for AI-powered story analysis and consistency validation in the CineGraph system.
