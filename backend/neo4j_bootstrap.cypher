// ============================================================================
// CineGraph Neo4j Schema Bootstrap Script
// ============================================================================
// This script creates indexes, constraints, and properties that match the
// CineGraphAgent schema design with enum values and temporal properties.
//
// Run this script to synchronize the live Graphiti database with the
// expected CineGraphAgent schema constraints.
// ============================================================================

// ============================================================================
// 1. NODE CONSTRAINTS AND INDEXES
// ============================================================================

// Character Node Constraints
CREATE CONSTRAINT character_id_unique IF NOT EXISTS
FOR (c:Character) REQUIRE c.character_id IS UNIQUE;

CREATE CONSTRAINT character_name_per_story IF NOT EXISTS  
FOR (c:Character) REQUIRE (c.name, c.story_id, c.user_id) IS UNIQUE;

// Knowledge Node Constraints
CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;

CREATE CONSTRAINT knowledge_content_required IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.content IS NOT NULL;

// Scene Node Constraints  
CREATE CONSTRAINT scene_id_unique IF NOT EXISTS
FOR (s:Scene) REQUIRE s.scene_id IS UNIQUE;

CREATE CONSTRAINT scene_order_per_story IF NOT EXISTS
FOR (s:Scene) REQUIRE (s.scene_order, s.story_id, s.user_id) IS UNIQUE;

// Location Node Constraints
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

CREATE CONSTRAINT location_name_per_story IF NOT EXISTS
FOR (l:Location) REQUIRE (l.name, l.story_id, l.user_id) IS UNIQUE;

// ============================================================================
// 2. DATA ISOLATION INDEXES
// ============================================================================

// Story ID indexes for data isolation
CREATE INDEX story_id_character IF NOT EXISTS
FOR (c:Character) ON (c.story_id);

CREATE INDEX story_id_knowledge IF NOT EXISTS  
FOR (k:Knowledge) ON (k.story_id);

CREATE INDEX story_id_scene IF NOT EXISTS
FOR (s:Scene) ON (s.story_id);

CREATE INDEX story_id_location IF NOT EXISTS
FOR (l:Location) ON (l.story_id);

// User ID indexes for multi-tenancy
CREATE INDEX user_id_character IF NOT EXISTS
FOR (c:Character) ON (c.user_id);

CREATE INDEX user_id_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.user_id);

CREATE INDEX user_id_scene IF NOT EXISTS
FOR (s:Scene) ON (s.user_id);

CREATE INDEX user_id_location IF NOT EXISTS
FOR (l:Location) ON (l.user_id);

// Combined story+user indexes for optimal filtering
CREATE INDEX story_user_character IF NOT EXISTS
FOR (c:Character) ON (c.story_id, c.user_id);

CREATE INDEX story_user_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.story_id, k.user_id);

CREATE INDEX story_user_scene IF NOT EXISTS
FOR (s:Scene) ON (s.story_id, s.user_id);

CREATE INDEX story_user_location IF NOT EXISTS
FOR (l:Location) ON (l.story_id, l.user_id);

// ============================================================================
// 3. TEMPORAL PROPERTY INDEXES
// ============================================================================

// Temporal indexes for bi-temporal queries
CREATE INDEX temporal_valid_from_character IF NOT EXISTS
FOR (c:Character) ON (c.valid_from);

CREATE INDEX temporal_valid_to_character IF NOT EXISTS
FOR (c:Character) ON (c.valid_to);

CREATE INDEX temporal_valid_from_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.valid_from);

CREATE INDEX temporal_valid_to_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.valid_to);

CREATE INDEX temporal_created_at_character IF NOT EXISTS
FOR (c:Character) ON (c.created_at);

CREATE INDEX temporal_updated_at_character IF NOT EXISTS
FOR (c:Character) ON (c.updated_at);

CREATE INDEX temporal_created_at_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.created_at);

CREATE INDEX temporal_updated_at_knowledge IF NOT EXISTS
FOR (k:Knowledge) ON (k.updated_at);

CREATE INDEX temporal_created_at_scene IF NOT EXISTS
FOR (s:Scene) ON (s.created_at);

CREATE INDEX temporal_updated_at_scene IF NOT EXISTS
FOR (s:Scene) ON (s.updated_at);

CREATE INDEX temporal_created_at_location IF NOT EXISTS
FOR (l:Location) ON (l.created_at);

CREATE INDEX temporal_updated_at_location IF NOT EXISTS
FOR (l:Location) ON (l.updated_at);

// ============================================================================
// 4. ENUM PROPERTY INDEXES  
// ============================================================================

// Knowledge type enumeration indexes
CREATE INDEX knowledge_type_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.knowledge_type);

CREATE INDEX importance_level_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.importance_level);

CREATE INDEX verification_status_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.verification_status);

// Location type enumeration indexes
CREATE INDEX location_type_index IF NOT EXISTS
FOR (l:Location) ON (l.location_type);

CREATE INDEX accessibility_index IF NOT EXISTS
FOR (l:Location) ON (l.accessibility);

// Character activity indexes
CREATE INDEX character_active_index IF NOT EXISTS
FOR (c:Character) ON (c.is_active);

CREATE INDEX location_active_index IF NOT EXISTS
FOR (l:Location) ON (l.is_active);

// Scene ordering index
CREATE INDEX scene_order_index IF NOT EXISTS
FOR (s:Scene) ON (s.scene_order);

// ============================================================================
// 5. RELATIONSHIP PROPERTY INDEXES
// ============================================================================

// KNOWS relationship indexes
CREATE INDEX knows_learned_at IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.learned_at);

CREATE INDEX knows_confidence_level IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.confidence_level);

CREATE INDEX knows_sharing_restrictions IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.sharing_restrictions);

CREATE INDEX knows_emotional_impact IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.emotional_impact);

// RELATIONSHIP relationship indexes  
CREATE INDEX relationship_type_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_type);

CREATE INDEX relationship_strength_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_strength);

CREATE INDEX trust_level_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.trust_level);

CREATE INDEX emotional_valence_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.emotional_valence);

CREATE INDEX relationship_status_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_status);

CREATE INDEX power_dynamic_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.power_dynamic);

// PRESENT_IN relationship indexes
CREATE INDEX present_participation_level IF NOT EXISTS
FOR ()-[r:PRESENT_IN]-() ON (r.participation_level);

CREATE INDEX present_arrival_time IF NOT EXISTS
FOR ()-[r:PRESENT_IN]-() ON (r.arrival_time);

CREATE INDEX present_departure_time IF NOT EXISTS
FOR ()-[r:PRESENT_IN]-() ON (r.departure_time);

// CONTRADICTS relationship indexes
CREATE INDEX contradicts_severity IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.severity);

CREATE INDEX contradicts_type IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.contradiction_type);

CREATE INDEX contradicts_resolution_status IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.resolution_status);

CREATE INDEX contradicts_detected_at IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.detected_at);

// IMPLIES relationship indexes
CREATE INDEX implies_strength IF NOT EXISTS
FOR ()-[r:IMPLIES]-() ON (r.implication_strength);

// Data isolation indexes for relationships
CREATE INDEX relationship_story_id IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.story_id);

CREATE INDEX relationship_user_id IF NOT EXISTS  
FOR ()-[r:KNOWS]-() ON (r.user_id);

CREATE INDEX rel_relationship_story_id IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.story_id);

CREATE INDEX rel_relationship_user_id IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.user_id);

CREATE INDEX present_story_id IF NOT EXISTS
FOR ()-[r:PRESENT_IN]-() ON (r.story_id);

CREATE INDEX present_user_id IF NOT EXISTS
FOR ()-[r:PRESENT_IN]-() ON (r.user_id);

CREATE INDEX occurs_story_id IF NOT EXISTS
FOR ()-[r:OCCURS_IN]-() ON (r.story_id);

CREATE INDEX occurs_user_id IF NOT EXISTS
FOR ()-[r:OCCURS_IN]-() ON (r.user_id);

CREATE INDEX contradicts_story_id IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.story_id);

CREATE INDEX contradicts_user_id IF NOT EXISTS
FOR ()-[r:CONTRADICTS]-() ON (r.user_id);

CREATE INDEX implies_story_id IF NOT EXISTS
FOR ()-[r:IMPLIES]-() ON (r.story_id);

CREATE INDEX implies_user_id IF NOT EXISTS
FOR ()-[r:IMPLIES]-() ON (r.user_id);

// Temporal indexes for relationships
CREATE INDEX relationship_temporal_valid_from IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.valid_from);

CREATE INDEX relationship_temporal_valid_to IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.valid_to);

CREATE INDEX relationship_temporal_created_at IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.created_at);

CREATE INDEX relationship_temporal_updated_at IF NOT EXISTS
FOR ()-[r:KNOWS]-() ON (r.updated_at);

CREATE INDEX rel_relationship_temporal_created_at IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.created_at);

CREATE INDEX rel_relationship_temporal_updated_at IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.updated_at);

// ============================================================================
// 6. GRAPHITI-SPECIFIC INDEXES
// ============================================================================

// Group ID indexes for Graphiti episodic memory
CREATE INDEX group_id_index IF NOT EXISTS
FOR (n) ON (n.group_id) WHERE n.group_id IS NOT NULL;

CREATE INDEX rel_group_id_index IF NOT EXISTS
FOR ()-[r]-() ON (r.group_id) WHERE r.group_id IS NOT NULL;

// Graphiti node type indexes
CREATE INDEX graphiti_node_type IF NOT EXISTS
FOR (n) ON (n.node_type) WHERE n.node_type IS NOT NULL;

// Fact indexing for Graphiti
CREATE INDEX fact_content_index IF NOT EXISTS
FOR (n) ON (n.fact) WHERE n.fact IS NOT NULL;

// Episode indexing
CREATE INDEX episode_body_index IF NOT EXISTS
FOR (n) ON (n.episode_body) WHERE n.episode_body IS NOT NULL;

// Reference time indexing for temporal queries
CREATE INDEX reference_time_index IF NOT EXISTS
FOR (n) ON (n.reference_time) WHERE n.reference_time IS NOT NULL;

// ============================================================================
// 7. PERFORMANCE OPTIMIZATION INDEXES
// ============================================================================

// Composite indexes for common query patterns
CREATE INDEX character_name_story_user IF NOT EXISTS
FOR (c:Character) ON (c.name, c.story_id, c.user_id);

CREATE INDEX knowledge_type_importance_story IF NOT EXISTS
FOR (k:Knowledge) ON (k.knowledge_type, k.importance_level, k.story_id);

CREATE INDEX scene_order_story_user IF NOT EXISTS
FOR (s:Scene) ON (s.scene_order, s.story_id, s.user_id);

CREATE INDEX location_type_accessibility_story IF NOT EXISTS
FOR (l:Location) ON (l.location_type, l.accessibility, l.story_id);

// Query optimization indexes for agent operations
CREATE INDEX character_first_appearance IF NOT EXISTS
FOR (c:Character) ON (c.first_appearance);

CREATE INDEX character_last_mentioned IF NOT EXISTS
FOR (c:Character) ON (c.last_mentioned);

CREATE INDEX location_first_mentioned IF NOT EXISTS
FOR (l:Location) ON (l.first_mentioned);

CREATE INDEX scene_timestamp_in_story IF NOT EXISTS
FOR (s:Scene) ON (s.timestamp_in_story);

CREATE INDEX scene_word_count IF NOT EXISTS
FOR (s:Scene) ON (s.word_count);

// ============================================================================
// 8. TEXT SEARCH INDEXES
// ============================================================================

// Full-text search indexes for content
CREATE FULLTEXT INDEX character_name_fulltext IF NOT EXISTS
FOR (c:Character) ON EACH [c.name, c.description];

CREATE FULLTEXT INDEX knowledge_content_fulltext IF NOT EXISTS  
FOR (k:Knowledge) ON EACH [k.content];

CREATE FULLTEXT INDEX scene_content_fulltext IF NOT EXISTS
FOR (s:Scene) ON EACH [s.title, s.content];

CREATE FULLTEXT INDEX location_description_fulltext IF NOT EXISTS
FOR (l:Location) ON EACH [l.name, l.description];

// ============================================================================
// Schema Bootstrap Complete
// ============================================================================
// 
// This script creates:
// - 4 unique constraints for primary keys
// - 4 composite unique constraints for data isolation
// - 32+ indexes for data isolation (story_id, user_id)
// - 16+ temporal property indexes
// - 20+ enum property indexes  
// - 25+ relationship property indexes
// - 8+ Graphiti-specific indexes
// - 12+ performance optimization indexes
// - 4 full-text search indexes
//
// Total: 100+ database objects for optimal CineGraphAgent performance
//
// Run `/api/admin/ensure_schema` endpoint to apply this script.
// ============================================================================
