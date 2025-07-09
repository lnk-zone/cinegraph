"""
CineGraph Agent Module
=====================

This module provides the CineGraph AI agent interface for story analysis,
querying, and consistency validation.
"""

import asyncio
import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from openai import AsyncOpenAI
from core.redis_alerts import alert_manager
from core.models import TemporalQuery
from supabase import create_client, Client


class CineGraphAgent:
    """
    AI-powered agent for story consistency validation, querying, and analysis.
    Enhanced with advanced Cypher capabilities, query optimization, and schema awareness.
    """
    
    def __init__(self, graphiti_manager=None, openai_api_key: str = None, supabase_url: str = None, supabase_key: str = None):
        self.graphiti_manager = graphiti_manager
        
        # Initialize OpenAI client if API key is provided
        if openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            
        # Initialize Supabase client if URL and key are provided
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
            
        self.model = "gpt-4-turbo-preview"
        
        # Enhanced capabilities
        self.schema_context = self._load_schema_context()
        self.query_cache = {}  # Cache for frequently used queries
        self.query_templates = self._build_query_templates()
        self.dangerous_operations = {'DELETE', 'DROP', 'CREATE', 'MERGE', 'SET', 'REMOVE', 'DETACH'}
        
        self.system_prompt = self._build_enhanced_system_prompt()
        self.tool_schemas = self._build_enhanced_tool_schemas()
        self._setup_redis_alerts()
    
    def _load_schema_context(self) -> Dict[str, Any]:
        """Load and parse the CineGraph schema for enhanced query generation."""
        schema = {
            "entities": [
                {
                    "name": "Character",
                    "properties": {
                        "character_id": {"type": "string", "unique": True},
                        "name": {"type": "string", "unique": True},
                        "description": "string",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal",
                        "deleted_at": "temporal"
                    }
                },
                {
                    "name": "Knowledge",
                    "properties": {
                        "knowledge_id": {"type": "string", "unique": True},
                        "content": "string",
                        "story_id": "string",
                        "user_id": "string",
                        "valid_from": "temporal",
                        "valid_to": "temporal",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "name": "Scene",
                    "properties": {
                        "scene_id": {"type": "string", "unique": True},
                        "name": "string",
                        "content": "string",
                        "story_id": "string",
                        "user_id": "string",
                        "scene_order": {"type": "integer", "sequential": True},
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "name": "Location",
                    "properties": {
                        "location_id": {"type": "string", "unique": True},
                        "name": {"type": "string", "unique": True},
                        "details": "string",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                }
            ],
            "relationships": [
                {
                    "type": "KNOWS",
                    "from": "Character",
                    "to": "Knowledge",
                    "properties": {
                        "intensity": "integer",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "type": "RELATIONSHIP",
                    "from": "Character",
                    "to": "Character",
                    "properties": {
                        "relationship_type": "string",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "type": "PRESENT_IN",
                    "from": "Character",
                    "to": "Scene",
                    "properties": {
                        "appearance_order": "integer",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "type": "OCCURS_IN",
                    "from": "Scene",
                    "to": "Location",
                    "properties": {
                        "event_time": "temporal",
                        "story_id": "string",
                        "user_id": "string"
                    }
                },
                {
                    "type": "CONTRADICTS",
                    "from": "Knowledge",
                    "to": "Knowledge",
                    "properties": {
                        "severity": "string",
                        "reason": "string",
                        "confidence": "float",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                },
                {
                    "type": "IMPLIES",
                    "from": "Knowledge",
                    "to": "Knowledge",
                    "properties": {
                        "certainty": "integer",
                        "story_id": "string",
                        "user_id": "string",
                        "created_at": "temporal",
                        "updated_at": "temporal"
                    }
                }
            ]
        }
        return schema
    
    def _build_query_templates(self) -> Dict[str, str]:
        """Build reusable Cypher query templates for common operations."""
        return {
            "character_knowledge_at_time": """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k.valid_from <= $timestamp
                AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)
                RETURN k
                ORDER BY k.valid_from DESC
            """,
            "characters_in_scene": """
                MATCH (c:Character)-[:PRESENT_IN]->(s:Scene {scene_id: $scene_id, story_id: $story_id})
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                RETURN c
                ORDER BY c.name
            """,
            "scene_location": """
                MATCH (s:Scene {scene_id: $scene_id, story_id: $story_id})-[:OCCURS_IN]->(l:Location)
                WHERE ($user_id IS NULL OR s.user_id = $user_id)
                RETURN l
            """,
            "character_relationships": """
                MATCH (c1:Character {name: $character_name, story_id: $story_id})-[r:RELATIONSHIP]->(c2:Character)
                WHERE ($user_id IS NULL OR c1.user_id = $user_id)
                RETURN c2, r.relationship_type as relationship_type
                ORDER BY r.created_at DESC
            """,
            "temporal_knowledge_conflicts": """
                MATCH (c:Character {story_id: $story_id})-[:KNOWS]->(k1:Knowledge)
                MATCH (c)-[:KNOWS]->(k2:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k1.knowledge_id <> k2.knowledge_id
                AND k1.valid_from > k2.valid_to
                AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
                RETURN c, k1, k2
            """,
            "story_timeline": """
                MATCH (s:Scene {story_id: $story_id})
                WHERE ($user_id IS NULL OR s.user_id = $user_id)
                OPTIONAL MATCH (s)-[:OCCURS_IN]->(l:Location)
                RETURN s, l
                ORDER BY s.scene_order ASC
            """,
            "knowledge_propagation": """
                MATCH (k1:Knowledge {story_id: $story_id})-[:IMPLIES]->(k2:Knowledge)
                WHERE ($user_id IS NULL OR k1.user_id = $user_id)
                RETURN k1, k2
                ORDER BY k1.created_at
            """
        }
    
    def _build_enhanced_system_prompt(self) -> str:
        """Build enhanced system prompt with comprehensive schema and capabilities."""
        schema_json = json.dumps(self.schema_context, indent=2)
        
        return f"""
        You are CineGraphAgent, an advanced AI assistant specialized in story analysis, consistency validation, and temporal reasoning.
        You have enhanced Cypher query capabilities and deep knowledge of the CineGraph schema.
        
        GRAPH SCHEMA:
        {schema_json}
        
        AVAILABLE TOOLS:
        1. graph_query: Execute Cypher queries against the story knowledge graph
        2. narrative_context: Retrieve raw scene text for analysis
        3. optimized_query: Execute optimized queries using templates
        4. validate_query: Validate Cypher queries before execution
        
        CYPHER QUERY CAPABILITIES:
        - You can write custom Cypher queries using the provided schema
        - Always include story_id and user_id filters for data isolation
        - Use temporal constraints for time-based queries
        - Leverage relationship patterns for complex analysis
        
        COMMON PATTERNS:
        - Character knowledge: (c:Character)-[:KNOWS]->(k:Knowledge)
        - Scene presence: (c:Character)-[:PRESENT_IN]->(s:Scene)
        - Location mapping: (s:Scene)-[:OCCURS_IN]->(l:Location)
        - Character relationships: (c1:Character)-[:RELATIONSHIP]->(c2:Character)
        - Knowledge contradictions: (k1:Knowledge)-[:CONTRADICTS]->(k2:Knowledge)
        - Knowledge implications: (k1:Knowledge)-[:IMPLIES]->(k2:Knowledge)
        
        TEMPORAL QUERY EXAMPLES:
        - "What did character X know at time Y?"
          MATCH (c:Character {{name: $character_name, story_id: $story_id}})-[:KNOWS]->(k:Knowledge)
          WHERE k.valid_from <= $timestamp AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)
          RETURN k
        
        - "What events occurred before character X learned about Y?"
          MATCH (c:Character {{name: $character_name, story_id: $story_id}})-[:KNOWS]->(k:Knowledge {{content: $knowledge_content}})
          MATCH (s:Scene {{story_id: $story_id}})
          WHERE s.created_at < k.valid_from
          RETURN s
        
        CONSISTENCY VALIDATION:
        - Look for temporal contradictions (events occurring out of order)
        - Check character knowledge consistency (characters knowing things they shouldn't)
        - Validate location consistency (characters being in multiple places)
        - Ensure relationship consistency (conflicting relationships)
        - Detect knowledge conflicts and implications
        
        QUERY OPTIMIZATION:
        - Use query templates for common operations
        - Cache frequently used queries
        - Add appropriate indexes and constraints
        - Optimize for story_id and user_id filtering
        
        SAFETY GUIDELINES:
        - Only use READ operations (MATCH, RETURN, WHERE, ORDER BY, LIMIT)
        - Never use destructive operations (DELETE, DROP, CREATE, MERGE, SET, REMOVE)
        - Always include proper data isolation filters
        - Validate queries before execution
        
        Always provide detailed explanations for your findings and assign appropriate severity levels.
        Use the enhanced capabilities to provide deeper insights and more accurate analysis.
        """
    
    def _build_enhanced_tool_schemas(self) -> List[Dict[str, Any]]:
        """Build enhanced OpenAI function schemas for available tools."""
        return [
            {
                "name": "graph_query",
                "description": "Execute a validated Cypher query against the story knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cypher_query": {
                            "type": "string",
                            "description": "The Cypher query to execute (will be validated for safety)"
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the query",
                            "properties": {},
                            "additionalProperties": True
                        },
                        "use_cache": {
                            "type": "boolean",
                            "description": "Whether to use query caching (default: true)",
                            "default": True
                        }
                    },
                    "required": ["cypher_query"]
                }
            },
            {
                "name": "optimized_query",
                "description": "Execute an optimized query using predefined templates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Name of the query template to use",
                            "enum": ["character_knowledge_at_time", "characters_in_scene", "scene_location", 
                                   "character_relationships", "temporal_knowledge_conflicts", "story_timeline", 
                                   "knowledge_propagation"]
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the template query",
                            "properties": {},
                            "additionalProperties": True
                        }
                    },
                    "required": ["template_name", "params"]
                }
            },
            {
                "name": "validate_query",
                "description": "Validate a Cypher query for safety and correctness before execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cypher_query": {
                            "type": "string",
                            "description": "The Cypher query to validate"
                        }
                    },
                    "required": ["cypher_query"]
                }
            },
            {
                "name": "narrative_context",
                "description": "Retrieve raw scene text for a given story",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "string",
                            "description": "The story identifier"
                        },
                        "scene_id": {
                            "type": "string",
                            "description": "Optional scene identifier for specific scene text"
                        }
                    },
                    "required": ["story_id"]
                }
            }
        ]
    
    def _setup_redis_alerts(self):
        """Setup Redis alerts listener for processing contradiction alerts."""
        alert_manager.add_alert_handler("cinegraph_agent", self._handle_alert)
    
    async def validate_cypher_query(self, cypher_query: str) -> Tuple[bool, str]:
        """Validate a Cypher query for safety and correctness."""
        try:
            # Check for dangerous operations
            query_upper = cypher_query.upper()
            for dangerous_op in self.dangerous_operations:
                if dangerous_op in query_upper:
                    return False, f"Dangerous operation '{dangerous_op}' detected. Only read operations are allowed."
            
            # Check for required data isolation filters
            if 'story_id' not in cypher_query.lower() and '$story_id' not in cypher_query.lower():
                return False, "Query must include story_id filter for data isolation"
            
            # Basic syntax validation
            if not cypher_query.strip():
                return False, "Query cannot be empty"
            
            # Check for balanced parentheses and brackets
            if cypher_query.count('(') != cypher_query.count(')'):
                return False, "Unbalanced parentheses in query"
            
            if cypher_query.count('[') != cypher_query.count(']'):
                return False, "Unbalanced brackets in query"
            
            # Check for proper MATCH/RETURN structure
            if 'MATCH' not in query_upper and 'RETURN' not in query_upper:
                return False, "Query must contain MATCH and RETURN clauses"
            
            return True, "Query validation passed"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _generate_query_hash(self, cypher_query: str, params: dict) -> str:
        """Generate a hash for query caching."""
        query_string = f"{cypher_query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(query_string.encode()).hexdigest()
    
    async def _optimize_query(self, cypher_query: str) -> str:
        """Optimize a Cypher query for better performance."""
        # Add common optimizations
        optimized_query = cypher_query
        
        # Add index hints for common patterns
        if 'story_id' in optimized_query and 'WHERE' in optimized_query.upper():
            # Query is already likely optimized with story_id filter
            pass
        
        # Add LIMIT if not present and query might return many results
        if 'LIMIT' not in optimized_query.upper() and 'COUNT' not in optimized_query.upper():
            if any(pattern in optimized_query.upper() for pattern in ['MATCH (', 'OPTIONAL MATCH']):
                optimized_query += " LIMIT 1000"  # Safety limit
        
        return optimized_query
    
    async def graph_query(self, cypher_query: str, params: dict = None, use_cache: bool = True) -> dict:
        """Execute a validated Cypher query via GraphitiManager with caching."""
        try:
            if params is None:
                params = {}
            
            # Validate the query first
            is_valid, validation_message = await self.validate_cypher_query(cypher_query)
            if not is_valid:
                return {"success": False, "error": f"Query validation failed: {validation_message}"}
            
            # Check cache if enabled
            if use_cache:
                query_hash = self._generate_query_hash(cypher_query, params)
                if query_hash in self.query_cache:
                    return {"success": True, "data": self.query_cache[query_hash], "cached": True}
            
            # Optimize the query
            optimized_query = await self._optimize_query(cypher_query)
            
            # Execute the query
            result = await self.graphiti_manager.client.query(optimized_query, params)
            
            # Cache the result if enabled
            if use_cache:
                query_hash = self._generate_query_hash(cypher_query, params)
                self.query_cache[query_hash] = result
                # Limit cache size to prevent memory issues
                if len(self.query_cache) > 100:
                    # Remove oldest entries
                    oldest_keys = list(self.query_cache.keys())[:20]
                    for key in oldest_keys:
                        del self.query_cache[key]
            
            return {"success": True, "data": result, "cached": False}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def optimized_query(self, template_name: str, params: dict) -> dict:
        """Execute an optimized query using predefined templates."""
        try:
            if template_name not in self.query_templates:
                return {"success": False, "error": f"Unknown template: {template_name}"}
            
            template_query = self.query_templates[template_name]
            
            # Execute using the template
            result = await self.graph_query(template_query, params, use_cache=True)
            
            return {
                "success": result["success"],
                "data": result.get("data"),
                "template_used": template_name,
                "cached": result.get("cached", False),
                "error": result.get("error")
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_query(self, cypher_query: str) -> dict:
        """Validate a Cypher query and return validation results."""
        is_valid, message = await self.validate_cypher_query(cypher_query)
        
        return {
            "valid": is_valid,
            "message": message,
            "suggested_optimizations": self._get_query_suggestions(cypher_query) if is_valid else []
        }
    
    def _get_query_suggestions(self, cypher_query: str) -> List[str]:
        """Provide optimization suggestions for a query."""
        suggestions = []
        
        query_upper = cypher_query.upper()
        
        # Check for common optimization opportunities
        if 'LIMIT' not in query_upper and 'COUNT' not in query_upper:
            suggestions.append("Consider adding a LIMIT clause to prevent large result sets")
        
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            suggestions.append("ORDER BY without LIMIT can be expensive - consider adding LIMIT")
        
        if 'user_id' not in cypher_query.lower():
            suggestions.append("Consider adding user_id filter for better data isolation")
        
        if cypher_query.count('MATCH') > 3:
            suggestions.append("Complex query with multiple MATCH clauses - consider breaking into smaller queries")
        
        return suggestions
    
    async def narrative_context(self, story_id: str, scene_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Return raw scene text for a given story ID."""
        try:
            if scene_id:
                # Query specific scene
                query = "MATCH (s:Scene {id: $scene_id, story_id: $story_id}) WHERE ($user_id IS NULL OR s.user_id = $user_id) RETURN s.content as content"
                params = {"scene_id": scene_id, "story_id": story_id, "user_id": user_id}
            else:
                # Query all scenes for the story
                query = "MATCH (s:Scene {story_id: $story_id}) WHERE ($user_id IS NULL OR s.user_id = $user_id) RETURN s.content as content ORDER BY s.sequence"
                params = {"story_id": story_id, "user_id": user_id}
            
            result = await self.graphiti_manager.client.query(query, params)
            
            if result:
                scenes = [r["content"] for r in result]
                return "\n\n".join(scenes)
            else:
                return f"No scene content found for story {story_id}"
                
        except Exception as e:
            return f"Error retrieving narrative context: {str(e)}"
    
    async def initialize(self) -> None:
        """Initialize the CineGraph Agent."""
        # Start Redis alerts listener
        await alert_manager.start_listening()
        print("CineGraph Agent initialized and listening for alerts.")
    
    async def analyze_story(self, content: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze story content and provide insights using OpenAI SDK.
        
        Args:
            content: Raw story content
            extracted_data: Processed story data with entities and relationships
            
        Returns:
            Dict containing analysis insights
        """
        try:
            story_id = extracted_data.get("story_id", "unknown")
            
            # Return basic analysis if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "analysis": "OpenAI client not configured. Basic analysis:",
                    "entity_count": len(extracted_data.get("entities", [])),
                    "relationship_count": len(extracted_data.get("relationships", [])),
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_analysis"
                }
            
            # Build prompt for story analysis
            analysis_prompt = f"""
            Analyze the following story content and provide insights:
            
            Story Content: {content}
            
            Extracted Data: {json.dumps(extracted_data, indent=2)}
            
            Please provide:
            1. Main themes and genres
            2. Character analysis and roles
            3. Story complexity score (0-1)
            4. Temporal structure analysis
            5. Potential inconsistencies or plot holes
            
            Use the available tools to query the knowledge graph for additional context.
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls if any
            if response.choices[0].message.function_call:
                function_result = await self._execute_function_call(
                    response.choices[0].message.function_call,
                    story_id
                )
                
                # Continue conversation with function result
                follow_up_response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": analysis_prompt},
                        {"role": "assistant", "content": response.choices[0].message.content, "function_call": response.choices[0].message.function_call.model_dump()},
                        {"role": "function", "name": response.choices[0].message.function_call.name, "content": json.dumps(function_result)}
                    ]
                )
                analysis_result = follow_up_response.choices[0].message.content
            else:
                analysis_result = response.choices[0].message.content
            
            # Parse and structure the analysis result
            return {
                "analysis": analysis_result,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": extracted_data.get("story_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def detect_inconsistencies(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Detect inconsistencies in the story using OpenAI SDK.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing detected inconsistencies
        """
        try:
            # Return basic inconsistency detection if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "inconsistencies": "OpenAI client not configured. Basic inconsistency detection not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_detection"
                }
            
            # Build prompt for inconsistency detection
            detection_prompt = f"""
            Analyze the story with ID '{story_id}' for inconsistencies.
            
            Please perform the following consistency checks:
            1. Temporal consistency - Check for events out of chronological order
            2. Character knowledge consistency - Verify characters don't know things they shouldn't
            3. Location consistency - Ensure characters aren't in multiple places simultaneously
            4. Relationship consistency - Check for conflicting character relationships
            5. Event sequence consistency - Verify cause-and-effect relationships
            
            Use the graph_query tool to examine the story's knowledge graph and narrative_context to get scene details.
            
            Return a detailed report of any inconsistencies found with:
            - Type of inconsistency
            - Severity level (low, medium, high, critical)
            - Specific examples
            - Suggested fixes
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": detection_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "inconsistencies": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def query_story(self, story_id: str, question: str, user_id: str) -> Dict[str, Any]:
        """
        Query the story using a natural language question with OpenAI SDK.
        
        Args:
            story_id: Story identifier
            question: Natural language question
            user_id: User ID for data isolation
            
        Returns:
            Dict containing query response
        """
        try:
            # Return basic query response if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "answer": "OpenAI client not configured. Basic query processing not available.",
                    "question": question,
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_query"
                }
            
            # Build prompt for story querying
            query_prompt = f"""
            Answer the following question about the story with ID '{story_id}':
            
            Question: {question}
            
            Use the available tools to:
            1. Query the knowledge graph for relevant information
            2. Retrieve narrative context for detailed analysis
            3. Consider temporal aspects if the question involves "when" or "what did X know at Y"
            
            Provide a comprehensive answer with:
            - Direct answer to the question
            - Supporting evidence from the story
            - Confidence level (0-1)
            - Relevant quotes or references
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "answer": final_response,
                "question": question,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "question": question,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def validate_story_consistency(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Validate the consistency of the entire story using OpenAI SDK.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing validation report
        """
        try:
            # Return basic validation if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "validation_report": "OpenAI client not configured. Basic validation not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_validation"
                }
            
            # Build prompt for comprehensive story validation
            validation_prompt = f"""
            Perform a comprehensive consistency validation of the story with ID '{story_id}'.
            
            Please analyze:
            1. Overall story coherence and logical flow
            2. Character consistency throughout the narrative
            3. Timeline and temporal consistency
            4. Plot coherence and cause-effect relationships
            5. Setting and world-building consistency
            6. Dialogue and character voice consistency
            
            Use the available tools to:
            - Query the knowledge graph for character relationships and events
            - Retrieve narrative context for detailed scene analysis
            - Perform temporal queries to check chronological consistency
            
            Provide a comprehensive validation report with:
            - Overall consistency score (0-1)
            - Summary of findings
            - Detailed breakdown by category
            - Specific issues found with severity levels
            - Recommendations for improvement
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": validation_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "validation_report": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the CineGraph Agent."""
        try:
            # Test OpenAI connection
            test_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            
            # Test Supabase connection
            supabase_health = self.supabase.table("alerts").select("count").execute()
            
            # Test GraphitiManager connection
            graphiti_health = await self.graphiti_manager.health_check()
            
            return {
                "status": "healthy",
                "components": {
                    "openai": "connected",
                    "supabase": "connected",
                    "graphiti": graphiti_health["status"],
                    "redis_alerts": "listening" if alert_manager.is_listening else "not_listening"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_function_call(self, function_call, story_id: str) -> Any:
        """Execute a function call from OpenAI with enhanced tool support."""
        function_name = function_call.name
        function_args = json.loads(function_call.arguments)
        
        if function_name == "graph_query":
            return await self.graph_query(
                function_args.get("cypher_query"),
                function_args.get("params", {}),
                function_args.get("use_cache", True)
            )
        elif function_name == "optimized_query":
            return await self.optimized_query(
                function_args.get("template_name"),
                function_args.get("params", {})
            )
        elif function_name == "validate_query":
            return await self.validate_query(
                function_args.get("cypher_query")
            )
        elif function_name == "narrative_context":
            return await self.narrative_context(
                function_args.get("story_id", story_id),
                function_args.get("scene_id")
            )
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def _process_function_calls(self, response, story_id: str) -> str:
        """Process function calls in OpenAI response."""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        current_response = response
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while (current_response.choices[0].message.function_call and 
               iteration < max_iterations):
            
            function_call = current_response.choices[0].message.function_call
            function_result = await self._execute_function_call(function_call, story_id)
            
            # Add messages to conversation
            messages.append({
                "role": "assistant",
                "content": current_response.choices[0].message.content,
                "function_call": function_call.model_dump()
            })
            messages.append({
                "role": "function",
                "name": function_call.name,
                "content": json.dumps(function_result)
            })
            
            # Continue conversation
            current_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            iteration += 1
        
        return current_response.choices[0].message.content
    
    async def _handle_alert(self, alert_data: Dict[str, Any]):
        """Handle incoming Redis alert by enriching and storing in Supabase."""
        try:
            # Enrich alert with explanation using OpenAI
            enrichment_prompt = f"""
            Analyze this contradiction alert and provide:
            1. Detailed explanation of the inconsistency
            2. Severity assessment (low, medium, high, critical)
            3. Potential impact on story coherence
            4. Suggested resolution steps
            
            Alert Data: {json.dumps(alert_data, indent=2)}
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enrichment_prompt}
                ],
                max_tokens=500
            )
            
            explanation = response.choices[0].message.content
            
            # Determine severity based on alert data
            severity = self._assess_alert_severity(alert_data)
            
            # Create enriched alert for Supabase
            enriched_alert = {
                "id": alert_data.get("id", f"alert_{datetime.utcnow().isoformat()}"),
                "story_id": alert_data.get("story_id"),
                "alert_type": alert_data.get("alert_type", "contradiction_detected"),
                "severity": severity,
                "explanation": explanation,
                "original_alert": alert_data,
                "detected_at": alert_data.get("timestamp", datetime.utcnow().isoformat()),
                "enriched_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Store in Supabase realtime table
            result = self.supabase.table("alerts").insert(enriched_alert).execute()
            
            print(f"Alert enriched and stored: {enriched_alert['id']}")
            
        except Exception as e:
            print(f"Error handling alert: {str(e)}")
    
    def _assess_alert_severity(self, alert_data: Dict[str, Any]) -> str:
        """Assess the severity of an alert based on its data."""
        # Basic severity assessment logic
        reason = alert_data.get("reason", "").lower()
        
        if any(keyword in reason for keyword in ["critical", "major", "severe"]):
            return "critical"
        elif any(keyword in reason for keyword in ["significant", "important", "conflict"]):
            return "high"
        elif any(keyword in reason for keyword in ["minor", "inconsistent", "unclear"]):
            return "medium"
        else:
            return "low"
    
    # === ADVANCED ANALYSIS METHODS ===
    
    async def analyze_story_timeline(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """Analyze the story timeline for temporal consistency and flow."""
        try:
            # Use optimized query for timeline analysis
            timeline_result = await self.optimized_query(
                "story_timeline",
                {"story_id": story_id, "user_id": user_id}
            )
            
            if not timeline_result["success"]:
                return {"error": timeline_result["error"]}
            
            # Analyze temporal knowledge conflicts
            conflicts_result = await self.optimized_query(
                "temporal_knowledge_conflicts",
                {"story_id": story_id, "user_id": user_id}
            )
            
            timeline_data = timeline_result["data"]
            conflicts_data = conflicts_result.get("data", [])
            
            # Generate comprehensive analysis
            analysis = {
                "story_id": story_id,
                "total_scenes": len(timeline_data),
                "temporal_conflicts": len(conflicts_data),
                "scenes": timeline_data,
                "conflicts": conflicts_data,
                "timeline_coherence": "good" if len(conflicts_data) == 0 else "needs_attention",
                "recommendations": self._generate_timeline_recommendations(timeline_data, conflicts_data)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_character_consistency(self, story_id: str, character_name: str, user_id: str) -> Dict[str, Any]:
        """Analyze character consistency across the story."""
        try:
            # Get character relationships
            relationships_result = await self.optimized_query(
                "character_relationships",
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Get character knowledge evolution
            knowledge_query = """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                RETURN k
                ORDER BY k.valid_from ASC
            """
            
            knowledge_result = await self.graph_query(
                knowledge_query,
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Check for knowledge contradictions
            contradictions_query = """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[:KNOWS]->(k1:Knowledge)
                MATCH (c)-[:KNOWS]->(k2:Knowledge)
                WHERE k1.knowledge_id <> k2.knowledge_id
                AND EXISTS((k1)-[:CONTRADICTS]->(k2))
                RETURN k1, k2
            """
            
            contradictions_result = await self.graph_query(
                contradictions_query,
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Compile analysis
            return {
                "character_name": character_name,
                "story_id": story_id,
                "relationships": relationships_result.get("data", []),
                "knowledge_evolution": knowledge_result.get("data", []),
                "contradictions": contradictions_result.get("data", []),
                "consistency_score": self._calculate_character_consistency_score(
                    relationships_result.get("data", []),
                    knowledge_result.get("data", []),
                    contradictions_result.get("data", [])
                ),
                "recommendations": self._generate_character_recommendations(
                    character_name,
                    contradictions_result.get("data", [])
                )
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def detect_plot_holes(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """Detect potential plot holes using advanced graph analysis."""
        try:
            # Use custom query to find logical inconsistencies
            plot_hole_query = """
                MATCH (c:Character {story_id: $story_id})-[:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND NOT EXISTS {
                    MATCH (c)-[:PRESENT_IN]->(s:Scene)
                    WHERE s.created_at <= k.valid_from
                }
                RETURN c.name as character, k.content as knowledge, 
                       'impossible_knowledge' as issue_type,
                       'Character knows something without being present when it happened' as description
                
                UNION
                
                MATCH (c:Character {story_id: $story_id})-[:PRESENT_IN]->(s1:Scene)-[:OCCURS_IN]->(l1:Location)
                MATCH (c)-[:PRESENT_IN]->(s2:Scene)-[:OCCURS_IN]->(l2:Location)
                WHERE s1.scene_order = s2.scene_order AND l1.location_id <> l2.location_id
                RETURN c.name as character, l1.name as location1, l2.name as location2,
                       'location_contradiction' as issue_type,
                       'Character cannot be in two places at once' as description
            """
            
            plot_holes_result = await self.graph_query(
                plot_hole_query,
                {"story_id": story_id, "user_id": user_id}
            )
            
            plot_holes = plot_holes_result.get("data", [])
            
            # Categorize plot holes by severity
            categorized_holes = self._categorize_plot_holes(plot_holes)
            
            return {
                "story_id": story_id,
                "total_plot_holes": len(plot_holes),
                "plot_holes_by_severity": categorized_holes,
                "detailed_analysis": plot_holes,
                "overall_coherence_score": self._calculate_coherence_score(plot_holes),
                "recommendations": self._generate_plot_hole_recommendations(plot_holes)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # === HELPER METHODS FOR ANALYSIS ===
    
    def _generate_timeline_recommendations(self, timeline_data: List[Dict], conflicts_data: List[Dict]) -> List[str]:
        """Generate recommendations for timeline improvements."""
        recommendations = []
        
        if len(conflicts_data) > 0:
            recommendations.append(f"Resolve {len(conflicts_data)} temporal conflicts in the story")
        
        if len(timeline_data) > 50:
            recommendations.append("Consider breaking the story into chapters for better organization")
        
        return recommendations
    
    def _calculate_character_consistency_score(self, relationships: List, knowledge: List, contradictions: List) -> float:
        """Calculate a consistency score for a character."""
        base_score = 1.0
        
        # Deduct for contradictions
        contradiction_penalty = len(contradictions) * 0.1
        
        # Bonus for rich character development
        development_bonus = min(len(knowledge) * 0.02, 0.2)
        
        score = max(0.0, base_score - contradiction_penalty + development_bonus)
        return min(1.0, score)
    
    def _generate_character_recommendations(self, character_name: str, contradictions: List) -> List[str]:
        """Generate recommendations for character consistency."""
        recommendations = []
        
        if len(contradictions) > 0:
            recommendations.append(f"Resolve {len(contradictions)} knowledge contradictions for {character_name}")
        
        return recommendations
    
    def _categorize_plot_holes(self, plot_holes: List) -> Dict[str, List]:
        """Categorize plot holes by severity."""
        categories = {"critical": [], "major": [], "minor": []}
        
        for hole in plot_holes:
            issue_type = hole.get("issue_type", "unknown")
            if issue_type == "temporal_paradox":
                categories["critical"].append(hole)
            elif issue_type == "location_contradiction":
                categories["major"].append(hole)
            else:
                categories["minor"].append(hole)
        
        return categories
    
    def _calculate_coherence_score(self, plot_holes: List) -> float:
        """Calculate overall story coherence score."""
        if not plot_holes:
            return 1.0
        
        # Simple scoring based on number and severity of plot holes
        critical_holes = sum(1 for hole in plot_holes if hole.get("issue_type") == "temporal_paradox")
        major_holes = sum(1 for hole in plot_holes if hole.get("issue_type") == "location_contradiction")
        minor_holes = len(plot_holes) - critical_holes - major_holes
        
        penalty = (critical_holes * 0.3) + (major_holes * 0.2) + (minor_holes * 0.1)
        return max(0.0, 1.0 - penalty)
    
    def _generate_plot_hole_recommendations(self, plot_holes: List) -> List[str]:
        """Generate recommendations for fixing plot holes."""
        recommendations = []
        
        categorized = self._categorize_plot_holes(plot_holes)
        
        if categorized["critical"]:
            recommendations.append(f"Address {len(categorized['critical'])} critical plot holes immediately")
        
        if categorized["major"]:
            recommendations.append(f"Review {len(categorized['major'])} major inconsistencies")
        
        if categorized["minor"]:
            recommendations.append(f"Consider resolving {len(categorized['minor'])} minor issues")
        
        return recommendations
