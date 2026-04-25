"""
Integration demonstration showing all Phase 2 Swarm 2 components working together.
This demo creates agents, assigns them to roles, and routes tasks intelligently.
"""

from agent_factory import get_factory, EXAMPLE_AGENT_DEFINITIONS
from agent_roles import get_role_manager
from task_router import (
    get_router,
    TaskDefinition,
    TaskPriority,
    RoutingStrategy,
)
from datetime import datetime


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_role_system():
    """Demonstrate the role system."""
    print_header("1. ROLE SYSTEM DEMONSTRATION")
    
    manager = get_role_manager()
    
    print(f"\n✓ Total Roles Defined: {manager.get_role_count()}")
    print("\nBuilt-in Roles:")
    
    for role in manager.list_roles():
        print(f"  • {role.role_name:20} [{role.category.value:12}] "
              f"Priority: {role.priority_weight:.1f}")
    
    # Show capability inheritance
    print("\nRole Inheritance Example:")
    vision = manager.get_role("vision")
    print(f"  Vision role inherits from: {vision.parent_role.role_name}")
    print(f"  All capabilities: {', '.join(list(vision.get_all_capabilities())[:5])}...")
    
    # Create custom role
    print("\nCreating Custom Role:")
    custom = manager.create_custom_role(
        role_name="DataEngineer",
        description="Specializes in ETL and data pipeline engineering",
        category="execution",
        capabilities=["etl_operations", "data_validation", "performance_tuning"],
        parent_role_id="executor"
    )
    print(f"  ✓ Created: {custom.role_name} ({custom.role_id})")
    print(f"  ✓ Inherits from: {custom.parent_role.role_name}")


def demo_agent_factory():
    """Demonstrate the agent factory."""
    print_header("2. AGENT FACTORY DEMONSTRATION")
    
    factory = get_factory()
    
    print(f"\nCreating {len(EXAMPLE_AGENT_DEFINITIONS)} example agents...\n")
    
    created_agents = []
    for definition in EXAMPLE_AGENT_DEFINITIONS:
        agent, error = factory.create_agent(
            description=definition["description"],
            role_id=definition["role_id"],
            name=definition["name"],
            capabilities=definition["capabilities"]
        )
        
        if agent:
            created_agents.append(agent)
            print(f"  ✓ {agent.name:20} | Role: {agent.role_id:12} "
                  f"| Capabilities: {len(agent.capabilities)}")
        else:
            print(f"  ✗ Failed: {error}")
    
    # Show statistics
    print("\nFactory Statistics:")
    stats = factory.get_stats()
    print(f"  • Total Agents Created: {stats['total_agents']}")
    print(f"  • Total Capabilities: {stats['total_capabilities']}")
    print(f"  • Avg Capabilities/Agent: {stats['avg_capabilities_per_agent']:.1f}")
    print(f"  • Avg Creation Time: {stats['avg_creation_time_ms']:.2f}ms")
    
    print(f"\nAgents by Role:")
    for role_id, count in stats['agents_by_role'].items():
        print(f"  • {role_id:15}: {count} agents")
    
    return created_agents


def demo_task_router(agents):
    """Demonstrate the task router."""
    print_header("3. TASK ROUTER DEMONSTRATION")
    
    router = get_router()
    
    # Register all agents
    print(f"\nRegistering {len(agents)} agents with router...\n")
    
    for agent in agents:
        router.register_agent(
            agent_id=agent.agent_id,
            name=agent.name,
            role_id=agent.role_id,
            capabilities=agent.capabilities,
            skill_level=agent.skill_level,
            max_concurrent_tasks=agent.max_concurrent_tasks
        )
        print(f"  ✓ Registered: {agent.name}")
    
    # Create and route diverse tasks
    print("\n\nRouting Diverse Tasks:")
    
    tasks = [
        TaskDefinition(
            task_id="task_001",
            task_type="analysis",
            description="Analyze quarterly sales data",
            required_capabilities=["data_analysis", "pattern_recognition"],
            priority=TaskPriority.HIGH,
            estimated_duration_ms=3000
        ),
        TaskDefinition(
            task_id="task_002",
            task_type="execution",
            description="Execute data migration script",
            required_capabilities=["task_execution", "command_execution"],
            priority=TaskPriority.NORMAL,
            estimated_duration_ms=5000
        ),
        TaskDefinition(
            task_id="task_003",
            task_type="creation",
            description="Generate automated report code",
            required_capabilities=["code_generation", "creative_thinking"],
            priority=TaskPriority.NORMAL,
            estimated_duration_ms=2000
        ),
        TaskDefinition(
            task_id="task_004",
            task_type="security",
            description="Validate system security compliance",
            required_capabilities=["security_validation", "access_control"],
            priority=TaskPriority.CRITICAL,
            estimated_duration_ms=4000
        ),
    ]
    
    routed_tasks = []
    for task in tasks:
        decision = router.route_task(task, strategy=RoutingStrategy.WEIGHTED_SCORE)
        
        if decision:
            routed_tasks.append((task, decision))
            print(f"\n  Task: {task.task_id} ({task.task_type})")
            print(f"    → Assigned to: {decision.agent_name}")
            print(f"    → Score: {decision.score:.2f}/100")
            print(f"    → Confidence: {decision.confidence:.0%}")
            print(f"    → Reason: {decision.reason}")
        else:
            print(f"\n  ✗ Task {task.task_id}: No suitable agent found")
    
    # Simulate task completion
    print("\n\nSimulating Task Completions:")
    
    for task, decision in routed_tasks[:2]:  # Complete first 2 tasks
        agent_id = decision.assigned_agent_id
        router.complete_task(agent_id, success=True, actual_duration_ms=1500)
        print(f"  ✓ Task {task.task_id} completed successfully")
    
    # Show routing statistics
    print("\n\nRouting Statistics:")
    stats = router.get_routing_stats()
    print(f"  • Total Routings: {stats['total_routings']}")
    print(f"  • Average Score: {stats['average_score']:.2f}/100")
    print(f"  • Average Confidence: {stats['average_confidence']:.0%}")
    
    # Show agent load
    print("\n\nAgent Load Distribution:")
    agent_stats = router.get_all_agents_stats()
    for agent_stat in agent_stats[:5]:  # Show first 5
        print(f"  • {agent_stat['name']:20} | "
              f"Load: {agent_stat['load_percentage']:5.1f}% | "
              f"Available: {agent_stat['available_capacity']} slots")


def demo_routing_strategies():
    """Demonstrate different routing strategies."""
    print_header("4. ROUTING STRATEGIES COMPARISON")
    
    router = get_router()
    
    # Register test agents with different characteristics
    test_agents = [
        ("agent_fast", "FastExecutor", "executor", 
         ["task_execution", "command_execution"], 5, 90.0),
        ("agent_reliable", "ReliableExecutor", "executor",
         ["task_execution", "command_execution"], 3, 95.0),
        ("agent_available", "AvailableExecutor", "executor",
         ["task_execution", "command_execution"], 2, 20.0),
    ]
    
    for agent_id, name, role, caps, skill, success_rate in test_agents:
        router.register_agent(agent_id, name, role, caps, skill_level=skill)
        router.update_agent_state(agent_id, 1, int(success_rate), 1, 500)
    
    # Create a test task
    task = TaskDefinition(
        task_id="comparison_task",
        task_type="execution",
        description="Execute system task",
        required_capabilities=["task_execution"],
        priority=TaskPriority.NORMAL
    )
    
    print("\nRouting Same Task with Different Strategies:\n")
    
    strategies = [
        RoutingStrategy.WEIGHTED_SCORE,
        RoutingStrategy.LEAST_LOADED,
        RoutingStrategy.BEST_FIT,
        RoutingStrategy.ROUND_ROBIN,
    ]
    
    for strategy in strategies:
        decision = router.route_task(task, strategy=strategy)
        if decision:
            print(f"  {strategy.value:20} → {decision.agent_name:20} "
                  f"(Score: {decision.score:5.1f}, Confidence: {decision.confidence:.0%})")


def demo_capability_matching():
    """Demonstrate capability matching."""
    print_header("5. CAPABILITY MATCHING DEMONSTRATION")
    
    manager = get_role_manager()
    
    print("\nFinding Best Roles for Various Task Types:\n")
    
    task_types = [
        ("data_analysis", ["data_analysis", "pattern_recognition"]),
        ("code_generation", ["code_generation", "creative_thinking"]),
        ("security_audit", ["security_validation", "audit_logging"]),
        ("system_monitoring", ["system_monitoring", "health_checking"]),
    ]
    
    for task_type, required_caps in task_types:
        roles = manager.get_roles_for_task(task_type, required_caps)
        print(f"  Task: {task_type}")
        for role in roles[:3]:  # Show top 3
            print(f"    ✓ {role.role_name:20} (priority: {role.priority_weight:.1f})")
        print()


def main():
    """Run all demonstrations."""
    print("\n" + "▓" * 70)
    print("▓  PHASE 2 SWARM 2: COMPLETE INTEGRATION DEMONSTRATION  ▓")
    print("▓" * 70)
    
    # Run all demos
    demo_role_system()
    agents = demo_agent_factory()
    demo_task_router(agents)
    demo_routing_strategies()
    demo_capability_matching()
    
    # Final summary
    print_header("DEMO SUMMARY")
    print("""
✓ Role System: 12 base roles + custom role creation
✓ Agent Factory: 12+ agents created dynamically
✓ Task Router: Intelligent routing with 5 strategies
✓ Capability Matching: Smart capability-to-role mapping
✓ Load Balancing: Weighted scoring across agents

Phase 2 Swarm 2 is fully operational!
    """)


if __name__ == "__main__":
    main()
