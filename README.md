# CineGraph - Advanced Story Analysis System

CineGraph is an AI-powered story analysis system that leverages graph databases and advanced natural language processing to analyze narrative consistency, character development, and plot coherence. It provides deep insights into story structure, temporal relationships, and potential plot holes.

## 🌟 Features

### Core Capabilities
- **Story Analysis**: Comprehensive analysis of narrative structure, character development, and plot coherence
- **Temporal Reasoning**: Advanced temporal consistency checking and timeline analysis
- **Character Consistency**: Deep character relationship mapping and consistency validation
- **Plot Hole Detection**: Intelligent detection of logical inconsistencies and narrative gaps
- **Knowledge Graph**: Dynamic knowledge graph construction from story content
- **Quest Generation**: Create quests from story events using OpenAI models
- **Dialogue Generation**: Produce interactive dialogue trees with OpenAI

### Enhanced AI Agent
- **Dynamic Cypher Generation**: AI can write custom Cypher queries based on story schema
- **Three-Tier Query Architecture**: Predefined, template-based, and AI-generated queries
- **Advanced Validation**: Comprehensive query validation and safety checks
- **Intelligent Caching**: Performance optimization through smart query caching
- **Real-time Analysis**: Live contradiction detection and alert system
- **Quest Generation (OpenAI-powered)**: Create quests from story events
- **Dialogue Generation (OpenAI-powered)**: Build dynamic dialogues from interactions

### Technical Stack
- **Backend**: FastAPI with async/await support
- **Database**: Neo4j graph database with Graphiti framework
- **AI Integration**: OpenAI GPT models for analysis and query generation
- **Authentication**: Supabase Auth with Row Level Security (RLS)
- **Background Jobs**: Celery for async processing
- **Caching**: Redis for performance optimization

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Neo4j database
- Redis server
- OpenAI API key (optional)
- Supabase project (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lnk-zone/cinegraph.git
   cd cinegraph
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the setup script**
   ```bash
   python setup_enhanced_agent.py
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Environment Variables

```env
# Database Configuration
GRAPHITI_DATABASE_URL=bolt://localhost:7687
GRAPHITI_DATABASE_USER=neo4j
GRAPHITI_DATABASE_PASSWORD=your_password
GRAPHITI_DATABASE_NAME=neo4j

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your_openai_key

# Supabase Configuration (Optional)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
```

## 📖 Usage

### Basic Story Analysis

```python
from agents.cinegraph_agent import CineGraphAgent

# Initialize the agent
agent = CineGraphAgent(
    graphiti_manager=your_graphiti_manager,
    openai_api_key=your_openai_key
)

# Analyze a story
story_content = "Your story content here..."
analysis = await agent.analyze_story(story_content, extracted_data)
```

### Advanced Query Examples

```python
# Timeline analysis
timeline = await agent.analyze_story_timeline("story_123", "user_456")

# Character consistency check
character_analysis = await agent.analyze_character_consistency(
    "story_123", "character_name", "user_456"
)

# Plot hole detection
plot_holes = await agent.detect_plot_holes("story_123", "user_456")

# Custom query validation
validation = await agent.validate_query(
    "MATCH (c:Character {story_id: $story_id}) RETURN c.name"
)
```

### API Endpoints

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Analyze story
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your story content"}'

# Query story
curl -X POST "http://localhost:8000/api/query" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"story_id": "story_123", "question": "What did John know?"}'
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  CineGraph      │    │   Neo4j Graph   │
│   (REST API)    │◄──►│     Agent       │◄──►│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Supabase      │    │     OpenAI      │    │     Redis       │
│   (Auth & DB)   │    │   (AI Models)   │    │   (Caching)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Three-Tier Query Architecture

1. **Tier 1: Core Operations** (Predefined)
   - Consistency checks and validation rules
   - Performance-critical queries
   - System health checks

2. **Tier 2: Common Patterns** (Template-based)
   - Character relationship queries
   - Timeline analysis
   - Knowledge propagation

3. **Tier 3: Creative Queries** (AI-generated)
   - Novel analysis questions
   - Custom user queries
   - Exploratory analysis

## 🔧 Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest tests/test_cinegraph_agent.py
python -m pytest tests/test_consistency_engine.py
```

### Demo Script

```bash
# Run comprehensive demo
python test_enhanced_agent.py
```

### Code Structure

```
cinegraph/
├── backend/
│   ├── agents/           # CineGraph Agent implementation
│   ├── app/             # FastAPI application
│   ├── core/            # Core modules (models, managers)
│   ├── docs/            # Documentation
│   ├── graphiti/        # Graph schema and rules
│   ├── sql/             # Database migrations
│   ├── tests/           # Test suites
│   └── tasks/           # Background jobs
├── README.md
└── .gitignore
```

## 📊 Performance Features

### Query Optimization
- **Smart Caching**: MD5-based query hashing with LRU eviction
- **Template System**: Pre-optimized queries for common operations
- **Safety Limits**: Automatic LIMIT clauses to prevent large result sets
- **Validation**: Comprehensive query safety and syntax checking

### Analysis Capabilities
- **Timeline Coherence**: Temporal consistency scoring
- **Character Consistency**: Relationship and knowledge tracking
- **Plot Hole Detection**: Logical inconsistency identification
- **Knowledge Networks**: Dynamic knowledge graph construction

## 🛡️ Security

### Data Protection
- **Row Level Security**: Supabase RLS for multi-tenant isolation
- **Query Validation**: Prevents dangerous operations
- **JWT Authentication**: Secure API access
- **Data Isolation**: User-scoped queries and results

### Safety Features
- **Query Whitelisting**: Only safe read operations allowed
- **Injection Prevention**: Parameterized queries
- **Access Control**: Role-based permissions
- **Audit Logging**: Comprehensive activity tracking

## 📚 Documentation

- **[Enhanced Agent Capabilities](backend/docs/enhanced_agent_capabilities.md)** - Detailed feature documentation
- **[API Documentation](backend/README_API.md)** - REST API reference
- **[Agent Documentation](backend/README_CINEGRAPH_AGENT.md)** - Agent usage guide
- **[Story Ingestion Pipeline](backend/docs/story_ingestion_pipeline.md)** - Data processing flow

## 🧪 Testing

### Test Coverage
- Query validation and optimization
- Advanced analysis features
- Caching mechanisms
- Authentication and authorization
- Background job processing

### Performance Benchmarks
- Query execution times
- Cache hit/miss ratios
- Analysis accuracy metrics
- System scalability tests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: https://github.com/lnk-zone/cinegraph
- **Documentation**: [backend/docs/](backend/docs/)
- **Issues**: https://github.com/lnk-zone/cinegraph/issues

## 🙏 Acknowledgments

- **Graphiti Framework** - For graph database management
- **OpenAI** - For AI-powered analysis capabilities
- **Supabase** - For authentication and database services
- **FastAPI** - For high-performance API framework

---

**CineGraph** - Transforming story analysis through AI and graph technology.
