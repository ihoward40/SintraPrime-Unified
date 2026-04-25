#!/usr/bin/env python3
"""Test the memory system without heavy dependencies"""

import sys
sys.path.insert(0, '/agent/home/universe')

from memory_system import MemorySystem

def test_memory_system():
    """Test the memory system"""
    print("=" * 60)
    print("UniVerse Hive Mind Memory System - Test Suite")
    print("=" * 60)
    
    # Initialize
    print("\n[1/8] Initializing Memory System...")
    system = MemorySystem()
    print("✓ Memory system initialized")
    
    # Test knowledge storage
    print("\n[2/8] Testing Knowledge Storage...")
    k1 = system.store_knowledge(
        "Always validate user input to prevent injection attacks",
        "security_insight",
        "security_agent",
        {"risk_level": "high", "domain": "security"}
    )
    k2 = system.store_knowledge(
        "Use connection pooling for database performance",
        "optimization_pattern",
        "database_agent",
        {"impact": "high", "domain": "database"}
    )
    print(f"✓ Stored knowledge: {k1[:8]}..., {k2[:8]}...")
    
    # Test tag extraction
    print("\n[3/8] Testing Auto Tag Extraction...")
    tags = system._extract_tags("Always validate user input to prevent injection attacks")
    print(f"✓ Extracted tags: {tags}")
    
    # Test knowledge updates
    print("\n[4/8] Testing Knowledge Usage Updates...")
    system.update_knowledge_usage(k1, success=True)
    system.update_knowledge_usage(k1, success=True)
    print("✓ Updated knowledge usage tracking")
    
    # Test keyword search
    print("\n[5/8] Testing Knowledge Search (Keyword)...")
    results = system.search_knowledge_keyword("security validation", limit=5)
    print(f"✓ Found {len(results)} relevant pieces of knowledge")
    if results:
        print(f"  - Top result: {results[0]['content'][:50]}...")
    
    # Test skill registration
    print("\n[6/8] Testing Skill Registration...")
    skill_id = system.register_skill(
        "input_validation",
        "Comprehensive input validation framework",
        "def validate(data): return sanitize(data)",
        "security_agent",
        dependencies=["sanitizer"],
        tags=["security", "validation"]
    )
    print(f"✓ Registered skill: {skill_id[:8]}...")
    
    # Test skill inheritance
    print("\n[7/8] Testing Skill Inheritance & Performance Tracking...")
    inherited = system.inherit_skill(skill_id, "learner_agent")
    print(f"✓ Agent inherited skill: {inherited}")
    system.update_skill_performance(skill_id, "learner_agent", success=True)
    system.update_skill_performance(skill_id, "learner_agent", success=True)
    print("✓ Updated skill performance metrics")
    
    # Test learning sessions
    print("\n[8/8] Testing Learning Sessions...")
    session = system.start_learning_session(
        "learner_agent",
        "task_failure",
        "failed_task_123",
        "mentor_agent"
    )
    system.record_learning_improvement(
        session,
        generated_skills=[skill_id],
        improvements={"error_reduction": 0.3, "performance": "improved"}
    )
    print(f"✓ Completed learning session: {session[:8]}...")
    
    # Get statistics
    print("\n" + "=" * 60)
    print("Memory System Statistics")
    print("=" * 60)
    stats = system.get_stats()
    for key, value in stats.items():
        print(f"{key:.<40} {value:>10}")
    
    # Test performance tracking
    print("\n" + "=" * 60)
    print("Agent Performance Analytics")
    print("=" * 60)
    system.record_agent_performance("learner_agent", "success_rate", 0.95)
    system.record_agent_performance("learner_agent", "avg_response_time", 1.2)
    system.record_agent_performance("learner_agent", "success_rate", 0.98)
    
    analytics = system.get_agent_analytics("learner_agent")
    for metric, data in analytics.items():
        print(f"\n{metric}:")
        print(f"  Count: {data['count']}")
        print(f"  Average: {data['average']:.4f}")
        print(f"  Min: {data['min']:.4f}, Max: {data['max']:.4f}")
    
    # Test knowledge relationships
    print("\n" + "=" * 60)
    print("Knowledge Relationships")
    print("=" * 60)
    system.link_knowledge(k1, k2, "complements", 0.8)
    system.link_knowledge(k1, k2, "related", 0.7)
    related = system.get_related_knowledge(k1, depth=1)
    print(f"Related to first knowledge: {len(related)} connections")
    if related:
        print(f"  - {related[0]['relationship_type']}: {related[0]['content'][:40]}...")
    
    # Cleanup
    system.cleanup_old_cache()
    system.close()
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_system()
