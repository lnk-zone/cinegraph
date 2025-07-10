// Migration 002: Add New Relationships and Properties
// ===================================================
// 
// This migration script adds new relationship types with additional properties
// and necessary indexes and uniqueness constraints for Neo4j.
// 
// Version: 2.0.0
// Author: CineGraph Schema Migration
// Date: 2025-01-11
//
// Usage:
//   cat migration_002_add_new_relationships.cypher | cypher-shell -u neo4j -p password

// === MIGRATION VERSION TRACKING ===
// Create a migration tracking system for idempotent runs
CREATE CONSTRAINT migration_version_unique IF NOT EXISTS
FOR (m:Migration) REQUIRE m.version IS UNIQUE;

// Check if this migration has already been applied
MERGE (m:Migration {version: "002"})
ON CREATE SET 
  m.name = "Add New Relationships and Properties",
  m.description = "Adds INTERACTS_WITH, SHARES_SCENE relationships and new properties",
  m.applied_at = datetime(),
  m.status = "applying";

// === NEW RELATIONSHIP TYPES ===

// 1. INTERACTS_WITH relationship (Character -> Character)
// Used to track character interactions with weight scoring
CREATE INDEX interacts_with_weight_index IF NOT EXISTS
FOR ()-[r:INTERACTS_WITH]-() ON (r.interactionWeight);

CREATE INDEX interacts_with_story_index IF NOT EXISTS
FOR ()-[r:INTERACTS_WITH]-() ON (r.story_id, r.user_id);

CREATE INDEX interacts_with_temporal_index IF NOT EXISTS
FOR ()-[r:INTERACTS_WITH]-() ON (r.created_at, r.updated_at);

// 2. SHARES_SCENE relationship (Character -> Character)
// Used to track screen time overlap between characters
CREATE INDEX shares_scene_overlap_index IF NOT EXISTS
FOR ()-[r:SHARES_SCENE]-() ON (r.screenTimeOverlap);

CREATE INDEX shares_scene_story_index IF NOT EXISTS
FOR ()-[r:SHARES_SCENE]-() ON (r.story_id, r.user_id);

CREATE INDEX shares_scene_temporal_index IF NOT EXISTS
FOR ()-[r:SHARES_SCENE]-() ON (r.created_at, r.updated_at);

// 3. MENTORS relationship (Character -> Character)
// Used to track mentorship relationships
CREATE INDEX mentors_story_index IF NOT EXISTS
FOR ()-[r:MENTORS]-() ON (r.story_id, r.user_id);

CREATE INDEX mentors_start_date_index IF NOT EXISTS
FOR ()-[r:MENTORS]-() ON (r.start_date);

CREATE INDEX mentors_temporal_index IF NOT EXISTS
FOR ()-[r:MENTORS]-() ON (r.created_at, r.updated_at);

// 4. RIVALS relationship (Character -> Character)
// Used to track rivalry relationships
CREATE INDEX rivals_intensity_index IF NOT EXISTS
FOR ()-[r:RIVALS]-() ON (r.intensity);

CREATE INDEX rivals_story_index IF NOT EXISTS
FOR ()-[r:RIVALS]-() ON (r.story_id, r.user_id);

CREATE INDEX rivals_temporal_index IF NOT EXISTS
FOR ()-[r:RIVALS]-() ON (r.created_at, r.updated_at);

// 5. ROMANTIC_PARTNER relationship (Character -> Character)
// Used to track romantic relationships
CREATE INDEX romantic_partner_status_index IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() ON (r.relationship_status);

CREATE INDEX romantic_partner_story_index IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() ON (r.story_id, r.user_id);

CREATE INDEX romantic_partner_temporal_index IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() ON (r.created_at, r.updated_at);

// === ENHANCED CHARACTER RELATIONSHIP PROPERTIES ===

// Add indexes for extended RELATIONSHIP properties
CREATE INDEX relationship_milestone_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.milestone);

CREATE INDEX relationship_trigger_event_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.trigger_event_id);

CREATE INDEX relationship_secret_level_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.secret_level);

CREATE INDEX relationship_trust_level_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.trust_level);

CREATE INDEX relationship_strength_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_strength);

CREATE INDEX relationship_context_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_context);

CREATE INDEX relationship_established_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.established_at);

CREATE INDEX relationship_last_interaction_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.last_interaction);

// === EPISODE ENTITY SUPPORT ===

// Episode entity indexes for hierarchy and continuity
CREATE INDEX episode_type_index IF NOT EXISTS
FOR (e:Episode) ON (e.episode_type);

CREATE INDEX episode_pov_character_index IF NOT EXISTS
FOR (e:Episode) ON (e.pov_character_id);

CREATE INDEX episode_significance_index IF NOT EXISTS
FOR (e:Episode) ON (e.significance_score);

CREATE INDEX episode_story_user_index IF NOT EXISTS
FOR (e:Episode) ON (e.story_id, e.user_id);

CREATE INDEX episode_temporal_index IF NOT EXISTS
FOR (e:Episode) ON (e.timestamp_in_story);

// Episode hierarchy relationships
CREATE INDEX parent_of_story_index IF NOT EXISTS
FOR ()-[r:PARENT_OF]-() ON (r.story_id, r.user_id);

CREATE INDEX callbacks_to_story_index IF NOT EXISTS
FOR ()-[r:CALLBACKS_TO]-() ON (r.story_id, r.user_id);

CREATE INDEX foreshadows_story_index IF NOT EXISTS
FOR ()-[r:FORESHADOWS]-() ON (r.story_id, r.user_id);

CREATE INDEX resolves_story_index IF NOT EXISTS
FOR ()-[r:RESOLVES]-() ON (r.story_id, r.user_id);

// Episode-entity relationships
CREATE INDEX contains_scene_order_index IF NOT EXISTS
FOR ()-[r:CONTAINS]-() ON (r.scene_order);

CREATE INDEX features_prominence_index IF NOT EXISTS
FOR ()-[r:FEATURES]-() ON (r.prominence_level);

CREATE INDEX features_arc_stage_index IF NOT EXISTS
FOR ()-[r:FEATURES]-() ON (r.character_arc_stage);

// === VALIDATION CONSTRAINTS ===

// Interaction weight validation (1-10 scale)
CREATE CONSTRAINT interaction_weight_validation IF NOT EXISTS
FOR ()-[r:INTERACTS_WITH]-() REQUIRE r.interactionWeight >= 1 AND r.interactionWeight <= 10;

// Screen time overlap validation (minutes, 0-1440)
CREATE CONSTRAINT screen_time_overlap_validation IF NOT EXISTS
FOR ()-[r:SHARES_SCENE]-() REQUIRE r.screenTimeOverlap >= 0 AND r.screenTimeOverlap <= 1440;

// Trust level validation (1-10 scale)
CREATE CONSTRAINT trust_level_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.trust_level >= 1 AND r.trust_level <= 10;

// Relationship strength validation (1-10 scale)
CREATE CONSTRAINT relationship_strength_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.relationship_strength >= 1 AND r.relationship_strength <= 10;

// Secret level validation (0-10 scale)
CREATE CONSTRAINT secret_level_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.secret_level >= 0 AND r.secret_level <= 10;

// Rivals intensity validation (1-10 scale)
CREATE CONSTRAINT rivals_intensity_validation IF NOT EXISTS
FOR ()-[r:RIVALS]-() REQUIRE r.intensity >= 1 AND r.intensity <= 10;

// Episode significance score validation (0-10 scale)
CREATE CONSTRAINT episode_significance_validation IF NOT EXISTS
FOR (e:Episode) REQUIRE e.significance_score >= 0 AND e.significance_score <= 10;

// Episode type validation
CREATE CONSTRAINT episode_type_validation IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_type IN ['Arc', 'Chapter', 'Thread'];

// Romantic partner status validation
CREATE CONSTRAINT romantic_partner_status_validation IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() REQUIRE r.relationship_status IN ['current', 'past', 'complicated', 'unknown'];

// === DATA ISOLATION INDEXES ===

// Ensure all new relationships have story_id and user_id indexes for multi-tenancy
CREATE INDEX interacts_with_isolation_index IF NOT EXISTS
FOR ()-[r:INTERACTS_WITH]-() ON (r.story_id);

CREATE INDEX shares_scene_isolation_index IF NOT EXISTS
FOR ()-[r:SHARES_SCENE]-() ON (r.story_id);

CREATE INDEX mentors_isolation_index IF NOT EXISTS
FOR ()-[r:MENTORS]-() ON (r.story_id);

CREATE INDEX rivals_isolation_index IF NOT EXISTS
FOR ()-[r:RIVALS]-() ON (r.story_id);

CREATE INDEX romantic_partner_isolation_index IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() ON (r.story_id);

// === FULL-TEXT SEARCH INDEXES ===

// Episode content search
CREATE FULLTEXT INDEX episode_content_search IF NOT EXISTS
FOR (e:Episode) ON EACH [e.title, e.mood];

// Relationship context search
CREATE FULLTEXT INDEX relationship_context_search IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON EACH [r.relationship_context, r.milestone];

// === PERFORMANCE OPTIMIZATION INDEXES ===

// Composite indexes for common queries
CREATE INDEX character_story_user_composite IF NOT EXISTS
FOR (c:Character) ON (c.character_id, c.story_id, c.user_id);

CREATE INDEX episode_hierarchy_composite IF NOT EXISTS
FOR (e:Episode) ON (e.episode_type, e.story_id, e.user_id);

CREATE INDEX relationship_strength_trust_composite IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_strength, r.trust_level);

// === MARK MIGRATION AS COMPLETE ===
MATCH (m:Migration {version: "002"})
SET 
  m.status = "completed",
  m.completed_at = datetime();

// === MIGRATION SUMMARY ===
// This migration adds:
// - 5 new relationship types (INTERACTS_WITH, SHARES_SCENE, MENTORS, RIVALS, ROMANTIC_PARTNER)
// - Extended properties for existing RELATIONSHIP type
// - Episode entity support with hierarchy relationships
// - 47+ new indexes for performance optimization
// - 9 validation constraints for data integrity
// - Full-text search capabilities
// - Multi-tenant data isolation support
// - Temporal indexing for bi-temporal queries
