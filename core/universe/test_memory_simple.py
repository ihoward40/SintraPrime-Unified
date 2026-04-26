#!/usr/bin/env python3
"""Simple test of memory system without embeddings"""

import sys
import os

# Disable embeddings
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/tmp'

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent))

# Mock sentence transformers to prevent loading
class MockSentenceTransformer:
    def encode(self, text, convert_to_numpy=False):
        # Return a dummy embedding
        return [0.1] * 384

sys.modules['sentence_transformers'] = type(sys)('sentence_transformers')
sys.modules['sentence_transformers'].SentenceTransformer = MockSentenceTransformer

from memory_system import MemorySystem

def test_memory_system():
    """Test the memory system"""
    print("=" * 60)
    print("UniVerse Hive Mind Memory System - Basic Test")
    print("=" * 60)
    
    # Initialize
    print("\n[1/7] Initializing Memory System...")
    system = MemorySystem(db_path='/tmp/test_memory.db')
    print("✓ Memory system initialized")
    print(f"  Embeddings available: {system.embedder is not None}")
    
    # Test knowledge storage
    print("\n[2/7] Testing Knowledge Storage...")
    k1 = system.store_knowledge(
        "Always validate user input to prevent injection attacks",
        "security_insight",
        "security_agent",
        {"risk_level": "high"}
    )
    k2 = system.store_knowledge(
        "Use connection pooling for database performance",
        "optimization_pattern",
        "database_agent",
        {"impact": "high"}
    )
    print(f"✓ Stored 2 knowledge items")
    
    # Test tag extraction
    print("\n[3/7] Testing Auto Tag Extraction...")
    tags = system._extract_tags("Always validate user input to prevent injection attacks")
    print(f"✓ Extracted tags: {tags[:3]}")
    
    # Test knowledge updates
    print("\n[4/7] Testing Knowledge Usage Tracking...")
    system.update_knowledge_usage(k1, success=True)
    system.update_knowledge_usage(k1, success=True)
    print("✓ Updated knowledge usage")
    
    # Test skill registration
    print("\n[5/7] Testing Skill Registration...")
    skill_id = system.register_skill(
        "input_validation",
        "Comprehensive input validation",
        "def validate(data): pass",
        "security_agent",
        tags=["security"]
    )
    print(f"✓ Registered skill")
    
    # Test skill inheritance
    print("\n[6/7] Testing Skill Inheritance...")
    system.inherit_skill(skill_id, "learner_agent")
    system.update_skill_performance(skill_id, "learner_agent", success=True)
    print("✓ Agent inherited skill")
    
    # Get statistics
    print("\n[7/7] Memory System Statistics")
    stats = system.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    system.close()
    
    print("\n" + "=" * 60)
    print("✓ All basic tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_system()
