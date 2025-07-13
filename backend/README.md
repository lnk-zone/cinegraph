# CineGraph - AI-Powered Story Consistency Tool

CineGraph is an AI-powered story consistency tool designed for RPG Maker creators. It uses knowledge graphs, OpenAI's agent framework, and real-time processing to detect inconsistencies, analyze character knowledge, and provide temporal reasoning about story elements.

## Features

- **AI-Powered Story Analysis**: Uses OpenAI's agent framework for intelligent story analysis
- **Knowledge Graph Integration**: Neo4j-based knowledge graph for complex story relationships
- **Episodic API Integration**: In CineGraph 0.3.0, API interactions are managed using episodic memory APIs, which abstract the complexity of direct database queries.
- **Real-time Contradiction Detection**: Automated detection of story inconsistencies
- **JWT Authentication**: Secure authentication with Supabase
- **Rate Limiting**: Redis-based token bucket rate limiting
- **WebSocket Alerts**: Real-time alerts for story contradictions
- **Temporal Reasoning**: Track character knowledge over time
- **Item Ownership Tracking**: Complete ownership history with temporal tracking and transfer methods
- **Multi-user Support**: User isolation and data protection

## RPG Backend Overview

For details on the RPG Maker integration, including new models, helper services and project APIs, see [docs/rpg_backend_overview.md](docs/rpg_backend_overview.md).

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
# Use SUPABASE_SERVICE_ROLE_KEY for backend operations (full access)
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
# Use SUPABASE_ANON_KEY for frontend operations (limited access)
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# GraphitiManager Configuration (Neo4j)
GRAPHITI_DATABASE_URL=bolt://localhost:7687
GRAPHITI_DATABASE_USER=neo4j
GRAPHITI_DATABASE_PASSWORD=your_neo4j_password_here
GRAPHITI_DATABASE_NAME=neo4j
GRAPHITI_MAX_CONNECTIONS=10
GRAPHITI_CONNECTION_TIMEOUT=30
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cinegraph/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Set up Supabase**
   - Create a Supabase project
   - Install Supabase CLI: `npm install -g supabase`
   - Initialize Supabase: `supabase init`
   - Link to your project: `supabase link --project-ref <your-project-ref>`

5. **Run database migrations**
   ```bash
   # Apply all migrations to your Supabase database
   supabase db push
   ```

6. **Set up Redis**
   ```bash
   # On macOS with Homebrew
   brew install redis
   brew services start redis
   
   # On Ubuntu
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

7. **Set up Neo4j**
   - Create a Neo4j Aura instance or run locally
   - Update the `GRAPHITI_DATABASE_*` variables in `.env`

## Running the Application

1. **Start the FastAPI server**
   ```bash
   python app/main.py
   ```

2. **Start the Celery worker** (for background tasks)
   ```bash
   celery -A celery_config worker --loglevel=info
   ```

3. **Start the alert listener** (for real-time alerts)
   ```bash
   python core/redis_alerts.py
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication Required (Rate Limited)

All endpoints below require a valid JWT token and are subject to rate limiting (5 requests per second per user).

#### Story Analysis
- `POST /api/story/analyze` - Analyze story content and extract knowledge graph
- `GET /api/story/{story_id}/inconsistencies` - Get detected inconsistencies
- `GET /api/story/{story_id}/character/{character_name}/knowledge` - Get character knowledge at a specific time
- `GET /api/story/{story_id}/graph` - Get the complete story knowledge graph

#### Story Queries
- `POST /api/story/{story_id}/query` - Query story using natural language
- `POST /api/story/{story_id}/validate` - Validate story consistency
- `POST /api/story/{story_id}/detect_contradictions` - Detect contradictions using Neo4j procedures
- `POST /api/story/{story_id}/scan_contradictions` - Trigger manual contradiction scan

#### Management
- `DELETE /api/story/{story_id}` - Delete story and associated data
- `GET /api/alerts/stats` - Get alert statistics

### No Authentication Required
- `GET /api/health` - Health check endpoint
- `GET /` - Root endpoint

### WebSocket Endpoints
- `WS /api/alerts/stream?token=<jwt_token>` - Real-time alert stream

## cURL Examples for Protected Endpoints

### 1. Authentication Header Format
All protected endpoints require a JWT token in the Authorization header:

```bash
# Replace YOUR_JWT_TOKEN with your actual Supabase JWT token
export JWT_TOKEN="YOUR_JWT_TOKEN"
```

### 2. Analyze Story Content
```bash
curl -X POST "http://localhost:8000/api/story/analyze" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "example-story-001",
    "content": "John entered the tavern. The bartender, Mary, greeted him warmly. John ordered an ale and sat by the fire.",
    "user_id": "user-123"
  }'
```

### 3. Query Story with Natural Language
```bash
curl -X POST "http://localhost:8000/api/story/example-story-001/query" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What did John order at the tavern?"
  }'
```

### 4. Get Character Knowledge at Specific Time
```bash
curl -X GET "http://localhost:8000/api/story/example-story-001/character/John/knowledge?timestamp=2024-01-15T10:30:00Z" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 5. Get Story Inconsistencies
```bash
curl -X GET "http://localhost:8000/api/story/example-story-001/inconsistencies" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 6. Validate Story Consistency
```bash
curl -X POST "http://localhost:8000/api/story/example-story-001/validate" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### 7. Get Story Knowledge Graph
```bash
curl -X GET "http://localhost:8000/api/story/example-story-001/graph" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 8. Delete Story
```bash
curl -X DELETE "http://localhost:8000/api/story/example-story-001" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 9. Query Item Ownership History
```bash
curl -X POST "http://localhost:8000/api/story/example-story-001/query" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me the complete ownership history of Excalibur"
  }'
```

### 10. Query Character's Current Items
```bash
curl -X POST "http://localhost:8000/api/story/example-story-001/query" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What items does Arthur currently own?"
  }'
```

### 11. WebSocket Connection (JavaScript Example)
```javascript
const token = "YOUR_JWT_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/api/alerts/stream?token=${token}`);

ws.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  console.log('Alert received:', alert);
};

ws.onopen = () => {
  console.log('Connected to alerts stream');
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

## Database Migrations

### Running Migrations

CineGraph uses Supabase for database management. To apply migrations:

```bash
# Apply all pending migrations
supabase db push

# View migration status
supabase db status

# Reset database (caution: this will delete all data)
supabase db reset

# Create a new migration
supabase migration new <migration_name>
```

### Manual Migration Scripts

For specific migration tasks, you can also run:

```bash
# Apply alerts table migration
python apply_alerts_migration.py

# Verify alerts migration
python verify_alerts_migration.py
```

### Migration Files

Migration files are stored in `supabase/migrations/` with timestamps:
- `202507091910_auth_rls.sql` - Authentication and Row Level Security setup

## Knowledge Graph Schema

### Entities

CineGraph uses a comprehensive knowledge graph schema with five main entity types:

#### Character
- `character_id` (String, unique): Unique identifier
- `name` (String, unique): Character name
- `description` (String): Character description
- `created_at`, `updated_at`, `deleted_at` (DateTime): Temporal fields

#### Knowledge
- `knowledge_id` (String, unique): Unique identifier
- `content` (String): Knowledge content
- `valid_from`, `valid_to` (DateTime): Temporal validity period
- `created_at`, `updated_at` (DateTime): Temporal fields

#### Scene
- `scene_id` (String, unique): Unique identifier
- `name` (String): Scene name
- `scene_order` (Int, sequential): Order in story sequence
- `created_at`, `updated_at` (DateTime): Temporal fields

#### Location
- `location_id` (String, unique): Unique identifier
- `name` (String, unique): Location name
- `details` (String): Location description
- `created_at`, `updated_at` (DateTime): Temporal fields

#### Item
- `item_id` (String, unique): Unique identifier
- `name` (String): Item name
- `description` (String): Item description
- `item_type` (Enum): weapon, tool, clothing, artifact
- `origin_scene` (String): Scene where item first appears
- `location_found` (String): Location where item was found
- `current_owner` (String): Current owner character ID
- `is_active` (Boolean): Whether item is actively in the story
- `created_at`, `updated_at` (DateTime): Temporal fields

### Relationships

#### OWNS (Character → Item)
Tracks complete ownership history with temporal support:
- `ownership_start` (DateTime, required): When ownership begins
- `ownership_end` (DateTime, optional): When ownership ends
- `obtained_from` (String, optional): Previous owner ID
- `transfer_method` (Enum): gift, exchange, theft, inheritance
- `ownership_notes` (String, optional): Additional context
- `created_at`, `updated_at` (DateTime): Temporal fields

#### Other Relationships
- `KNOWS` (Character → Character): Character knowledge relationships
- `RELATIONSHIP` (Character → Character): Character relationships
- `PRESENT_IN` (Character → Scene): Character scene appearances
- `OCCURS_IN` (Scene → Location): Scene location mapping
- `CONTRADICTS` (Knowledge → Knowledge): Knowledge contradictions
- `IMPLIES` (Knowledge → Knowledge): Knowledge implications

### Sample Cypher Queries

#### Query Ownership History
```cypher
// Get complete ownership history for an item
MATCH (c:Character)-[owns:OWNS]->(i:Item {name: 'Excalibur'})
WHERE owns.story_id = $story_id
RETURN c.name as owner, 
       owns.ownership_start as acquired,
       owns.ownership_end as lost,
       owns.transfer_method as how_obtained,
       owns.obtained_from as previous_owner
ORDER BY owns.ownership_start ASC
```

#### Query Current Item Owners
```cypher
// Find all items currently owned by a character
MATCH (c:Character {name: 'Arthur'})-[owns:OWNS]->(i:Item)
WHERE owns.story_id = $story_id 
  AND owns.ownership_end IS NULL
RETURN i.name as item, 
       i.item_type as type,
       owns.ownership_start as acquired,
       owns.transfer_method as how_obtained
ORDER BY owns.ownership_start DESC
```

#### Query Item Transfer Chain
```cypher
// Trace the complete transfer chain of an item
MATCH (i:Item {name: 'Magic Ring'})<-[owns:OWNS]-(c:Character)
WHERE owns.story_id = $story_id
OPTIONAL MATCH (prev:Character {character_id: owns.obtained_from})
RETURN c.name as current_owner,
       prev.name as previous_owner,
       owns.transfer_method as transfer_method,
       owns.ownership_start as transfer_date,
       owns.ownership_notes as notes
ORDER BY owns.ownership_start ASC
```

### Sample GraphQL Queries

#### Get Item Ownership History
```graphql
query ItemOwnershipHistory($itemName: String!, $storyId: String!) {
  items(where: { name: $itemName, story_id: $storyId }) {
    name
    description
    item_type
    ownedBy {
      character {
        name
        character_id
      }
      ownership_start
      ownership_end
      transfer_method
      obtained_from
      ownership_notes
    }
  }
}
```

#### Get Character's Current Items
```graphql
query CharacterItems($characterName: String!, $storyId: String!) {
  characters(where: { name: $characterName, story_id: $storyId }) {
    name
    owns(where: { ownership_end: null }) {
      item {
        name
        description
        item_type
      }
      ownership_start
      transfer_method
      obtained_from
    }
  }
}
```

## Architecture Overview

### Core Components

1. **FastAPI Application** (`app/main.py`) - REST API endpoints
2. **CineGraphAgent** (`agents/cinegraph_agent.py`) - AI-powered story analysis
3. **GraphitiManager** (`core/graphiti_manager.py`) - Neo4j knowledge graph management
4. **StoryProcessor** (`core/story_processor.py`) - Story content processing
5. **Redis Alerts** (`core/redis_alerts.py`) - Real-time alert system

### Data Flow

1. **Story Upload** → StoryProcessor → GraphitiManager → Neo4j
2. **AI Analysis** → CineGraphAgent → OpenAI → Structured insights
3. **Contradiction Detection** → Background tasks → Redis alerts → WebSocket clients
4. **User Queries** → CineGraphAgent → Knowledge graph → AI responses

### Security Features

- **JWT Authentication**: Supabase-based authentication
- **Rate Limiting**: Redis token bucket (5 requests/second per user)
- **User Isolation**: All data is scoped to authenticated users
- **CORS Protection**: Configured for specific origins

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cinegraph_agent.py

# Run with coverage
pytest --cov=app tests/
```

### Test Scripts
```bash
# Test API functionality
python test_api.py

# Test CineGraph Agent
python test_agent.py

# Test user isolation
python test_user_isolation_basic.py
```

## Development

### File Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   └── auth.py              # Authentication & rate limiting
├── agents/
│   ├── cinegraph_agent.py   # AI agent implementation
│   └── agent_factory.py     # Agent factory
├── core/
│   ├── graphiti_manager.py  # Neo4j knowledge graph
│   ├── story_processor.py   # Story processing
│   ├── redis_alerts.py      # Alert system
│   └── models.py           # Data models
├── tasks/
│   └── temporal_contradiction_detection.py  # Background tasks
├── tests/
│   └── test_*.py           # Test files
├── supabase/
│   └── migrations/         # Database migrations
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding New Endpoints

1. Define endpoint in `app/main.py`
2. Add authentication dependency: `Depends(get_rate_limited_user)`
3. Implement business logic in appropriate core module
4. Add tests in `tests/` directory

### Error Handling

The API uses standard HTTP status codes:
- `200` - Success
- `401` - Unauthorized (invalid/missing JWT)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check environment variables are set correctly
   - Verify Redis is running: `redis-cli ping`
   - Test Neo4j connection: `neo4j cypher-shell`
   - Check Supabase project status

2. **Authentication Issues**
   - Verify JWT token is valid and not expired
   - Check Supabase configuration
   - Ensure correct service role key is used

3. **Rate Limiting**
   - Default limit is 5 requests/second per user
   - Check Redis connection if rate limiting isn't working
   - Monitor Redis with: `redis-cli monitor`

4. **Migration Issues**
   - Run `supabase db status` to check migration state
   - Use `supabase db reset` to start fresh (development only)
   - Check migration files for syntax errors

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License.
