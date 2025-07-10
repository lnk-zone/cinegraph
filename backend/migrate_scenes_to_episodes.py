#!/usr/bin/env python3
"""
One-time Migration Script: Scenes to Episodes (Chapters)
======================================================

This script transforms existing scenes into episodes of type 'Chapter'.
Assumptions:
- Scenes already exist in the database
- Episodes table has been created and is ready for inserting new entries
"""

import os
import asyncpg
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Database connection details
DATABASE_URL = os.getenv('DATABASE_URL')

async def migrate_scenes_to_episodes():
    """Back-fill scenes to episodes"""

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Retrieve scenes
        scenes = await conn.fetch('''
            SELECT scene_id, title, story_id, user_id
            FROM public.scenes;
        ''')

        # Insert scenes as Chapter episodes
        for scene in scenes:
            await conn.execute('''
                INSERT INTO public.episodes (episode_id, title, episode_type, story_id, user_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (episode_id) DO NOTHING;
            ''', f"chapter-{scene['scene_id']}", scene['title'], 'Chapter', scene['story_id'], scene['user_id'])

        print(f"{len(scenes)} scenes migrated to episodes (as Chapters).")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_scenes_to_episodes())

