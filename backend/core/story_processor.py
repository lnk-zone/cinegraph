"""
Story Processor Module
=====================

This module handles the processing of story content to extract entities,
relationships, and other structured data for the knowledge graph.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
import uuid
import re
import json
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search import SearchConfig
from neo4j import AsyncGraphDatabase

from .graphiti_manager import GraphitiManager
from .models import EntityType, RelationshipType, ContinuityEdge


class StoryProcessor:
    """
    Processes story content to extract structured data for the knowledge graph.
    Implements story ingestion pipeline with Graphiti's /extract endpoint.
    """
    
    def __init__(self, graphiti_manager: Optional[GraphitiManager] = None, cinegraph_agent=None):
        """Initialize the story processor.
        
        Args:
            graphiti_manager: Optional GraphitiManager instance. If None, creates new one.
            cinegraph_agent: CinegraphAgent instance for AI-powered analysis
        """
        self.graphiti_manager = graphiti_manager or GraphitiManager()
        self.cinegraph_agent = cinegraph_agent
        self._scene_mappings: Dict[str, str] = {}  # text_segment_id -> scene_id
        self._processing_stats = {
            "total_processed": 0,
            "avg_processing_time": 0,
            "last_processed": None
        }
    
    async def process_story(self, content: str, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process story content and extract structured data using Graphiti's extraction.
        
        Target: <300ms extraction for 2K words
        
        Args:
            content: Raw story content
            story_id: Unique story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing extracted entities, relationships, and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Split content into manageable scenes/paragraphs
            scenes = self._split_into_scenes(content)
            
            # Step 2: Use CinegraphAgent for enhanced processing if available
            if self.cinegraph_agent:
                extracted_data = await self._process_with_agent(scenes, story_id, user_id)
            else:
                extracted_data = await self._extract_with_graphiti(scenes, story_id, user_id)
            
            # Step 3: Map extraction output to schema and upsert
            await self._map_and_upsert_entities(extracted_data, story_id, user_id)
            
            # Step 4: Store traceability mappings
            self._store_traceability_mappings(scenes, extracted_data)
            
            # Step 5: Fix generic relationships (convert RELATES_TO, etc. to meaningful types)
            fix_results = await self._fix_generic_relationships(story_id)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update processing stats
            self._update_processing_stats(processing_time)
            
            return {
                "entities": extracted_data.get("entities", []),
                "relationships": extracted_data.get("relationships", []),
                "scenes": extracted_data.get("scenes", []),
                "knowledge_items": extracted_data.get("knowledge_items", []),
                "continuity_edges": extracted_data.get("continuity_edges", []),
                "traceability_mappings": dict(self._scene_mappings),
                "metadata": {
                    "word_count": len(content.split()),
                    "scene_count": len(scenes),
                    "processing_time_ms": processing_time,
                    "processed_at": datetime.utcnow().isoformat(),
                    "processing_version": "1.0.0",
                    "story_id": story_id,
                    "scene_errors": extracted_data.get("scene_errors", []),  # Include scene errors
                    "relationship_fixes": fix_results  # Include relationship fixes
                }
            }
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "error": str(e),
                "processing_time_ms": processing_time,
                "processed_at": datetime.utcnow().isoformat(),
                "story_id": story_id
            }
    
    def _split_into_scenes(self, content: str) -> List[Dict[str, Any]]:
        """
        Split content into basic scenes/paragraphs for processing.
        
        Args:
            content: Raw story content
            
        Returns:
            List of scene dictionaries with basic metadata
        """
        # Split by double newlines or scene markers
        paragraphs = re.split(r'\n\s*\n|\n\s*---\s*\n|\n\s*\*\*\*\s*\n', content.strip())
        
        scenes = []
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if paragraph:  # Skip empty paragraphs
                scene_id = f"scene_{i+1}_{uuid.uuid4().hex[:8]}"
                scenes.append({
                    "id": scene_id,
                    "text": paragraph,
                    "order": i + 1,
                    "word_count": len(paragraph.split()),
                    "segment_id": f"segment_{i+1}"
                })
        
        return scenes
    
    async def _process_with_agent(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process scenes using CinegraphAgent for enhanced analysis.
        
        Args:
            scenes: List of scene dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing processed data with enhanced metadata
        """
        try:
            # Use CinegraphAgent to analyze scenes
            agent_analysis = await self.cinegraph_agent.analyze_scenes(
                scenes=scenes,
                story_id=story_id,
                user_id=user_id
            )
            
            return agent_analysis
            
        except Exception as e:
            print(f"Warning: Agent processing failed, falling back to basic extraction: {e}")
            # Fallback to basic extraction if agent fails
            return await self._extract_with_graphiti(scenes, story_id, user_id)
    
    def _detect_chapter_boundaries(self, text: str) -> Dict[str, Any]:
        """
        Detect chapter boundaries using simple NLP heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with chapter boundary information
        """
        chapter_patterns = [
            r'^\s*(chapter|ch\.?)\s+\d+',
            r'^\s*(part|book)\s+\d+',
            r'^\s*\d+\s*$',  # Standalone numbers
            r'^\s*[IVX]+\s*$',  # Roman numerals
        ]
        
        is_new_chapter = any(re.match(pattern, text, re.IGNORECASE) for pattern in chapter_patterns)
        
        # Additional heuristics
        is_title_like = len(text.split()) <= 5 and text.isupper()
        has_time_jump = bool(re.search(r'\b(years? later|months? later|days? later|meanwhile|elsewhere)\b', text, re.IGNORECASE))
        
        return {
            "is_new_chapter": is_new_chapter or is_title_like,
            "confidence": 0.9 if is_new_chapter else (0.7 if is_title_like else 0.3),
            "indicators": {
                "pattern_match": is_new_chapter,
                "title_like": is_title_like,
                "time_jump": has_time_jump
            }
        }
    
    def _detect_episode_boundaries(self, text: str, scene_index: int, total_scenes: int) -> Dict[str, Any]:
        """
        Detect episode boundaries within chapters.
        
        Args:
            text: Text to analyze
            scene_index: Current scene index
            total_scenes: Total number of scenes
            
        Returns:
            Dict with episode boundary information
        """
        episode_indicators = [
            r'\b(scene|act)\s+\d+\b',
            r'\b(cut to|fade to|dissolve to)\b',
            r'\b(meanwhile|elsewhere|at the same time)\b',
            r'\b(hours? later|minutes? later|soon after)\b'
        ]
        
        has_indicator = any(re.search(pattern, text, re.IGNORECASE) for pattern in episode_indicators)
        
        # Heuristic: longer scenes or significant location/POV shifts might be new episodes
        word_count = len(text.split())
        is_long_scene = word_count > 300  # Threshold for scene length
        
        # Natural breakpoints (every 3-5 scenes, depending on length)
        natural_break = scene_index > 0 and scene_index % 4 == 0
        
        is_new_episode = has_indicator or (is_long_scene and natural_break)
        
        return {
            "is_new_episode": is_new_episode,
            "confidence": 0.8 if has_indicator else (0.6 if is_long_scene else 0.4),
            "indicators": {
                "explicit_marker": has_indicator,
                "length_based": is_long_scene,
                "natural_break": natural_break
            }
        }
    
    def _detect_story_arc(self, text: str) -> Dict[str, Any]:
        """
        Detect story arc elements using NLP heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with story arc information
        """
        # Story arc patterns
        exposition_patterns = [r'\b(introduce|meet|background|setting|world)\b']
        rising_action_patterns = [r'\b(conflict|problem|challenge|discover)\b']
        climax_patterns = [r'\b(battle|fight|confrontation|crisis|decisive)\b']
        falling_action_patterns = [r'\b(aftermath|consequence|result|resolve)\b']
        resolution_patterns = [r'\b(end|conclude|peace|happy|reunion)\b']
        
        arc_scores = {
            "exposition": sum(len(re.findall(p, text, re.IGNORECASE)) for p in exposition_patterns),
            "rising_action": sum(len(re.findall(p, text, re.IGNORECASE)) for p in rising_action_patterns),
            "climax": sum(len(re.findall(p, text, re.IGNORECASE)) for p in climax_patterns),
            "falling_action": sum(len(re.findall(p, text, re.IGNORECASE)) for p in falling_action_patterns),
            "resolution": sum(len(re.findall(p, text, re.IGNORECASE)) for p in resolution_patterns)
        }
        
        # Determine primary arc element
        primary_arc = max(arc_scores, key=arc_scores.get) if any(arc_scores.values()) else "neutral"
        
        return {
            "primary_arc": primary_arc,
            "arc_scores": arc_scores,
            "intensity": max(arc_scores.values()) if arc_scores.values() else 0
        }
    
    def _detect_pov(self, text: str) -> Dict[str, Any]:
        """
        Detect point of view using NLP analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with POV information
        """
        # Count pronoun usage
        first_person = len(re.findall(r'\b(I|me|my|mine|we|us|our|ours)\b', text, re.IGNORECASE))
        second_person = len(re.findall(r'\b(you|your|yours)\b', text, re.IGNORECASE))
        third_person = len(re.findall(r'\b(he|him|his|she|her|hers|they|them|their|theirs)\b', text, re.IGNORECASE))
        
        total_pronouns = first_person + second_person + third_person
        
        if total_pronouns == 0:
            return {"type": "unknown", "confidence": 0.0, "pronouns": {"first": 0, "second": 0, "third": 0}}
        
        # Determine POV type
        if first_person / total_pronouns > 0.4:
            pov_type = "first_person"
            confidence = first_person / total_pronouns
        elif second_person / total_pronouns > 0.3:
            pov_type = "second_person"
            confidence = second_person / total_pronouns
        else:
            pov_type = "third_person"
            confidence = third_person / total_pronouns
        
        return {
            "type": pov_type,
            "confidence": confidence,
            "pronouns": {
                "first": first_person,
                "second": second_person,
                "third": third_person
            }
        }
    
    async def _analyze_mood_and_significance(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze mood using OpenAI sentiment and significance using TF-IDF.
        
        Args:
            scenes: List of scene dictionaries
            
        Returns:
            List of scenes with mood and significance analysis
        """
        enhanced_scenes = []
        
        # Collect all text for TF-IDF analysis
        all_texts = [scene["text"] for scene in scenes]
        
        for i, scene in enumerate(scenes):
            enhanced_scene = scene.copy()
            
            # Mood analysis using OpenAI sentiment
            mood_analysis = await self._analyze_mood_openai(scene["text"])
            enhanced_scene["mood"] = mood_analysis
            
            # Significance analysis using TF-IDF
            significance_analysis = self._analyze_significance_tfidf(scene["text"], all_texts, i)
            enhanced_scene["significance"] = significance_analysis
            
            enhanced_scenes.append(enhanced_scene)
        
        return enhanced_scenes
    
    async def _analyze_mood_openai(self, text: str) -> Dict[str, Any]:
        """
        Analyze mood using OpenAI sentiment analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with mood analysis
        """
        if not self.openai_client:
            # Fallback to simple lexical analysis
            return self._analyze_mood_lexical(text)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the mood and emotional tone of the given text. Respond with a JSON object containing 'primary_mood' (happy, sad, tense, peaceful, dramatic, mysterious, romantic, action), 'intensity' (0.0-1.0), and 'secondary_moods' (array of up to 2 additional moods)."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the mood of this text: {text[:500]}"  # Limit to 500 chars
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            try:
                mood_data = json.loads(response.choices[0].message.content)
                return {
                    "primary_mood": mood_data.get("primary_mood", "neutral"),
                    "intensity": mood_data.get("intensity", 0.5),
                    "secondary_moods": mood_data.get("secondary_moods", []),
                    "method": "openai"
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return self._analyze_mood_lexical(text)
        
        except Exception as e:
            print(f"Warning: OpenAI mood analysis failed: {e}")
            return self._analyze_mood_lexical(text)
    
    def _analyze_mood_lexical(self, text: str) -> Dict[str, Any]:
        """
        Fallback mood analysis using lexical patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with mood analysis
        """
        mood_keywords = {
            "happy": ["joy", "happy", "pleased", "delighted", "cheerful", "smile", "laugh"],
            "sad": ["sad", "sorrow", "grief", "melancholy", "despair", "cry", "tear"],
            "tense": ["tension", "suspense", "anxious", "worried", "nervous", "fear"],
            "dramatic": ["dramatic", "intense", "powerful", "striking", "significant"],
            "mysterious": ["mystery", "secret", "hidden", "unknown", "enigma", "puzzle"],
            "action": ["fight", "battle", "run", "chase", "attack", "escape", "rush"]
        }
        
        mood_scores = {}
        text_lower = text.lower()
        
        for mood, keywords in mood_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            mood_scores[mood] = score
        
        primary_mood = max(mood_scores, key=mood_scores.get) if any(mood_scores.values()) else "neutral"
        max_score = max(mood_scores.values()) if mood_scores.values() else 0
        intensity = min(max_score / 3.0, 1.0)  # Normalize to 0-1
        
        return {
            "primary_mood": primary_mood,
            "intensity": intensity,
            "secondary_moods": [],
            "method": "lexical"
        }
    
    def _analyze_significance_tfidf(self, text: str, all_texts: List[str], current_index: int) -> Dict[str, Any]:
        """
        Analyze significance using TF-IDF against the narrative.
        
        Args:
            text: Current text to analyze
            all_texts: All texts in the narrative
            current_index: Index of current text
            
        Returns:
            Dict with significance analysis
        """
        if not self.nlp:
            return {"significance_score": 0.5, "key_terms": [], "method": "unavailable"}
        
        try:
            # Simple TF-IDF implementation
            doc = self.nlp(text)
            
            # Extract meaningful tokens (nouns, verbs, adjectives)
            tokens = [token.lemma_.lower() for token in doc if token.pos_ in ["NOUN", "VERB", "ADJ"] and not token.is_stop and len(token.text) > 2]
            
            if not tokens:
                return {"significance_score": 0.3, "key_terms": [], "method": "tfidf"}
            
            # Calculate term frequencies
            tf = Counter(tokens)
            total_tokens = len(tokens)
            tf_scores = {term: count / total_tokens for term, count in tf.items()}
            
            # Calculate document frequencies (simple version)
            df = {}
            for term in tf_scores:
                df[term] = sum(1 for other_text in all_texts if term in other_text.lower())
            
            # Calculate TF-IDF scores
            tfidf_scores = {}
            for term, tf_score in tf_scores.items():
                idf = len(all_texts) / (df[term] + 1)  # +1 to avoid division by zero
                tfidf_scores[term] = tf_score * idf
            
            # Get top terms
            top_terms = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Calculate overall significance score
            significance_score = min(sum(score for _, score in top_terms) / 5.0, 1.0) if top_terms else 0.3
            
            return {
                "significance_score": significance_score,
                "key_terms": [term for term, _ in top_terms],
                "tfidf_scores": dict(top_terms),
                "method": "tfidf"
            }
        
        except Exception as e:
            print(f"Warning: TF-IDF analysis failed: {e}")
            return {"significance_score": 0.5, "key_terms": [], "method": "error"}
    
    def _detect_continuity_callbacks(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect foreshadowing and callback phrases for continuity edges.
        
        Args:
            scenes: List of scene dictionaries
            
        Returns:
            List of continuity edge dictionaries
        """
        continuity_edges = []
        
        for i, scene in enumerate(scenes):
            text = scene["text"]
            
            # Check for continuity patterns
            for pattern_idx, pattern in enumerate(self.compiled_patterns):
                matches = pattern.finditer(text)
                
                for match in matches:
                    # Look for references to other scenes
                    for j, other_scene in enumerate(scenes):
                        if i == j:  # Skip self-references
                            continue
                        
                        # Simple similarity check for callbacks
                        if self._check_callback_similarity(scene, other_scene, match.group()):
                            edge_id = f"continuity_{uuid.uuid4().hex[:8]}"
                            
                            continuity_edge = {
                                "id": edge_id,
                                "type": "CONTINUITY",
                                "from_scene_id": scene["id"],
                                "to_scene_id": other_scene["id"],
                                "properties": {
                                    "callback_phrase": match.group(),
                                    "pattern_type": f"pattern_{pattern_idx}",
                                    "confidence": self._calculate_continuity_confidence(scene, other_scene, match.group()),
                                    "scene_order_diff": abs(i - j),
                                    "detected_at": datetime.utcnow().isoformat()
                                }
                            }
                            
                            continuity_edges.append(continuity_edge)
        
        return continuity_edges
    
    def _check_callback_similarity(self, scene1: Dict[str, Any], scene2: Dict[str, Any], phrase: str) -> bool:
        """
        Check if two scenes have callback similarity.
        
        Args:
            scene1: First scene
            scene2: Second scene
            phrase: Matched phrase
            
        Returns:
            Boolean indicating if there's a callback similarity
        """
        if not self.nlp:
            # Simple keyword matching fallback
            words1 = set(scene1["text"].lower().split())
            words2 = set(scene2["text"].lower().split())
            common_words = words1.intersection(words2)
            return len(common_words) >= 3  # At least 3 common words
        
        try:
            # Use spaCy for semantic similarity
            doc1 = self.nlp(scene1["text"][:200])  # Limit for performance
            doc2 = self.nlp(scene2["text"][:200])
            
            similarity = doc1.similarity(doc2)
            return similarity > 0.3  # Threshold for semantic similarity
        
        except Exception:
            # Fallback to keyword matching
            words1 = set(scene1["text"].lower().split())
            words2 = set(scene2["text"].lower().split())
            common_words = words1.intersection(words2)
            return len(common_words) >= 3
    
    def _calculate_continuity_confidence(self, scene1: Dict[str, Any], scene2: Dict[str, Any], phrase: str) -> float:
        """
        Calculate confidence score for continuity edge.
        
        Args:
            scene1: First scene
            scene2: Second scene
            phrase: Matched phrase
            
        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.6
        
        # Boost confidence for explicit temporal references
        if any(word in phrase.lower() for word in ["remember", "recalled", "earlier", "before", "later", "future"]):
            base_confidence += 0.2
        
        # Boost confidence for character mentions
        if self.nlp:
            try:
                doc1 = self.nlp(scene1["text"])
                doc2 = self.nlp(scene2["text"])
                
                # Extract person entities
                persons1 = {ent.text.lower() for ent in doc1.ents if ent.label_ == "PERSON"}
                persons2 = {ent.text.lower() for ent in doc2.ents if ent.label_ == "PERSON"}
                
                if persons1.intersection(persons2):
                    base_confidence += 0.1
            except Exception:
                pass
        
        return min(base_confidence, 1.0)
    
    async def _extract_with_graphiti(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Extract entities, relations, and timestamps using Graphiti's capabilities.
        
        Args:
            scenes: List of scene dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing extracted data
        """
        if not self.graphiti_manager.client:
            await self.graphiti_manager.connect()
        
        # Enhance scenes with mood and significance analysis
        enhanced_scenes = await self._analyze_mood_and_significance(scenes)
        
        # Detect continuity edges
        continuity_edges = self._detect_continuity_callbacks(enhanced_scenes)
        
        all_entities = []
        all_relationships = []
        all_scenes = []
        all_knowledge_items = []
        scene_errors = []  # Track errors for failed fact extraction
        
        # Get or create story session
        session_id = await self.graphiti_manager.create_story_session(story_id)
        
        for scene in enhanced_scenes:
            try:
                # Create enhanced episode name with chapter/episode info
                episode_name = f"Ch{scene['chapter']}.Ep{scene['episode']} - Scene {scene['order']} - {story_id}"
                
                # Use Graphiti's add_episode for extraction (acts as /extract endpoint)
                episode_result = await self.graphiti_manager.client.add_episode(
                    name=episode_name,
                    episode_body=scene['text'],
                    source_description=f"Chapter {scene['chapter']}, Episode {scene['episode']}, Scene {scene['order']} from story {story_id}",
                    reference_time=datetime.utcnow(),
                    group_id=session_id
                )
                
                # Capture the returned session_id from the episode for future calls
                if episode_result and hasattr(episode_result, 'group_id') and episode_result.group_id:
                    session_id = episode_result.group_id
                    # Update the session in the graphiti_manager
                    self.graphiti_manager._story_sessions[story_id] = session_id
                
                # Extract entities and relationships from Graphiti 0.3.0 - wrap in try/catch to prevent batch failure
                try:
                    # In Graphiti 0.3.0, add_episode automatically extracts entities/relationships
                    # We need to search for what was created to get the actual data
                    search_results = await self.graphiti_manager.client.search(
                        query=scene['text'][:100],  # Use first 100 chars as search query
                        group_ids=[session_id],
                        num_results=20  # Get more results to capture all extractions
                    )
                    
                    # Process search results to extract entities and relationships
                    scene_entities, scene_relationships, scene_knowledge = self._process_search_results(
                        search_results, scene, story_id, user_id
                    )
                    
                    all_entities.extend(scene_entities)
                    all_relationships.extend(scene_relationships)
                    all_knowledge_items.extend(scene_knowledge)
                    
                except Exception as extraction_error:
                    # Log extraction error but continue processing
                    error_info = {
                        "scene_id": scene['id'],
                        "error_type": "entity_extraction_failed",
                        "error_message": str(extraction_error),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    scene_errors.append(error_info)
                    print(f"Warning: Entity extraction failed for scene {scene['id']}: {str(extraction_error)}")
                
                # Create scene entity with defensive episode_id handling
                episode_id = None
                if episode_result:
                    # Try multiple possible attributes for the episode ID
                    for attr_name in ['uuid', 'id', 'episode_id']:
                        if hasattr(episode_result, attr_name):
                            episode_id = getattr(episode_result, attr_name)
                            break
                
                # Enhanced scene entity with new metadata
                scene_entity = {
                    "id": scene['id'],
                    "name": f"Ch{scene['chapter']}.Ep{scene['episode']} - Scene {scene['order']}",
                    "type": "SCENE",
                    "properties": {
                        "order": scene['order'],
                        "text": scene['text'],
                        "word_count": scene['word_count'],
                        "story_id": story_id,
                        "user_id": user_id,
                        "episode_id": episode_id,
                        "chapter": scene['chapter'],
                        "episode": scene['episode'],
                        "chapter_boundary": scene['chapter_boundary'],
                        "episode_boundary": scene['episode_boundary'],
                        "story_arc": scene['story_arc'],
                        "pov": scene['pov'],
                        "mood": scene.get('mood', {}),
                        "significance": scene.get('significance', {}),
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                all_scenes.append(scene_entity)
                
            except Exception as e:
                # Log scene processing error but continue with other scenes
                error_info = {
                    "scene_id": scene['id'],
                    "error_type": "scene_processing_failed",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                scene_errors.append(error_info)
                print(f"Warning: Scene processing failed for scene {scene['id']}: {str(e)}")
                continue
        
        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "scenes": all_scenes,
            "knowledge_items": all_knowledge_items,
            "continuity_edges": continuity_edges,
            "scene_errors": scene_errors  # Include errors in the result
        }
    
    def _process_search_results(self, search_results: List[Any], scene: Dict[str, Any], story_id: str, user_id: str) -> tuple:
        """
        Process search results from Graphiti 0.3.0 to extract entities, relationships, and knowledge items.
        
        Args:
            search_results: List of search results from Graphiti (EntityEdge, EntityNode, etc.)
            scene: Scene metadata
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Tuple of (entities, relationships, knowledge_items)
        """
        entities = []
        relationships = []
        knowledge_items = []
        
        for result in search_results:
            try:
                result_type = type(result).__name__
                
                if 'EntityEdge' in result_type:
                    # This is a relationship/edge
                    relationship_id = f"rel_{getattr(result, 'uuid', uuid.uuid4().hex[:8])}"
                    
                    relationship = {
                        "id": relationship_id,
                        "type": getattr(result, 'name', 'RELATED_TO'),
                        "from_id": getattr(result, 'source_node_uuid', 'unknown'),
                        "to_id": getattr(result, 'target_node_uuid', 'unknown'),
                        "properties": {
                            "fact": getattr(result, 'fact', ''),
                            "confidence": 0.8,  # Default confidence
                            "scene_id": scene['id'],
                            "story_id": story_id,
                            "user_id": user_id,
                            "created_at": getattr(result, 'created_at', datetime.utcnow()).isoformat() if hasattr(result, 'created_at') else datetime.utcnow().isoformat(),
                            "graphiti_uuid": getattr(result, 'uuid', None)
                        }
                    }
                    relationships.append(relationship)
                    
                    # Create knowledge item from the fact
                    if hasattr(result, 'fact') and result.fact:
                        knowledge_id = f"knowledge_{uuid.uuid4().hex[:8]}"
                        knowledge_item = {
                            "id": knowledge_id,
                            "name": f"Fact: {result.fact[:50]}...",
                            "type": "KNOWLEDGE",
                            "properties": {
                                "content": result.fact,
                                "confidence": 0.8,
                                "scene_id": scene['id'],
                                "story_id": story_id,
                                "user_id": user_id,
                                "created_at": datetime.utcnow().isoformat(),
                                "source_relationship": relationship_id
                            }
                        }
                        knowledge_items.append(knowledge_item)
                
                elif 'EntityNode' in result_type or 'Node' in result_type:
                    # This is an entity/node
                    entity_id = f"entity_{getattr(result, 'uuid', uuid.uuid4().hex[:8])}"
                    entity_name = getattr(result, 'name', 'Unknown Entity')
                    entity_type = self._determine_entity_type(entity_name, getattr(result, 'summary', ''))
                    
                    entity = {
                        "id": entity_id,
                        "name": entity_name,
                        "type": entity_type,
                        "properties": {
                            "summary": getattr(result, 'summary', ''),
                            "mentioned_in_scene": scene['id'],
                            "story_id": story_id,
                            "user_id": user_id,
                            "confidence": 0.8,
                            "created_at": getattr(result, 'created_at', datetime.utcnow()).isoformat() if hasattr(result, 'created_at') else datetime.utcnow().isoformat(),
                            "graphiti_uuid": getattr(result, 'uuid', None)
                        }
                    }
                    entities.append(entity)
                
            except Exception as e:
                print(f"Warning: Error processing search result {result_type}: {str(e)}")
                continue
        
        return entities, relationships, knowledge_items
    
    def _determine_entity_type(self, entity_name: str, context: str) -> str:
        """
        Determine the type of an entity based on name and context.
        
        Args:
            entity_name: Name of the entity
            context: Context where entity appears
            
        Returns:
            Entity type string
        """
        entity_name_lower = entity_name.lower()
        context_lower = context.lower()
        
        # Simple heuristics for entity type determination
        if any(word in entity_name_lower for word in ['castle', 'town', 'forest', 'mountain', 'river', 'room', 'house']):
            return "LOCATION"
        elif any(word in context_lower for word in ['said', 'told', 'spoke', 'thought', 'felt', 'character']):
            return "CHARACTER"
        elif any(word in entity_name_lower for word in ['sword', 'potion', 'key', 'ring', 'book', 'scroll']):
            return "ITEM"
        elif any(word in context_lower for word in ['happened', 'occurred', 'event', 'battle', 'meeting']):
            return "EVENT"
        else:
            return "CHARACTER"  # Default to character
    
    async def _map_and_upsert_entities(self, extracted_data: Dict[str, Any], story_id: str, user_id: str) -> None:
        """
        Map extracted data to schema and upsert using GraphitiManager.
        
        Args:
            extracted_data: Extracted entities and relationships
            story_id: Story identifier
            user_id: User ID for data isolation
        """
        # Upsert entities
        for entity in extracted_data.get("entities", []):
            await self.graphiti_manager.upsert_entity(
                entity_type=entity["type"],
                properties={
                    "id": entity["id"],
                    "name": entity["name"],
                    **entity["properties"]
                }
            )
        
        # Upsert scenes
        for scene in extracted_data.get("scenes", []):
            await self.graphiti_manager.upsert_entity(
                entity_type="SCENE",
                properties={
                    "id": scene["id"],
                    "name": scene["name"],
                    **scene["properties"]
                }
            )
        
        # Upsert knowledge items
        for knowledge in extracted_data.get("knowledge_items", []):
            await self.graphiti_manager.upsert_entity(
                entity_type="KNOWLEDGE",
                properties={
                    "id": knowledge["id"],
                    "name": knowledge["name"],
                    **knowledge["properties"]
                }
            )
        
        # Upsert relationships
        for relationship in extracted_data.get("relationships", []):
            await self.graphiti_manager.upsert_relationship(
                relationship_type=relationship["type"],
                from_id=relationship["from_id"],
                to_id=relationship["to_id"],
                properties=relationship["properties"]
            )
    
    async def _create_continuity_edges(self, continuity_edges: List[Dict[str, Any]], story_id: str, user_id: str) -> None:
        """
        Create continuity edges for foreshadowing and callbacks.
        
        Args:
            continuity_edges: List of continuity edge dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
        """
        for edge in continuity_edges:
            # Add story and user context to properties
            edge["properties"]["story_id"] = story_id
            edge["properties"]["user_id"] = user_id
            
            # Create the continuity relationship
            await self.graphiti_manager.upsert_relationship(
                relationship_type="CONTINUITY",
                from_id=edge["from_scene_id"],
                to_id=edge["to_scene_id"],
                properties=edge["properties"]
            )
    
    def _store_traceability_mappings(self, scenes: List[Dict[str, Any]], extracted_data: Dict[str, Any]) -> None:
        """
        Store mapping from original text segment to scene_id for traceability.
        
        Args:
            scenes: Original scene data
            extracted_data: Extracted data with scene entities
        """
        for scene in scenes:
            segment_id = scene["segment_id"]
            scene_id = scene["id"]
            self._scene_mappings[segment_id] = scene_id
        
        # Also map any additional entities to their source scenes
        for entity in extracted_data.get("entities", []):
            if "mentioned_in_scene" in entity.get("properties", {}):
                entity_id = entity["id"]
                scene_id = entity["properties"]["mentioned_in_scene"]
                self._scene_mappings[f"entity_{entity_id}"] = scene_id
    
    def _update_processing_stats(self, processing_time: float) -> None:
        """
        Update processing statistics.
        
        Args:
            processing_time: Processing time in milliseconds
        """
        self._processing_stats["total_processed"] += 1
        total = self._processing_stats["total_processed"]
        current_avg = self._processing_stats["avg_processing_time"]
        
        # Calculate new running average
        self._processing_stats["avg_processing_time"] = ((current_avg * (total - 1)) + processing_time) / total
        self._processing_stats["last_processed"] = datetime.utcnow().isoformat()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get current processing statistics.
        
        Returns:
            Dict containing processing statistics
        """
        return dict(self._processing_stats)
    
    async def _fix_generic_relationships(self, story_id: str) -> Dict[str, Any]:
        """
        Post-process relationships to convert generic types to meaningful names.
        This addresses the Graphiti 0.3.0 issue where relationships are created with
        generic types (RELATES_TO, MENTIONS, HAS_MEMBER) but meaningful names are
        stored in the 'name' property.
        
        Args:
            story_id: Story identifier to limit the scope of fixes
            
        Returns:
            Dict containing fix results
        """
        if not self.graphiti_manager.client:
            return {"status": "error", "error": "No client connection"}
        
        # Generic relationship types that need conversion
        GENERIC_TYPES = ['RELATES_TO', 'MENTIONS', 'HAS_MEMBER']
        
        # Get connection details from GraphitiManager
        config = self.graphiti_manager.config
        driver = AsyncGraphDatabase.driver(
            config.database_url, 
            auth=(config.username, config.password)
        )
        
        try:
            async with driver.session() as session:
                total_fixed = 0
                fix_results = []
                
                for generic_type in GENERIC_TYPES:
                    # Find relationships of this type that need fixing
                    result = await session.run(f"""
                        MATCH ()-[r:{generic_type}]->()
                        WHERE r.name IS NOT NULL AND r.name <> type(r)
                        AND (r.group_id CONTAINS $story_id OR r.story_id = $story_id)
                        RETURN r.name as meaningful_name, count(*) as count
                    """, story_id=story_id)
                    
                    relationships_to_fix = []
                    async for record in result:
                        meaningful_name = record['meaningful_name']
                        count = record['count']
                        relationships_to_fix.append((meaningful_name, count))
                    
                    # Fix each meaningful relationship type
                    for meaningful_name, count in relationships_to_fix:
                        if count == 0:
                            continue
                            
                        # Sanitize the relationship name for Neo4j
                        safe_name = meaningful_name.upper().replace(' ', '_').replace('-', '_')
                        
                        try:
                            # Convert relationships
                            fix_result = await session.run(f"""
                                MATCH (a)-[old:{generic_type}]->(b)
                                WHERE old.name = $meaningful_name
                                AND (old.group_id CONTAINS $story_id OR old.story_id = $story_id)
                                WITH a, old, b, old {{ .* }} as props
                                DELETE old
                                CREATE (a)-[new:{safe_name}]->(b)
                                SET new = props
                                RETURN count(new) as converted
                            """, meaningful_name=meaningful_name, story_id=story_id)
                            
                            record = await fix_result.single()
                            converted = record['converted'] if record else 0
                            total_fixed += converted
                            
                            if converted > 0:
                                fix_results.append({
                                    "from_type": generic_type,
                                    "to_type": safe_name,
                                    "converted": converted,
                                    "original_name": meaningful_name
                                })
                                
                        except Exception as e:
                            print(f"Warning: Error fixing {generic_type}->{meaningful_name}: {e}")
                            continue
                
                return {
                    "status": "success",
                    "total_fixed": total_fixed,
                    "fixes": fix_results,
                    "story_id": story_id
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
        finally:
            await driver.close()
    
    def get_traceability_mapping(self, segment_id: str) -> Optional[str]:
        """
        Get scene_id for a given text segment.
        
        Args:
            segment_id: Text segment identifier
            
        Returns:
            Scene ID if found, None otherwise
        """
        return self._scene_mappings.get(segment_id)
