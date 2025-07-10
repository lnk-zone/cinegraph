// Cinegraph Schema Constraints and Indexes for Neo4j
// This file contains Cypher statements to create constraints and indexes
// for the extended cinegraph schema with Episode entities and SNA optimizations

// === UNIQUE CONSTRAINTS ===

// Episode unique constraint for Episode type Arc, Chapter, and Thread
CREATE CONSTRAINT episode_type_unique IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_type IS NOT NULL;

// Episode unique constraint
CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_id IS UNIQUE;

// Character unique constraint (existing)
CREATE CONSTRAINT character_id_unique IF NOT EXISTS
FOR (c:Character) REQUIRE c.character_id IS UNIQUE;

// Knowledge unique constraint (existing)
CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;

// Scene unique constraint (existing)
CREATE CONSTRAINT scene_id_unique IF NOT EXISTS
FOR (s:Scene) REQUIRE s.scene_id IS UNIQUE;

// Location unique constraint (existing)
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

// Item unique constraint (existing)
CREATE CONSTRAINT item_id_unique IF NOT EXISTS
FOR (i:Item) REQUIRE i.item_id IS UNIQUE;

// === PROPERTY EXISTENCE CONSTRAINTS ===

// Episode required properties
CREATE CONSTRAINT episode_required_props IF NOT EXISTS
FOR (e:Episode) REQUIRE (e.episode_id IS NOT NULL AND e.story_id IS NOT NULL AND e.user_id IS NOT NULL);

// Character required properties (existing)
CREATE CONSTRAINT character_required_props IF NOT EXISTS
FOR (c:Character) REQUIRE (c.character_id IS NOT NULL AND c.name IS NOT NULL AND c.story_id IS NOT NULL AND c.user_id IS NOT NULL);

// === INDEXES FOR SOCIAL NETWORK ANALYSIS ===

// Character relationship index for SNA metrics
CREATE INDEX character_rel_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.character_id);

// New relationship types indexes for SNA metrics
CREATE INDEX mentors_rel_index IF NOT EXISTS
FOR ()-[r:MENTORS]-() ON (r.story_id, r.start_date);

CREATE INDEX rivals_rel_index IF NOT EXISTS
FOR ()-[r:RIVALS]-() ON (r.story_id, r.intensity);

CREATE INDEX romantic_partner_rel_index IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() ON (r.story_id, r.relationship_status);

// Character network analysis composite index
CREATE INDEX character_network_index IF NOT EXISTS
FOR (c:Character) ON (c.character_id, c.story_id, c.user_id);

// Episode hierarchy index
CREATE INDEX episode_hierarchy_index IF NOT EXISTS
FOR ()-[r:PARENT_OF]-() ON (r.story_id, r.user_id);

// Episode continuity relationships index
CREATE INDEX episode_continuity_index IF NOT EXISTS
FOR ()-[r:CALLBACKS_TO|FORESHADOWS|RESOLVES]-() ON (r.story_id, r.user_id);

// Character relationship extended properties index
CREATE INDEX character_rel_extended_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.milestone, r.trigger_event_id, r.secret_level);

// Episode POV character index
CREATE INDEX episode_pov_index IF NOT EXISTS
FOR (e:Episode) ON (e.pov_character_id, e.story_id);

// Episode significance scoring index
CREATE INDEX episode_significance_index IF NOT EXISTS
FOR (e:Episode) ON (e.significance_score, e.episode_type);

// === TEMPORAL INDEXES ===

// Episode temporal index
CREATE INDEX episode_temporal_index IF NOT EXISTS
FOR (e:Episode) ON (e.valid_from, e.valid_to, e.timestamp_in_story);

// Character relationship temporal index
CREATE INDEX character_rel_temporal_index IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.valid_from, r.valid_to, r.established_at, r.last_interaction);

// === FULL-TEXT SEARCH INDEXES ===

// Episode content search
CREATE FULLTEXT INDEX episode_content_search IF NOT EXISTS
FOR (e:Episode) ON EACH [e.title, e.mood];

// Character relationship context search
CREATE FULLTEXT INDEX character_rel_context_search IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON EACH [r.relationship_context, r.milestone];

// === RANGE INDEXES FOR NUMERIC PROPERTIES ===

// Episode significance score range index
CREATE RANGE INDEX episode_significance_range IF NOT EXISTS
FOR (e:Episode) ON (e.significance_score);

// Character relationship strength range index
CREATE RANGE INDEX character_rel_strength_range IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_strength, r.trust_level, r.secret_level);

// === VALIDATION CONSTRAINTS (Neo4j 5.0+) ===

// Episode type validation
CREATE CONSTRAINT episode_type_validation IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_type IN ['Arc', 'Chapter', 'Thread'];

// Episode significance score validation
CREATE CONSTRAINT episode_significance_validation IF NOT EXISTS
FOR (e:Episode) REQUIRE e.significance_score >= 0 AND e.significance_score <= 10;

// Character relationship secret level validation
CREATE CONSTRAINT character_secret_level_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.secret_level >= 0 AND r.secret_level <= 10;

// Relationship strength validation
CREATE CONSTRAINT relationship_strength_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.relationship_strength >= 1 AND r.relationship_strength <= 10;

// Trust level validation
CREATE CONSTRAINT trust_level_validation IF NOT EXISTS
FOR ()-[r:RELATIONSHIP]-() REQUIRE r.trust_level >= 1 AND r.trust_level <= 10;

// Rivals intensity validation
CREATE CONSTRAINT rivals_intensity_validation IF NOT EXISTS
FOR ()-[r:RIVALS]-() REQUIRE r.intensity >= 1 AND r.intensity <= 10;

// Romantic partner relationship status validation
CREATE CONSTRAINT romantic_partner_status_validation IF NOT EXISTS
FOR ()-[r:ROMANTIC_PARTNER]-() REQUIRE r.relationship_status IN ['current', 'past', 'complicated', 'unknown'];

// === ANALYTICS PROJECTION LABELS ===

// Create projection labels for Social Network Analysis
// These are used for graph algorithms and analytics

// Character centrality label
CREATE CONSTRAINT character_centrality_label IF NOT EXISTS
FOR (c:Character) REQUIRE c.character_id IS NOT NULL;

// Episode hierarchy label
CREATE CONSTRAINT episode_hierarchy_label IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_id IS NOT NULL;
