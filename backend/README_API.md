# CineGraph API Implementation

This document describes the implementation of the CineGraph API layer with WebSocket support, JWT authentication, and rate limiting.

## Features Implemented

### 1. WebSocket Alert Stream (`/api/alerts/stream`)

- **Endpoint**: `ws://localhost:8000/api/alerts/stream?token=<jwt_token>`
- **Authentication**: JWT token verification using Supabase
- **Functionality**: Subscribes to Redis alerts channel and forwards messages to connected clients
- **Usage**: 
  ```javascript
  const ws = new WebSocket('ws://localhost:8000/api/alerts/stream?token=your_jwt_token');
  ws.onmessage = (event) => {
    const alert = JSON.parse(event.data);
    console.log('Alert received:', alert);
  };
  ```

### 2. JWT Authentication & User Dependency Injection

- **Implementation**: `app/auth.py`
- **User Model**: Extracts user ID and email from Supabase JWT
- **Dependencies**:
  - `get_authenticated_user`: Authentication only
  - `get_rate_limited_user`: Authentication + rate limiting
- **Usage**: Add as dependency to endpoints that require authentication

### 3. Rate Limiting (Redis Token Bucket)

- **Algorithm**: Token bucket with Redis backend
- **Limit**: 5 requests per second per user
- **Implementation**: `TokenBucket` class in `app/auth.py`
- **Endpoints Protected**: All query endpoints (analyze, query, validate, etc.)

## API Endpoints

### Authentication Required (Rate Limited)
- `POST /api/story/analyze` - Analyze story content
- `GET /api/story/{story_id}/inconsistencies` - Get inconsistencies
- `GET /api/story/{story_id}/character/{character_name}/knowledge` - Get character knowledge
- `GET /api/story/{story_id}/graph` - Get story graph
- `POST /api/story/{story_id}/query` - Query story
- `POST /api/story/{story_id}/validate` - Validate story consistency
- `POST /api/story/{story_id}/detect_contradictions` - Detect contradictions
- `POST /api/story/{story_id}/scan_contradictions` - Scan contradictions

### Authentication Required (No Rate Limiting)
- `DELETE /api/story/{story_id}` - Delete story
- `GET /api/alerts/stats` - Get alert statistics

### No Authentication Required
- `GET /api/health` - Health check
- `GET /` - Root endpoint

### WebSocket
- `WS /api/alerts/stream` - Real-time alert stream (JWT required)

## Configuration

### Environment Variables Required
```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT (optional, for future use)
JWT_SECRET_KEY=your_jwt_secret
```

### Dependencies Added
- `websockets==12.0` - WebSocket support
- `supabase==2.3.4` - Supabase client
- `python-jose[cryptography]==3.3.0` - JWT handling
- `redis==5.0.1` - Redis client

## Rate Limiting Details

The token bucket algorithm works as follows:
1. Each user gets a bucket with 5 tokens (capacity)
2. Tokens refill at 5 tokens per second
3. Each request consumes 1 token
4. If no tokens available, request is rejected with 429 status
5. Bucket state is stored in Redis with automatic expiration

## WebSocket Authentication

WebSocket authentication uses query parameters:
1. Client connects with `?token=<jwt_token>`
2. Server verifies token with Supabase
3. If valid, connection is established
4. If invalid, connection is closed with error code 1008

## Testing

Run the test script to verify functionality:
```bash
python test_api.py
```

Note: Update `TEST_JWT_TOKEN` with a valid Supabase JWT token for testing.

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app/main.py
```

## File Structure

```
app/
├── main.py          # FastAPI application with all endpoints
├── auth.py          # JWT authentication and rate limiting
test_api.py          # Test script for API functionality
```

## Error Handling

- **401 Unauthorized**: Invalid or missing JWT token
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server-side errors
- **WebSocket 1008**: Authentication failed during WebSocket connection

## Future Enhancements

1. **Metrics**: Add Prometheus metrics for rate limiting and WebSocket connections
2. **Logging**: Structured logging for authentication and rate limiting events
3. **Caching**: Redis caching for frequent queries
4. **Admin Endpoints**: Admin-only endpoints for user management
5. **Rate Limit Customization**: Per-user rate limit configuration
