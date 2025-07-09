from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import redis
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from core.graphiti_manager import GraphitiManager
from agents.cinegraph_agent import CineGraphAgent
from core.story_processor import StoryProcessor
from core.models import StoryInput, InconsistencyReport, CharacterKnowledge, ContradictionDetectionResult, UserProfile, UserProfileUpdate
from core.redis_alerts import alert_manager
from tasks.temporal_contradiction_detection import scan_story_contradictions
from celery_config import REDIS_HOST, REDIS_PORT, REDIS_DB, ALERTS_CHANNEL
from app.auth import get_authenticated_user, get_rate_limited_user, verify_websocket_token, User, get_supabase_client

load_dotenv()

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
