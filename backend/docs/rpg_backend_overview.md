# RPG Backend Overview

This document summarizes the backend additions that support RPG Maker workflows.

## New Models

The `backend/game/models.py` module defines several pydantic models for storing RPG data:

- **`RPGProject`** – basic project metadata such as name, version and genre.
- **`ExportConfiguration`** – settings for exporting a project to RPG Maker, including target version and package format.
- **`RPGVariable`** and **`RPGSwitch`** – variable and boolean switch definitions with data type and scope fields.
- **`RPGCharacter`** and **`CharacterStats`** – player and non‑player character data with simple statistics.
- **`RPGLocation`** and **`LocationConnection`** – description of locations in the world and how they connect.
- **`RPGQuest`**, **`QuestObjective`**, and **`CompletionCondition`** – quest structures generated from story events.
- **`DialogueTree`**, **`DialogueNode`**, and **`DialogueChoice`** – models for interactive dialogue sequences.

These models allow storing project state generated from stories or user input.

## Services

Several helper classes orchestrate AI powered generation of project data:

- **`StoryVariableGenerator`** – pulls variable and switch information from the knowledge graph through a `CineGraphAgent`.
- **`StoryCharacterEnhancer`** – builds `RPGCharacter` objects using character analysis results from the agent.
- **`StoryLocationEnhancer`** – extracts locations and their connections from the analyzed story.
- **`StoryQuestGenerator`** – creates `RPGQuest` structures from story events.
- **`StoryDialogueGenerator`** – generates `DialogueTree` objects from story interactions.
- **`CharacterRelationshipAnalyzer`** – helper used by generators to infer relationships.
- **`RPGMakerAgent`** – specialized SDK agent to assist with exporting analysis results to RPG Maker formats.

## API Endpoints

`backend/app/main.py` exposes a set of REST endpoints under `/api/rpg-projects` for managing projects:

- `POST /api/rpg-projects` – create a new project.
- `POST /api/rpg-projects/{project_id}/sync-story` – persist story content for the project.
- `GET /api/rpg-projects/{project_id}/export-configs` and `POST /api/rpg-projects/{project_id}/export-configs` – manage export settings.
- `GET /api/rpg-projects/{project_id}/variables` and `POST /api/rpg-projects/{project_id}/variables` – retrieve or add project variables.
- `POST /api/rpg-projects/{project_id}/variables/generate-from-story` – generate variables from analyzed story data.
- `POST /api/rpg-projects/{project_id}/variables/{variable_id}/story-sync` – update one variable with knowledge graph values.
- `GET /api/rpg-projects/{project_id}/switches` and `POST /api/rpg-projects/{project_id}/switches` – manage project switches.
- `GET /api/rpg-projects/{project_id}/characters` and `POST /api/rpg-projects/{project_id}/characters` – access or add characters.
- `POST /api/rpg-projects/{project_id}/characters/generate-stats` – generate character stats from the story.
- `POST /api/rpg-projects/{project_id}/characters/{character_id}/enhance-from-story` – update a specific character.
- `GET /api/rpg-projects/{project_id}/characters/{character_id}/knowledge-state` and `PUT /api/rpg-projects/{project_id}/characters/{character_id}/knowledge-state` – read or update a character's knowledge state.
- `GET /api/rpg-projects/{project_id}/locations` and `POST /api/rpg-projects/{project_id}/locations` – manage locations.
- `POST /api/rpg-projects/{project_id}/locations/generate-from-story` – generate locations and connections from the story.
- `POST /api/rpg-projects/{project_id}/locations/{location_id}/enhance-from-story` – update a location with latest analysis.
- `GET /api/rpg-projects/{project_id}/locations/{location_id}/connections` and `POST /api/rpg-projects/{project_id}/locations/{location_id}/connections` – manage location connections.
- `GET /api/rpg-projects/{project_id}/quests` and `POST /api/rpg-projects/{project_id}/quests` – retrieve or add quests.
- `POST /api/rpg-projects/{project_id}/quests/generate-from-story` – generate a quest from story events with OpenAI assistance.
- `POST /api/rpg-projects/{project_id}/quests/{quest_id}/validate-story-consistency` – validate a quest against the project story.
- `GET /api/rpg-projects/{project_id}/quests/{quest_id}/character-motivations` – analyze character motivations for a quest.
- `GET /api/rpg-projects/{project_id}/dialogue-trees` and `POST /api/rpg-projects/{project_id}/dialogue-trees` – manage dialogue trees.
- `POST /api/rpg-projects/{project_id}/dialogue-trees/generate-from-story` – create a dialogue tree from story interactions.
- `POST /api/rpg-projects/{project_id}/dialogue-trees/{tree_id}/validate-consistency` – validate dialogue consistency.
- `GET /api/rpg-projects/{project_id}/dialogue-trees/{tree_id}/personality-analysis` – request an OpenAI-driven personality analysis for a tree.

These endpoints store project data in memory and leverage the agent services to populate models based on story analysis.
