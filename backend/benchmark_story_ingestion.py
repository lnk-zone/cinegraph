#!/usr/bin/env python3
"""
Performance benchmark for story ingestion pipeline
Target: <300ms for 2K words
"""

import asyncio
import os
import sys
import time
from datetime import datetime
import statistics

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager


def generate_test_story(word_count: int = 2000) -> str:
    """Generate a test story with approximately the specified word count"""
    
    base_story = """
    The brave knight Sir Gallant rode through the enchanted forest on his noble steed. 
    The ancient trees whispered secrets of old magic, and mystical creatures watched from 
    the shadows. His quest was to find the legendary Crystal of Eternal Light, hidden 
    deep within the Dragon's Lair.
    
    Along his journey, Sir Gallant met a wise old hermit who lived in a stone cottage 
    beside a babbling brook. The hermit, named Eldric, possessed knowledge of ancient 
    spells and the location of the dragon's treasure. He warned Sir Gallant about the 
    perils ahead and gave him a magical amulet for protection.
    
    As Sir Gallant continued deeper into the forest, he encountered a group of bandits 
    who had been terrorizing local villages. Using his sword skills and quick thinking, 
    he defeated the bandits and freed their captives. Among the rescued was a young 
    princess named Aria, who had been kidnapped from the nearby Kingdom of Astoria.
    
    Princess Aria revealed that she too was seeking the Crystal of Eternal Light, as 
    it was the only thing that could save her kingdom from a terrible curse. Together, 
    they formed an alliance and continued toward the dragon's lair, facing many 
    challenges along the way.
    
    The dragon, a massive creature with scales like emeralds and eyes like burning 
    coals, guarded the crystal jealously. The battle was fierce and dangerous, but 
    Sir Gallant and Princess Aria worked together to defeat the beast and claim the 
    crystal. With the crystal in hand, they returned to Astoria and lifted the curse, 
    saving the kingdom and its people.
    """
    
    # Repeat and extend the base story to reach the target word count
    words = base_story.split()
    current_words = len(words)
    
    if current_words >= word_count:
        return ' '.join(words[:word_count])
    
    # Extend the story by repeating and modifying sections
    extensions = [
        "The celebration in the kingdom lasted for days. People came from far and wide to honor the heroes.",
        "Sir Gallant was knighted as the Royal Champion, and Princess Aria became the beloved ruler of Astoria.",
        "The crystal was placed in the kingdom's treasury, where it would protect the land for generations to come.",
        "New adventures awaited our heroes, as rumors of other mystical artifacts began to spread throughout the realm.",
        "The enchanted forest remained a place of wonder and mystery, where future heroes would test their courage.",
        "Eldric the hermit continued to help travelers, sharing his wisdom with those who sought to do good in the world.",
        "The defeated dragon's lair became a sacred site, where pilgrims would come to pray for strength and guidance.",
        "Trade routes reopened between kingdoms, bringing prosperity and peace to the land once again.",
        "The tale of Sir Gallant and Princess Aria became legend, inspiring young knights and princesses everywhere.",
        "Magic flowed more freely through the land, blessing crops and bringing good fortune to all who lived there."
    ]
    
    result = base_story
    extension_index = 0
    
    while len(result.split()) < word_count:
        result += "\n\n" + extensions[extension_index % len(extensions)]
        extension_index += 1
    
    # Trim to exact word count
    final_words = result.split()[:word_count]
    return ' '.join(final_words)


async def benchmark_story_ingestion():
    """Benchmark the story ingestion pipeline"""
    
    print("=== Story Ingestion Performance Benchmark ===")
    print("Target: <300ms for 2K words")
    print()
    
    # Test different word counts
    test_cases = [
        {"words": 500, "description": "Short story (500 words)"},
        {"words": 1000, "description": "Medium story (1K words)"},
        {"words": 2000, "description": "Target story (2K words)"},
        {"words": 3000, "description": "Long story (3K words)"},
    ]
    
    try:
        # Initialize components
        print("Initializing GraphitiManager...")
        graphiti_manager = GraphitiManager()
        await graphiti_manager.initialize()
        
        print("Initializing StoryProcessor...")
        story_processor = StoryProcessor(graphiti_manager=graphiti_manager)
        
        results = []
        
        for test_case in test_cases:
            print(f"\n=== Testing {test_case['description']} ===")
            
            # Generate test story
            test_story = generate_test_story(test_case['words'])
            actual_word_count = len(test_story.split())
            
            print(f"Generated story: {actual_word_count} words, {len(test_story)} characters")
            
            # Run multiple iterations for more accurate timing
            times = []
            iterations = 3
            
            for i in range(iterations):
                story_id = f"benchmark_story_{test_case['words']}_{i}"
                
                start_time = time.perf_counter()
                result = await story_processor.process_story(test_story, story_id)
                end_time = time.perf_counter()
                
                processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(processing_time)
                
                print(f"  Iteration {i+1}: {processing_time:.2f}ms")
                
                # Check for errors
                if "error" in result:
                    print(f"    ❌ Error: {result['error']}")
                else:
                    print(f"    ✅ Extracted {len(result.get('entities', []))} entities, "
                          f"{len(result.get('relationships', []))} relationships")
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Min: {min_time:.2f}ms")
            print(f"  Max: {max_time:.2f}ms")
            
            # Check performance target
            if test_case['words'] <= 2000:
                if avg_time < 300:
                    print(f"  ✅ Performance target met (avg: {avg_time:.2f}ms < 300ms)")
                else:
                    print(f"  ❌ Performance target not met (avg: {avg_time:.2f}ms >= 300ms)")
            
            results.append({
                "words": actual_word_count,
                "description": test_case['description'],
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "times": times
            })
        
        # Summary
        print("\n=== Performance Summary ===")
        print(f"{'Test Case':<25} {'Words':<8} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12} {'Target Met'}")
        print("-" * 85)
        
        for result in results:
            target_met = "✅ Yes" if result['words'] <= 2000 and result['avg_time'] < 300 else "❌ No"
            if result['words'] > 2000:
                target_met = "N/A"
            
            print(f"{result['description']:<25} {result['words']:<8} {result['avg_time']:<12.2f} "
                  f"{result['min_time']:<12.2f} {result['max_time']:<12.2f} {target_met}")
        
        # Performance analysis
        print("\n=== Performance Analysis ===")
        
        # Find the 2K word test result
        two_k_result = next((r for r in results if r['words'] >= 1900 and r['words'] <= 2100), None)
        if two_k_result:
            print(f"2K word performance: {two_k_result['avg_time']:.2f}ms average")
            if two_k_result['avg_time'] < 300:
                print("🎯 Target achieved! Pipeline processes 2K words in <300ms")
            else:
                print("⚠️  Target not achieved. Consider optimizations:")
                print("  - Batch processing of scenes")
                print("  - Caching of GraphitiManager connections")
                print("  - Parallel processing of independent scenes")
        
        # Calculate words per second
        if two_k_result:
            words_per_second = (two_k_result['words'] / two_k_result['avg_time']) * 1000
            print(f"Processing speed: {words_per_second:.0f} words/second")
        
    except Exception as e:
        print(f"❌ Benchmark failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if 'graphiti_manager' in locals():
            await graphiti_manager.close()


if __name__ == "__main__":
    asyncio.run(benchmark_story_ingestion())
