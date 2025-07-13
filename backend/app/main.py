from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from sdk_agents.manager import SDKAgentManager
import os
import redis
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

from core.graphiti_manager import GraphitiManager
from agents.cinegraph_agent import CineGraphAgent
from core.story_processor import StoryProcessor
from core.models import (
    StoryInput, InconsistencyReport, CharacterKnowledge, ContradictionDetectionResult,
    UserProfile, UserProfileUpdate, EpisodeEntity, EpisodeHierarchy, RelationshipEvolution
)
from game.models import (
    RPGProject,
    ExportConfiguration,
    RPGVariable,
    RPGSwitch,
    RPGCharacter,
    RPGLocation,
    LocationConnection,
)
from game.character_enhancer import StoryCharacterEnhancer
from game.variable_generator import StoryVariableGenerator
from game.location_enhancer import StoryLocationEnhancer
from core.redis_alerts import alert_manager
from tasks.temporal_contradiction_detection import scan_story_contradictions
from celery_config import REDIS_HOST, REDIS_PORT, REDIS_DB, ALERTS_CHANNEL
from app.auth import get_authenticated_user, get_rate_limited_user, verify_websocket_token, User, get_supabase_client

load_dotenv()


class ConversationRequest(BaseModel):
    """Input payload for SDK conversation endpoint."""

    session_id: Optional[str] = None
    messages: List[str]


class ConversationResponse(BaseModel):
    """Response payload for SDK conversation endpoint."""

    session_id: str
    responses: List[str]


sdk_sessions: Dict[str, SDKAgentManager] = {}

app = FastAPI(
    title="CineGraph API",
    description="AI-powered story consistency tool for RPG Maker creators",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
graphiti_manager = GraphitiManager()
story_processor = StoryProcessor(graphiti_manager=graphiti_manager)
cinegraph_agent = CineGraphAgent(graphiti_manager=graphiti_manager)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    await graphiti_manager.initialize()
    await cinegraph_agent.initialize()
    await alert_manager.start_listening()

@app.get("/")
async def root():
    return {"message": "CineGraph API is running"}


@app.post("/api/sdk/conversation", response_model=ConversationResponse)
async def sdk_conversation(conversation: ConversationRequest):
    """Route a list of messages through the SDK agent orchestrator."""
    try:
        session_id = conversation.session_id or str(uuid.uuid4())
        manager = sdk_sessions.get(session_id)
        if manager is None:
            manager = SDKAgentManager()
            sdk_sessions[session_id] = manager

        responses: List[str] = []
        for message in conversation.messages:
            response = await manager.send(message)
            responses.append(response)

        return ConversationResponse(session_id=session_id, responses=responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === RPG Project Endpoints ===

@app.post("/api/rpg-projects")
async def create_rpg_project(project: RPGProject):
    """Create a new RPG project."""
    project_id = await graphiti_manager.create_rpg_project(project)
    return {"project_id": project_id, "project": project}


@app.post("/api/rpg-projects/{project_id}/sync-story")
async def sync_project_story(project_id: str, story: StoryInput):
    """Persist story content for a specific RPG project."""
    await graphiti_manager.sync_project_story(project_id, story)
    return {
        "status": "success",
        "project_id": project_id,
        "story_id": story.story_id,
    }


@app.get("/api/rpg-projects/{project_id}/export-configs")
async def get_export_configs(project_id: str):
    """Retrieve export configurations for a project."""
    configs = await graphiti_manager.get_export_configs(project_id)
    return {"export_configs": configs}


@app.post("/api/rpg-projects/{project_id}/export-configs")
async def add_export_config(project_id: str, config: ExportConfiguration):
    """Add an export configuration to a project."""
    await graphiti_manager.add_export_config(project_id, config)
    configs = await graphiti_manager.get_export_configs(project_id)
    return {"status": "success", "count": len(configs)}


@app.get("/api/rpg-projects/{project_id}/variables")
async def get_project_variables(project_id: str):
    """Retrieve variables for a project."""
    vars = await graphiti_manager.get_project_variables(project_id)
    return {"variables": vars}


@app.post("/api/rpg-projects/{project_id}/variables")
async def add_project_variable(project_id: str, variable: RPGVariable):
    """Add a variable to a project."""
    await graphiti_manager.add_project_variable(project_id, variable)
    vars = await graphiti_manager.get_project_variables(project_id)
    return {"status": "success", "count": len(vars)}


@app.post("/api/rpg-projects/{project_id}/variables/generate-from-story")
async def generate_variables_from_story(project_id: str):
    """Generate variables from the current story state using the agent."""
    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    generator = StoryVariableGenerator(cinegraph_agent)
    all_vars: List[RPGVariable] = []
    for sid in story_ids:
        vars_for_story = await generator.generate_variables(sid)
        all_vars.extend(vars_for_story)

    await graphiti_manager.replace_project_variables(project_id, all_vars)
    return {"status": "success", "variables": all_vars}


@app.post("/api/rpg-projects/{project_id}/variables/{variable_id}/story-sync")
async def sync_variable_from_story(project_id: str, variable_id: str):
    """Sync a single variable with data from the story state."""
    variables = await graphiti_manager.get_project_variables(project_id)
    variable = next((v for v in variables if v.name == variable_id), None)
    if not variable:
        raise HTTPException(status_code=404, detail="Variable not found")

    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    generator = StoryVariableGenerator(cinegraph_agent)
    vars_for_story = await generator.generate_variables(story_ids[0])
    for updated in vars_for_story:
        if updated.name == variable_id:
            await graphiti_manager.update_project_variable(project_id, updated)
            variable = updated
            break

    return {"status": "success", "variable": variable}


@app.get("/api/rpg-projects/{project_id}/switches")
async def get_project_switches(project_id: str):
    """Retrieve switches for a project."""
    switches = await graphiti_manager.get_project_switches(project_id)
    return {"switches": switches}


@app.post("/api/rpg-projects/{project_id}/switches")
async def add_project_switch(project_id: str, switch: RPGSwitch):
    """Add a switch to a project."""
    await graphiti_manager.add_project_switch(project_id, switch)
    switches = await graphiti_manager.get_project_switches(project_id)
    return {"status": "success", "count": len(switches)}


@app.get("/api/rpg-projects/{project_id}/characters")
async def get_project_characters(project_id: str):
    """Retrieve characters for a project."""
    chars = await graphiti_manager.get_project_characters(project_id)
    return {"characters": chars}


@app.post("/api/rpg-projects/{project_id}/characters")
async def add_project_character(project_id: str, character: RPGCharacter):
    """Add a character to a project."""
    await graphiti_manager.add_project_character(project_id, character)
    chars = await graphiti_manager.get_project_characters(project_id)
    return {"status": "success", "count": len(chars)}


@app.post("/api/rpg-projects/{project_id}/characters/generate-stats")
async def generate_character_stats(project_id: str):
    """Generate character stats from the current story state."""
    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    enhancer = StoryCharacterEnhancer(cinegraph_agent)
    all_chars: List[RPGCharacter] = []
    for sid in story_ids:
        chars_for_story = await enhancer.enhance_characters(sid)
        all_chars.extend(chars_for_story)

    await graphiti_manager.replace_project_characters(project_id, all_chars)
    return {"status": "success", "characters": all_chars}


@app.post("/api/rpg-projects/{project_id}/characters/{character_id}/enhance-from-story")
async def enhance_character_from_story(project_id: str, character_id: str):
    """Update a character's details using the story state."""
    chars = await graphiti_manager.get_project_characters(project_id)
    character = next((c for c in chars if c.name == character_id), None)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    enhancer = StoryCharacterEnhancer(cinegraph_agent)
    chars_for_story = await enhancer.enhance_characters(story_ids[0])
    for updated in chars_for_story:
        if updated.name == character_id:
            await graphiti_manager.update_project_character(project_id, updated)
            character = updated
            break

    return {"status": "success", "character": character}


@app.get("/api/rpg-projects/{project_id}/characters/{character_id}/knowledge-state")
async def get_character_knowledge_state(project_id: str, character_id: str):
    """Retrieve a character's knowledge state."""
    knowledge = await graphiti_manager.get_character_knowledge_state(project_id, character_id)
    return {"knowledge_state": knowledge}


@app.put("/api/rpg-projects/{project_id}/characters/{character_id}/knowledge-state")
async def update_character_knowledge_state(project_id: str, character_id: str, knowledge: List[Dict[str, Any]]):
    """Update a character's knowledge state."""
    await graphiti_manager.update_character_knowledge_state(project_id, character_id, knowledge)
    return {"status": "success"}


@app.get("/api/rpg-projects/{project_id}/locations")
async def get_project_locations(project_id: str):
    """Retrieve locations for a project."""
    locs = await graphiti_manager.get_project_locations(project_id)
    return {"locations": locs}


@app.post("/api/rpg-projects/{project_id}/locations")
async def add_project_location(project_id: str, location: RPGLocation):
    """Add a location to a project."""
    await graphiti_manager.add_project_location(project_id, location)
    locs = await graphiti_manager.get_project_locations(project_id)
    return {"status": "success", "count": len(locs)}


@app.post("/api/rpg-projects/{project_id}/locations/generate-from-story")
async def generate_locations_from_story(project_id: str):
    """Generate locations and connections from the story state."""
    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    enhancer = StoryLocationEnhancer(cinegraph_agent)
    all_locs: List[RPGLocation] = []
    all_conns: List[LocationConnection] = []
    for sid in story_ids:
        locs, conns = await enhancer.enhance_locations(sid)
        all_locs.extend(locs)
        all_conns.extend(conns)

    await graphiti_manager.replace_project_locations(project_id, all_locs)
    await graphiti_manager.replace_location_connections(project_id, all_conns)
    return {"status": "success", "locations": all_locs, "connections": all_conns}


@app.post("/api/rpg-projects/{project_id}/locations/{location_id}/enhance-from-story")
async def enhance_location_from_story(project_id: str, location_id: str):
    """Update a location's details using the story state."""
    locs = await graphiti_manager.get_project_locations(project_id)
    location = next((l for l in locs if l.name == location_id), None)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    story_ids = await graphiti_manager.get_project_story_ids(project_id)
    if not story_ids:
        raise HTTPException(status_code=400, detail="No stories found for project")

    enhancer = StoryLocationEnhancer(cinegraph_agent)
    new_locs, conns = await enhancer.enhance_locations(story_ids[0])
    for updated in new_locs:
        if updated.name == location_id:
            await graphiti_manager.update_project_location(project_id, updated)
            location = updated
            break

    await graphiti_manager.replace_location_connections(project_id, conns)
    return {"status": "success", "location": location}


@app.get("/api/rpg-projects/{project_id}/locations/{location_id}/connections")
async def get_location_connections(project_id: str, location_id: str):
    """Retrieve connections for a specific location."""
    conns = await graphiti_manager.get_location_connections(project_id, location_id)
    return {"connections": conns}


@app.post("/api/rpg-projects/{project_id}/locations/{location_id}/connections")
async def add_location_connection(project_id: str, location_id: str, connection: LocationConnection):
    """Add a connection for a location."""
    await graphiti_manager.add_location_connection(project_id, connection)
    conns = await graphiti_manager.get_location_connections(project_id, location_id)
    return {"status": "success", "count": len(conns)}

@app.post("/api/story/analyze")
async def analyze_story(story_input: StoryInput, current_user: User = Depends(get_rate_limited_user)):
    """Analyze story content and extract knowledge graph"""
    try:
        # Ensure user_id is set for data isolation
        story_input.user_id = current_user.id
        
        # Process the story text (now includes GraphitiManager integration)
        extracted_data = await story_processor.process_story(story_input.content, story_input.story_id, current_user.id)
        
        # The processing already handles upserting to the knowledge graph
        # through the GraphitiManager, so we don't need to call add_story_content
        
        # Get AI insights
        insights = await cinegraph_agent.analyze_story(story_input.content, extracted_data)
        
        return {
            "status": "success",
            "extracted_data": extracted_data,
            "insights": insights,
            "story_id": story_input.story_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/story/{story_id}/inconsistencies")
async def get_inconsistencies(story_id: str, current_user: User = Depends(get_rate_limited_user)):
    """Get story inconsistencies detected by the AI agent"""
    try:
        inconsistencies = await cinegraph_agent.detect_inconsistencies(story_id, current_user.id)
        return {
            "status": "success",
            "inconsistencies": inconsistencies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/story/{story_id}/character/{character_name}/knowledge")
async def get_character_knowledge(story_id: str, character_name: str, timestamp: Optional[str] = None, current_user: User = Depends(get_rate_limited_user)):
    """Get what a character knows at a specific point in time"""
    try:
        knowledge = await graphiti_manager.get_character_knowledge(
            story_id, character_name, timestamp, current_user.id
        )
        return {
            "status": "success",
            "character": character_name,
            "knowledge": knowledge,
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/story/{story_id}/graph")
async def get_story_graph(story_id: str, current_user: User = Depends(get_rate_limited_user)):
    """Get the complete story knowledge graph"""
    try:
        graph_data = await graphiti_manager.get_story_graph(story_id, current_user.id)
        return {
            "status": "success",
            "graph": graph_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/query")
async def query_story(story_id: str, query: Dict[str, Any], current_user: User = Depends(get_rate_limited_user)):
    """Query the story using natural language via the AI agent"""
    try:
        response = await cinegraph_agent.query_story(story_id, query["question"], current_user.id)
        return {
            "status": "success",
            "query": query["question"],
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/validate")
async def validate_story_consistency(story_id: str, current_user: User = Depends(get_rate_limited_user)):
    """Run complete story consistency validation"""
    try:
        validation_report = await cinegraph_agent.validate_story_consistency(story_id, current_user.id)
        return {
            "status": "success",
            "validation_report": validation_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/hierarchy")
async def update_episode_hierarchy(story_id: str, episodes: List[EpisodeHierarchy], current_user: User = Depends(get_rate_limited_user)):
    """Update the hierarchy of episodes for the given story"""
    try:
        result = await graphiti_manager.add_episode_hierarchy(story_id, episodes)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/relationship_evolution")
async def log_relationship_evolution(story_id: str, evolutions: List[RelationshipEvolution], current_user: User = Depends(get_rate_limited_user)):
    """Log relationship evolution events for the given story"""
    try:
        result = await graphiti_manager.track_relationship_evolution(evolutions, story_id)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/story/{story_id}")
async def delete_story(story_id: str, current_user: User = Depends(get_authenticated_user)):
    """Delete a story and its associated knowledge graph"""
    try:
        await graphiti_manager.delete_story(story_id, current_user.id)
        return {"status": "success", "message": f"Story {story_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/detect_contradictions")
async def detect_contradictions(story_id: str, current_user: User = Depends(get_rate_limited_user)):
    """Run DETECT_CONTRADICTIONS procedure for a specific story"""
    try:
        result = await graphiti_manager.detect_contradictions(story_id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/{story_id}/scan_contradictions")
async def scan_contradictions(story_id: str, current_user: User = Depends(get_rate_limited_user)):
    """Trigger a manual contradiction scan for a specific story"""
    try:
        result = await scan_story_contradictions(story_id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/alerts/stream")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for streaming alerts after JWT authentication"""
    try:
        await websocket.accept()
        
        # Get token from query parameters or headers
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Token required")
            return
        
        # Verify JWT token
        try:
            user = await verify_websocket_token(token)
        except ValueError as e:
            await websocket.close(code=1008, reason=str(e))
            return
        
        # Connect to Redis for alerts
        alerts_redis = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        pubsub = alerts_redis.pubsub()
        pubsub.subscribe(ALERTS_CHANNEL)
        
        # Forward alerts to client
        async def listen_for_alerts():
            for message in pubsub.listen():
                if message['type'] == 'message':
                    await websocket.send_text(message['data'])
        
        # Start listening task
        listen_task = asyncio.create_task(listen_for_alerts())
        
        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            listen_task.cancel()
            pubsub.unsubscribe(ALERTS_CHANNEL)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.close()
        print(f"Connection error: {e}")

@app.get("/api/alerts/stats")
async def get_alert_stats(current_user: User = Depends(get_authenticated_user)):
    """Get Redis alerts system statistics"""
    try:
        stats = alert_manager.get_alert_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/me", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_authenticated_user)):
    """Get current user's profile"""
    try:
        supabase = get_supabase_client()
        
        # Fetch user profile from Supabase
        response = supabase.table("profiles").select("*").eq("id", current_user.id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile_data = response.data[0]
        
        return UserProfile(
            id=profile_data["id"],
            email=profile_data["email"],
            full_name=profile_data.get("full_name"),
            avatar_url=profile_data.get("avatar_url"),
            created_at=datetime.fromisoformat(profile_data["created_at"].replace("Z", "+00:00"))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/users/me", response_model=UserProfile)
async def update_user_profile(profile_update: UserProfileUpdate, current_user: User = Depends(get_authenticated_user)):
    """Update current user's profile"""
    try:
        supabase = get_supabase_client()
        
        # Prepare update data (only include non-None values)
        update_data = {}
        if profile_update.full_name is not None:
            update_data["full_name"] = profile_update.full_name
        if profile_update.avatar_url is not None:
            update_data["avatar_url"] = profile_update.avatar_url
        
        if not update_data:
            # If no data to update, just return current profile
            return await get_user_profile(current_user)
        
        # Update profile in Supabase
        response = supabase.table("profiles").update(update_data).eq("id", current_user.id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile_data = response.data[0]
        
        return UserProfile(
            id=profile_data["id"],
            email=profile_data["email"],
            full_name=profile_data.get("full_name"),
            avatar_url=profile_data.get("avatar_url"),
            created_at=datetime.fromisoformat(profile_data["created_at"].replace("Z", "+00:00"))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def ensure_schema() -> Dict[str, Any]:
    """
    Apply Neo4j schema constraints and indexes from bootstrap script.
    
    This function reads and executes the neo4j_bootstrap.cypher script
    to synchronize the live database with CineGraphAgent schema requirements.
    
    Returns:
        Dict containing execution results and any errors
    """
    try:
        # Read the bootstrap script
        bootstrap_path = Path(__file__).parent.parent / "neo4j_bootstrap.cypher"
        
        if not bootstrap_path.exists():
            return {
                "status": "error",
                "error": f"Bootstrap script not found at {bootstrap_path}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        with open(bootstrap_path, 'r') as f:
            bootstrap_script = f.read()
        
        # Split script into individual statements
        # Remove comments and empty lines
        statements = []
        current_statement = ""
        
        for line in bootstrap_script.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if line.startswith('//') or not line:
                continue
            
            current_statement += line + " "
            
            # End of statement
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Execute each statement
        successful_statements = 0
        failed_statements = 0
        errors = []
        
        if not graphiti_manager.client:
            await graphiti_manager.connect()
        
        for i, statement in enumerate(statements):
            try:
                # Execute through GraphitiManager's Neo4j connection
                # Use the Graphiti client's internal driver
                if hasattr(graphiti_manager.client, 'driver'):
                    # Direct driver access
                    result = await graphiti_manager.client.driver.execute_query(
                        statement, 
                        database_=graphiti_manager.config.database_name
                    )
                elif hasattr(graphiti_manager.client, '_driver'):
                    # Private driver access
                    result = await graphiti_manager.client._driver.execute_query(
                        statement,
                        database_=graphiti_manager.config.database_name
                    )
                else:
                    # Fallback: try to execute via session
                    async with graphiti_manager.client._driver.session(database=graphiti_manager.config.database_name) as session:
                        result = await session.run(statement)
                        await result.consume()
                
                successful_statements += 1
                
            except Exception as e:
                failed_statements += 1
                error_msg = f"Statement {i+1}: {str(e)}"
                errors.append(error_msg)
                print(f"Schema error: {error_msg}")
        
        return {
            "status": "completed" if failed_statements == 0 else "partial",
            "total_statements": len(statements),
            "successful": successful_statements,
            "failed": failed_statements,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Schema synchronization completed. Database now matches CineGraphAgent requirements."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/api/admin/ensure_schema")
async def admin_ensure_schema(current_user: User = Depends(get_authenticated_user)):
    """
    Development-only endpoint to ensure Neo4j schema matches CineGraphAgent design.
    
    This endpoint applies the neo4j_bootstrap.cypher script to create all necessary
    constraints, indexes, and properties for optimal CineGraphAgent performance.
    
    Security: Requires authentication. Only available in development environment.
    
    Returns:
        Dict containing schema synchronization results
    """
    try:
        # Development environment check
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment not in ["development", "dev", "local"]:
            raise HTTPException(
                status_code=403, 
                detail="Schema management endpoint only available in development environment"
            )
        
        # Execute schema synchronization
        result = await ensure_schema()
        
        return {
            "endpoint": "admin_ensure_schema",
            "user_id": current_user.id,
            "environment": environment,
            "schema_sync_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema management failed: {str(e)}")


@app.get("/api/admin/schema_status")
async def admin_schema_status(current_user: User = Depends(get_authenticated_user)):
    """
    Development-only endpoint to check current Neo4j schema status.
    
    Returns information about existing constraints, indexes, and compatibility
    with CineGraphAgent requirements.
    
    Security: Requires authentication. Only available in development environment.
    
    Returns:
        Dict containing current schema status and recommendations
    """
    try:
        # Development environment check
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment not in ["development", "dev", "local"]:
            raise HTTPException(
                status_code=403, 
                detail="Schema status endpoint only available in development environment"
            )
        
        if not graphiti_manager.client:
            await graphiti_manager.connect()
        
        # Get current constraints
        constraints_query = "SHOW CONSTRAINTS"
        constraints_result = None
        
        # Get current indexes
        indexes_query = "SHOW INDEXES"
        indexes_result = None
        
        # Execute queries with proper driver access
        if hasattr(graphiti_manager.client, 'driver'):
            # Direct driver access
            constraints_result = await graphiti_manager.client.driver.execute_query(
                constraints_query,
                database_=graphiti_manager.config.database_name
            )
            indexes_result = await graphiti_manager.client.driver.execute_query(
                indexes_query,
                database_=graphiti_manager.config.database_name
            )
        elif hasattr(graphiti_manager.client, '_driver'):
            # Private driver access
            constraints_result = await graphiti_manager.client._driver.execute_query(
                constraints_query,
                database_=graphiti_manager.config.database_name
            )
            indexes_result = await graphiti_manager.client._driver.execute_query(
                indexes_query,
                database_=graphiti_manager.config.database_name
            )
        else:
            # Fallback: try to execute via session
            async with graphiti_manager.client._driver.session(database=graphiti_manager.config.database_name) as session:
                constraints_result_cursor = await session.run(constraints_query)
                constraints_result = await constraints_result_cursor.data()
                
                indexes_result_cursor = await session.run(indexes_query)
                indexes_result = await indexes_result_cursor.data()
        
        # Count existing schema objects (handle different result formats)
        constraints_count = 0
        indexes_count = 0
        
        if constraints_result:
            if hasattr(constraints_result, 'records') and constraints_result.records:
                constraints_count = len(constraints_result.records)
            elif isinstance(constraints_result, list):
                constraints_count = len(constraints_result)
        
        if indexes_result:
            if hasattr(indexes_result, 'records') and indexes_result.records:
                indexes_count = len(indexes_result.records)
            elif isinstance(indexes_result, list):
                indexes_count = len(indexes_result)
        
        # Check for key CineGraphAgent requirements
        has_story_id_indexes = False
        has_user_id_indexes = False
        has_temporal_indexes = False
        
        # Extract index names from results
        index_names = []
        if indexes_result:
            if hasattr(indexes_result, 'records') and indexes_result.records:
                index_names = [record.get("name", "") for record in indexes_result.records]
            elif isinstance(indexes_result, list):
                index_names = [record.get("name", "") for record in indexes_result]
        
        if index_names:
            has_story_id_indexes = any("story_id" in name for name in index_names)
            has_user_id_indexes = any("user_id" in name for name in index_names) 
            has_temporal_indexes = any("temporal" in name for name in index_names)
        
        # Determine schema compatibility
        compatibility_score = 0
        if constraints_count > 0:
            compatibility_score += 25
        if indexes_count > 10:
            compatibility_score += 25
        if has_story_id_indexes:
            compatibility_score += 20
        if has_user_id_indexes:
            compatibility_score += 20
        if has_temporal_indexes:
            compatibility_score += 10
        
        schema_status = "incompatible"
        if compatibility_score >= 80:
            schema_status = "compatible"
        elif compatibility_score >= 50:
            schema_status = "partial"
        
        recommendations = []
        if not has_story_id_indexes:
            recommendations.append("Add story_id indexes for data isolation")
        if not has_user_id_indexes:
            recommendations.append("Add user_id indexes for multi-tenancy")
        if not has_temporal_indexes:
            recommendations.append("Add temporal indexes for bi-temporal queries")
        if constraints_count < 5:
            recommendations.append("Add unique constraints for entity integrity")
        if indexes_count < 20:
            recommendations.append("Add performance indexes for common query patterns")
        
        if not recommendations:
            recommendations.append("Schema appears complete for CineGraphAgent requirements")
        
        return {
            "endpoint": "admin_schema_status",
            "user_id": current_user.id,
            "environment": environment,
            "schema_status": schema_status,
            "compatibility_score": compatibility_score,
            "constraints_count": constraints_count,
            "indexes_count": indexes_count,
            "cinegraph_requirements": {
                "story_id_indexes": has_story_id_indexes,
                "user_id_indexes": has_user_id_indexes,
                "temporal_indexes": has_temporal_indexes
            },
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Run /api/admin/ensure_schema to synchronize schema with CineGraphAgent requirements"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema status check failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "graphiti": await graphiti_manager.health_check(),
        "agent": await cinegraph_agent.health_check(),
        "alerts": alert_manager.get_alert_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
