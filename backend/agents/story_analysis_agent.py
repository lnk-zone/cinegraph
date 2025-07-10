"""OpenAI interaction logic for story analysis."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional


class StoryAnalysisAgent:
    """Mixin providing OpenAI driven story analysis features."""

    async def _execute_function_call(self, function_call, story_id: str) -> Any:
        function_name = function_call.name
        function_args = json.loads(function_call.arguments)
        if function_name == "graph_query":
            return await self.graph_query(
                function_args.get("cypher_query"),
                function_args.get("params", {}),
                function_args.get("use_cache", True),
            )
        if function_name == "optimized_query":
            return await self.optimized_query(
                function_args.get("template_name"),
                function_args.get("params", {}),
            )
        if function_name == "validate_query":
            return await self.validate_query(function_args.get("cypher_query"))
        if function_name == "narrative_context":
            return await self.narrative_context(
                function_args.get("story_id", story_id),
                function_args.get("scene_id"),
            )
        return {"error": f"Unknown function: {function_name}"}

    async def _process_function_calls(self, response, story_id: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        current_response = response
        max_iterations = 5
        iteration = 0
        while current_response.choices[0].message.function_call and iteration < max_iterations:
            function_call = current_response.choices[0].message.function_call
            function_result = await self._execute_function_call(function_call, story_id)
            messages.append({"role": "assistant", "content": current_response.choices[0].message.content, "function_call": function_call.model_dump()})
            messages.append({"role": "function", "name": function_call.name, "content": json.dumps(function_result)})
            current_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self.tool_schemas,
                function_call="auto",
            )
            iteration += 1
        return current_response.choices[0].message.content

    async def analyze_story(self, content: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            story_id = extracted_data.get("story_id", "unknown")
            if not self.openai_client:
                return {
                    "analysis": "OpenAI client not configured. Basic analysis:",
                    "entity_count": len(extracted_data.get("entities", [])),
                    "relationship_count": len(extracted_data.get("relationships", [])),
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_analysis",
                }
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
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": analysis_prompt}],
                functions=self.tool_schemas,
                function_call="auto",
            )
            final_response = await self._process_function_calls(response, story_id)
            return {
                "analysis": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model,
            }
        except Exception as e:
            return {"error": str(e), "story_id": story_id, "timestamp": datetime.utcnow().isoformat()}

    async def detect_inconsistencies(self, story_id: str, user_id: str) -> Dict[str, Any]:
        try:
            if not self.openai_client:
                return {
                    "inconsistencies": "OpenAI client not configured. Basic inconsistency detection not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_detection",
                }
            detection_prompt = f"""
            Analyze the story with ID '{story_id}' for inconsistencies.

            Please perform the following consistency checks:
            1. Temporal consistency - Check for events out of chronological order
            2. Character knowledge consistency - Verify characters don't know things they shouldn't
            3. Location consistency - Ensure characters aren't in multiple places simultaneously
            4. Relationship consistency - Check for conflicting character relationships
            5. Event sequence consistency - Verify cause-and-effect relationships

            Use the graph_query tool to examine the story's knowledge graph and narrative_context to get scene details.
            """
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": detection_prompt}],
                functions=self.tool_schemas,
                function_call="auto",
            )
            final_response = await self._process_function_calls(response, story_id)
            return {
                "inconsistencies": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model,
            }
        except Exception as e:
            return {"error": str(e), "story_id": story_id, "timestamp": datetime.utcnow().isoformat()}

    async def query_story(self, story_id: str, question: str, user_id: str) -> Dict[str, Any]:
        try:
            if not self.openai_client:
                return {
                    "answer": "OpenAI client not configured. Basic query processing not available.",
                    "question": question,
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_query",
                }
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
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": query_prompt}],
                functions=self.tool_schemas,
                function_call="auto",
            )
            final_response = await self._process_function_calls(response, story_id)
            return {
                "answer": final_response,
                "question": question,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model,
            }
        except Exception as e:
            return {"error": str(e), "question": question, "story_id": story_id, "timestamp": datetime.utcnow().isoformat()}

    async def validate_story_consistency(self, story_id: str, user_id: str) -> Dict[str, Any]:
        try:
            if not self.openai_client:
                return {
                    "validation_report": "OpenAI client not configured. Basic validation not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_validation",
                }
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
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": validation_prompt}],
                functions=self.tool_schemas,
                function_call="auto",
            )
            final_response = await self._process_function_calls(response, story_id)
            return {
                "validation_report": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model,
            }
        except Exception as e:
            return {"error": str(e), "story_id": story_id, "timestamp": datetime.utcnow().isoformat()}

    async def narrative_context(self, story_id: str, scene_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        try:
            session_id = self.graphiti_manager._story_sessions.get(story_id)
            if not session_id:
                return f"No active session found for story {story_id}. Consider adding content first."
            if scene_id:
                search_results = await self.graphiti_manager.client.search(
                    query=f"scene {scene_id}",
                    group_ids=[session_id],
                    num_results=10,
                )
                if search_results:
                    scene_content = []
                    for result in search_results:
                        content = getattr(result, "episode_body", getattr(result, "fact", ""))
                        if content and scene_id.lower() in content.lower():
                            scene_content.append(content)
                    return "\n\n".join(scene_content) if scene_content else f"No content found for scene {scene_id}"
                return f"No content found for scene {scene_id}"
            episodes = await self.graphiti_manager.client.retrieve_episodes(
                reference_time=datetime.utcnow(),
                last_n=100,
                group_ids=[session_id],
            )
            if episodes:
                sorted_episodes = sorted(episodes, key=lambda ep: getattr(ep, "created_at", datetime.min))
                narrative_content = []
                for episode in sorted_episodes:
                    content = getattr(episode, "episode_body", "")
                    if content and "Story Content:" in content:
                        story_part = content.split("Story Content:")[1].split("\n\nEntities:")[0].strip()
                        if story_part:
                            narrative_content.append(story_part)
                    elif content:
                        narrative_content.append(content)
                return "\n\n".join(narrative_content) if narrative_content else f"No narrative content found for story {story_id}"
            return f"No episodes found for story {story_id}"
        except Exception as e:
            return f"Error retrieving narrative context via episodic APIs: {e}"

    async def health_check(self) -> Dict[str, Any]:
        try:
            test_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10,
            )
            supabase_health = self.supabase.table("alerts").select("count").execute()
            graphiti_health = await self.graphiti_manager.health_check()
            episodic_connectivity = False
            try:
                episodes_result = await self.graphiti_manager.client.retrieve_episodes(
                    reference_time=datetime.utcnow(),
                    last_n=1,
                    group_ids=None,
                ) if self.graphiti_manager.client else None
                episodic_connectivity = episodes_result is not None
            except Exception:
                episodic_connectivity = False
            return {
                "status": "healthy",
                "components": {
                    "openai": "connected",
                    "supabase": "connected",
                    "graphiti": graphiti_health["status"],
                    "episodic_api": "connected" if episodic_connectivity else "degraded",
                    "redis_alerts": "listening" if alert_manager.is_listening else "not_listening",
                },
                "graphiti_details": graphiti_health,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Health check using episodic APIs",
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
