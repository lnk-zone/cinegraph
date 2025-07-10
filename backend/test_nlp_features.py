#!/usr/bin/env python3
"""
Standalone test for StoryProcessor NLP features
Tests scene segmentation, POV detection, and continuity analysis
"""

import re
import uuid
from typing import Dict, List, Any
from collections import Counter

# Sample story content for testing
SAMPLE_STORY = """
Chapter 1: The Beginning

I woke up in a strange place. The room was dark and I couldn't remember how I got there. Fear gripped my heart as I realized I was completely alone.

Meanwhile, in another part of the city, Sarah was having coffee with her friend Mark. They were discussing the mysterious disappearances that had been happening lately.

Chapter 2: The Discovery

Hours later, I found a hidden door behind the bookshelf. As I had predicted earlier, this house held many secrets. The corridor beyond was filled with ancient symbols.

Sarah received a call from the police. Another person had gone missing - someone she knew. Little did she know that this case would change everything.

***

The final confrontation was intense. I remembered what my grandmother had told me years ago about the old mansion. Everything was connected - the disappearances, the symbols, the dreams I'd been having.

Sarah and I finally met at the mansion. The truth was more terrifying than either of us had imagined.
"""

def detect_chapter_boundaries(text: str) -> Dict[str, Any]:
    """Detect chapter boundaries using simple NLP heuristics."""
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

def detect_pov(text: str) -> Dict[str, Any]:
    """Detect point of view using NLP analysis."""
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

def detect_story_arc(text: str) -> Dict[str, Any]:
    """Detect story arc elements using NLP heuristics."""
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

def analyze_mood_lexical(text: str) -> Dict[str, Any]:
    """Analyze mood using lexical patterns."""
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
        "method": "lexical"
    }

def detect_continuity_patterns(text: str) -> List[str]:
    """Detect continuity patterns in text."""
    patterns = [
        r'\b(remember|recalled?|flashback|flash back)\b',
        r'\b(foreshadow|foretold?|prophes|predict)\b',
        r'\b(earlier|before|previously|past)\b.*\b(mentioned|said|told)\b',
        r'\b(later|future|will|shall)\b.*\b(see|find|discover|learn)\b',
        r'\b(as .* had said|as .* predicted|just as .* warned)\b',
        r'\b(little did .* know|unbeknownst|unknown to)\b'
    ]
    
    found_patterns = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found_patterns.extend(matches)
    
    return found_patterns

def split_into_scenes(content: str) -> List[Dict[str, Any]]:
    """Split content into scenes with enhanced metadata."""
    # Split by double newlines or scene markers
    paragraphs = re.split(r'\n\s*\n|\n\s*---\s*\n|\n\s*\*\*\*\s*\n', content.strip())
    
    scenes = []
    current_chapter = 1
    current_episode = 1
    
    for i, paragraph in enumerate(paragraphs):
        paragraph = paragraph.strip()
        if paragraph:  # Skip empty paragraphs
            scene_id = f"scene_{i+1}_{uuid.uuid4().hex[:8]}"
            
            # Detect chapter/episode boundaries
            chapter_indicators = detect_chapter_boundaries(paragraph)
            
            if chapter_indicators['is_new_chapter']:
                current_chapter += 1
                current_episode = 1  # Reset episode count for new chapter
            elif i > 0 and i % 3 == 0:  # Simple episode detection
                current_episode += 1
            
            # Extract narrative information
            arc_info = detect_story_arc(paragraph)
            pov_info = detect_pov(paragraph)
            mood_info = analyze_mood_lexical(paragraph)
            continuity_patterns = detect_continuity_patterns(paragraph)
            
            scene_data = {
                "id": scene_id,
                "text": paragraph,
                "order": i + 1,
                "word_count": len(paragraph.split()),
                "chapter": current_chapter,
                "episode": current_episode,
                "chapter_boundary": chapter_indicators,
                "story_arc": arc_info,
                "pov": pov_info,
                "mood": mood_info,
                "continuity_patterns": continuity_patterns
            }
            
            scenes.append(scene_data)
    
    return scenes

def main():
    """Test the NLP features"""
    print("🧪 Testing StoryProcessor NLP Features...")
    
    # Test scene splitting and analysis
    print("\n📖 Testing scene splitting and metadata extraction...")
    scenes = split_into_scenes(SAMPLE_STORY)
    
    print(f"Found {len(scenes)} scenes\n")
    
    for i, scene in enumerate(scenes):
        print(f"Scene {i+1}:")
        print(f"  Chapter: {scene['chapter']}, Episode: {scene['episode']}")
        print(f"  POV: {scene['pov']['type']} (confidence: {scene['pov']['confidence']:.2f})")
        print(f"  Story Arc: {scene['story_arc']['primary_arc']} (intensity: {scene['story_arc']['intensity']})")
        print(f"  Mood: {scene['mood']['primary_mood']} (intensity: {scene['mood']['intensity']:.2f})")
        print(f"  Chapter Boundary: {scene['chapter_boundary']['is_new_chapter']}")
        print(f"  Continuity Patterns: {len(scene['continuity_patterns'])} found")
        if scene['continuity_patterns']:
            for pattern in scene['continuity_patterns'][:2]:  # Show first 2
                print(f"    - {pattern}")
        print(f"  Text Preview: {scene['text'][:100]}...")
        print()
    
    # Summary statistics
    total_words = sum(scene['word_count'] for scene in scenes)
    total_chapters = max(scene['chapter'] for scene in scenes)
    total_episodes = sum(1 for scene in scenes if scene['episode'] == 1)  # Count episode starts
    
    print("\n📊 Summary Statistics:")
    print(f"  Total Words: {total_words}")
    print(f"  Total Chapters: {total_chapters}")
    print(f"  Total Episodes: {total_episodes}")
    print(f"  Average Scene Length: {total_words / len(scenes):.1f} words")
    
    # POV distribution
    pov_distribution = {}
    for scene in scenes:
        pov_type = scene['pov']['type']
        pov_distribution[pov_type] = pov_distribution.get(pov_type, 0) + 1
    
    print(f"  POV Distribution: {pov_distribution}")
    
    # Mood distribution
    mood_distribution = {}
    for scene in scenes:
        mood = scene['mood']['primary_mood']
        mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
    
    print(f"  Mood Distribution: {mood_distribution}")
    
    print("\n✅ All NLP feature tests completed!")

if __name__ == "__main__":
    main()
