"""
UniVerse Swarm Patterns - Practical Examples

Demonstrates how to use each of the 5 pre-configured swarm patterns
for real-world scenarios.
"""

import asyncio
import json
from swarm_patterns import SwarmFactory, AgentRole


# ============================================================================
# RESEARCH SWARM EXAMPLES
# ============================================================================


async def example_research_competitors():
    """
    Research Swarm: Analyze competitive landscape
    
    This example shows how to use the Research Swarm to gather information
    about competing products and create a comprehensive comparison.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Research Competitive Landscape")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('research')
    
    # Launch with custom configuration
    print("\n[1] Launching Research Swarm...")
    await swarm.launch(model="claude-3.5-sonnet", timeout_seconds=300)
    print(f"    ✓ Swarm initialized with {len(swarm.agents)} agents")
    
    # Pre-populate knowledge base with context
    print("\n[2] Setting up knowledge base...")
    swarm.update_knowledge_base("research_scope", {
        "focus_areas": ["Features", "Pricing", "Market Position", "Technology"],
        "competitors": ["Anthropic Claude", "OpenAI GPT", "Google Gemini"]
    })
    print("    ✓ Knowledge base initialized")
    
    # Submit research task
    print("\n[3] Submitting research tasks...")
    task_id = await swarm.execute(
        "Research AI agent platforms (Anthropic, OpenAI, Google) and create "
        "detailed comparison of features, pricing, and capabilities",
        priority=8
    )
    print(f"    ✓ Task submitted: {task_id}")
    
    # Monitor progress
    print("\n[4] Monitoring swarm progress...")
    for i in range(5):
        status = swarm.get_status()
        tasks = status['tasks']
        agents = status['agents']
        print(f"    [{i+1}/5] Tasks: {tasks['completed']} complete, "
              f"{tasks['in_progress']} in progress | "
              f"Agents: {agents['by_status']['idle']} idle, "
              f"{agents['by_status']['working']} working")
        await asyncio.sleep(0.5)
    
    # Retrieve results
    print("\n[5] Retrieving results...")
    result = swarm.get_results(task_id)
    print(f"    ✓ Task status: {result['status']}")
    print(f"    ✓ Output: {str(result.get('result', 'N/A'))[:100]}...")
    
    # Get knowledge accumulated by swarm
    knowledge = swarm.get_knowledge_base()
    print(f"    ✓ Knowledge base now contains {len(knowledge)} items")
    
    # Shutdown
    print("\n[6] Shutting down swarm...")
    shutdown_result = await swarm.shutdown()
    print(f"    ✓ Shutdown complete: {shutdown_result['tasks_completed']} tasks done")


async def example_research_trends():
    """
    Research Swarm: Identify technology trends
    
    Demonstrates using the Research Swarm for trend analysis and
    future forecasting.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Identify Technology Trends")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('research')
    await swarm.launch()
    
    print("\n[1] Submitting trend analysis task...")
    
    # Add specialized trend analyst
    trend_analyst = swarm.add_agent(
        role=AgentRole.ANALYST,
        specialization="trend_forecasting"
    )
    print(f"    ✓ Added trend analyst: {trend_analyst}")
    
    # Submit multi-faceted research task
    task_id = await swarm.execute(
        "Analyze emerging trends in AI agents: identify 5 key trends, "
        "provide evidence for each, predict impact",
        priority=7
    )
    
    print(f"    ✓ Task queued: {task_id}")
    
    # Monitor until complete
    await asyncio.sleep(1)
    
    # Get results
    result = swarm.get_results(task_id)
    print(f"\n[2] Results:")
    print(f"    Status: {result['status']}")
    print(f"    Completed: {result['completed_at']}")
    
    await swarm.shutdown()


# ============================================================================
# DEVELOPMENT SWARM EXAMPLES
# ============================================================================


async def example_develop_feature():
    """
    Development Swarm: Build a new feature with full quality assurance
    
    Shows how to use the Development Swarm to implement a feature with
    backend, frontend, security review, and testing.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Develop New Feature with QA")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('development')
    
    print("\n[1] Launching Development Swarm...")
    await swarm.launch(timeout_seconds=600)
    print(f"    ✓ Swarm ready with {len(swarm.agents)} agents")
    
    # Store design specifications in knowledge base
    print("\n[2] Storing design specifications...")
    swarm.update_knowledge_base("feature_spec", {
        "name": "User API Rate Limiting",
        "requirements": [
            "Implement token bucket algorithm",
            "Support per-user and per-IP limits",
            "Return proper HTTP 429 responses",
            "Include rate limit headers in response"
        ],
        "security_requirements": [
            "Prevent DDoS attacks",
            "Validate input parameters",
            "Log all rate limit violations"
        ]
    })
    print("    ✓ Specifications stored")
    
    # Submit development task
    print("\n[3] Submitting development task...")
    task_id = await swarm.execute(
        "Implement API rate limiting feature using token bucket algorithm. "
        "Include backend implementation, UI dashboard, full test coverage, "
        "and security audit",
        priority=9
    )
    print(f"    ✓ Feature development task: {task_id}")
    
    # Monitor progress
    print("\n[4] Progress tracking...")
    for i in range(3):
        status = swarm.get_status()
        print(f"    [{i+1}/3] {status['metrics']['tasks_completed']} tasks complete, "
              f"success rate: {status['metrics']['success_rate']:.1%}")
        await asyncio.sleep(0.5)
    
    # Shutdown
    print("\n[5] Completing development cycle...")
    result = await swarm.shutdown()
    print(f"    ✓ Development complete: {result['tasks_completed']} subtasks")


async def example_code_review():
    """
    Development Swarm: Comprehensive code review
    
    Demonstrates using the Development Swarm for reviewing existing code
    with focus on security and best practices.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Comprehensive Code Review")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('development')
    await swarm.launch()
    
    print("\n[1] Preparing code review...")
    
    # Store code to review
    swarm.update_knowledge_base("code_to_review", {
        "file": "authentication.py",
        "lines": 250,
        "language": "Python",
        "review_focus": ["Security", "Performance", "Maintainability"]
    })
    
    # Submit code review task
    task_id = await swarm.execute(
        "Perform comprehensive code review of authentication module: "
        "check for security vulnerabilities, performance issues, "
        "code quality, and maintainability. Suggest improvements.",
        priority=8
    )
    print(f"    ✓ Code review task: {task_id}")
    
    await asyncio.sleep(1)
    
    # Results
    result = swarm.get_results(task_id)
    print(f"\n[2] Review complete:")
    print(f"    Status: {result['status']}")
    
    await swarm.shutdown()


# ============================================================================
# OPERATIONS SWARM EXAMPLES
# ============================================================================


async def example_incident_response():
    """
    Operations Swarm: Respond to critical incident
    
    Shows how to use the Operations Swarm to diagnose and fix
    a production issue quickly.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Incident Response and Resolution")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('operations')
    
    print("\n[1] Launching Operations Swarm in CRITICAL mode...")
    await swarm.launch(timeout_seconds=300)
    
    # Set up incident context
    print("\n[2] Storing incident context...")
    swarm.update_knowledge_base("incident", {
        "severity": "CRITICAL",
        "alert": "API response time > 5000ms",
        "affected_services": ["API Gateway", "User Service", "Database"],
        "impact": "50% of requests timing out"
    })
    
    # Submit high-priority incident task
    print("\n[3] Submitting incident response task...")
    task_id = await swarm.execute(
        "CRITICAL: API response time degradation. Diagnose cause "
        "(check metrics, logs, database queries), identify root cause, "
        "implement immediate fix or workaround",
        priority=10  # Highest priority
    )
    print(f"    ✓ Incident task: {task_id}")
    
    # Fast monitoring
    print("\n[4] Rapid response tracking...")
    for i in range(5):
        status = swarm.get_status()
        result = swarm.get_results(task_id)
        if result['status'] == 'completed':
            print(f"    ✓ RESOLVED in {i} cycles")
            break
        print(f"    [{i+1}/5] Agents working: "
              f"{status['agents']['by_status']['working']}")
        await asyncio.sleep(0.3)
    
    await swarm.shutdown()


async def example_performance_optimization():
    """
    Operations Swarm: Optimize system performance
    
    Demonstrates using the Operations Swarm for proactive performance
    improvement and optimization.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Performance Optimization")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('operations')
    await swarm.launch()
    
    print("\n[1] Setting up optimization scope...")
    swarm.update_knowledge_base("optimization_scope", {
        "target": "Database layer",
        "current_metrics": {
            "avg_query_time_ms": 450,
            "slow_queries_percent": 15,
            "connection_pool_util": 0.85
        },
        "goals": {
            "target_avg_ms": 100,
            "slow_queries_percent": 5,
            "connection_pool_util": 0.6
        }
    })
    
    # Submit optimization task
    task_id = await swarm.execute(
        "Optimize database performance: identify slow queries, "
        "analyze execution plans, suggest indexes, optimize connection pooling",
        priority=6
    )
    print(f"    ✓ Optimization task: {task_id}")
    
    await asyncio.sleep(1)
    
    # Results
    result = swarm.get_results(task_id)
    print(f"\n[2] Optimization results:")
    print(f"    Status: {result['status']}")
    
    await swarm.shutdown()


# ============================================================================
# CONTENT SWARM EXAMPLES
# ============================================================================


async def example_create_blog_post():
    """
    Content Swarm: Write and publish a blog post
    
    Shows how to use the Content Swarm to create a complete,
    SEO-optimized blog post with visuals.
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Create Blog Post with SEO Optimization")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('content')
    
    print("\n[1] Launching Content Swarm...")
    await swarm.launch()
    
    # Store blog requirements
    print("\n[2] Setting content requirements...")
    swarm.update_knowledge_base("blog_brief", {
        "title": "The Complete Guide to AI Agents",
        "target_audience": "Technical managers and developers",
        "word_count": 2500,
        "seo_keywords": ["AI agents", "multi-agent systems", "LLM"],
        "structure": [
            "Introduction",
            "What are AI Agents?",
            "Types of Agents",
            "Use Cases",
            "Implementation Guide",
            "Conclusion"
        ]
    })
    print("    ✓ Content brief prepared")
    
    # Submit content creation task
    print("\n[3] Submitting content task...")
    task_id = await swarm.execute(
        "Write comprehensive blog post 'The Complete Guide to AI Agents' "
        "with SEO optimization, professional visuals, and engaging layout. "
        "2500 words, technical but accessible.",
        priority=7
    )
    print(f"    ✓ Content task: {task_id}")
    
    # Monitor writing progress
    print("\n[4] Content creation in progress...")
    for i in range(4):
        status = swarm.get_status()
        agents_working = status['agents']['by_status']['working']
        print(f"    [{i+1}/4] {agents_working} agents writing/editing/designing")
        await asyncio.sleep(0.5)
    
    # Final results
    result = swarm.get_results(task_id)
    print(f"\n[5] Blog post complete:")
    print(f"    Status: {result['status']}")
    
    await swarm.shutdown()


async def example_create_documentation():
    """
    Content Swarm: Create technical documentation
    
    Demonstrates using the Content Swarm for creating comprehensive
    technical documentation.
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Create Technical Documentation")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('content')
    await swarm.launch()
    
    print("\n[1] Starting documentation task...")
    
    task_id = await swarm.execute(
        "Create comprehensive API documentation for REST endpoints: "
        "include overview, authentication, endpoints, examples, error codes, "
        "with diagrams and code snippets",
        priority=6
    )
    print(f"    ✓ Documentation task: {task_id}")
    
    await asyncio.sleep(1)
    
    result = swarm.get_results(task_id)
    print(f"\n[2] Documentation ready:")
    print(f"    Status: {result['status']}")
    
    await swarm.shutdown()


# ============================================================================
# SALES SWARM EXAMPLES
# ============================================================================


async def example_lead_generation():
    """
    Sales Swarm: Generate and qualify sales leads
    
    Shows how to use the Sales Swarm to find qualified leads
    and create personalized outreach.
    """
    print("\n" + "="*80)
    print("EXAMPLE 9: Lead Generation and Qualification")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('sales')
    
    print("\n[1] Launching Sales Swarm...")
    await swarm.launch()
    
    # Set up lead profile
    print("\n[2] Configuring target profile...")
    swarm.update_knowledge_base("ideal_customer", {
        "industry": "Technology / SaaS",
        "company_size": "50-500 employees",
        "annual_revenue": "$10M-$100M",
        "pain_points": ["AI integration", "Automation", "Scalability"],
        "decision_makers": ["VP Engineering", "CTO", "CEO"]
    })
    print("    ✓ Target profile set")
    
    # Submit lead generation task
    print("\n[3] Submitting lead generation task...")
    task_id = await swarm.execute(
        "Find 20 qualified leads matching our ideal customer profile "
        "in the SaaS/Technology space. Include company info, decision makers, "
        "relevant contact info, and personalized outreach angles.",
        priority=8
    )
    print(f"    ✓ Lead generation task: {task_id}")
    
    # Monitor parallel research
    print("\n[4] Lead research in progress...")
    for i in range(4):
        status = swarm.get_status()
        tasks = status['tasks']
        print(f"    [{i+1}/4] {tasks['completed']} complete, "
              f"{tasks['in_progress']} in progress")
        await asyncio.sleep(0.5)
    
    # Results with leads
    result = swarm.get_results(task_id)
    print(f"\n[5] Lead list ready:")
    print(f"    Status: {result['status']}")
    print(f"    Qualified leads: 20")
    
    await swarm.shutdown()


async def example_campaign_preparation():
    """
    Sales Swarm: Prepare targeted sales campaign
    
    Demonstrates using the Sales Swarm to research prospects
    and prepare personalized outreach campaign.
    """
    print("\n" + "="*80)
    print("EXAMPLE 10: Targeted Campaign Preparation")
    print("="*80)
    
    swarm = SwarmFactory.create_swarm('sales')
    await swarm.launch()
    
    print("\n[1] Setting up campaign...")
    
    swarm.update_knowledge_base("campaign_target", {
        "company": "TechCorp Inc",
        "industry": "AI/ML",
        "size": "200 employees",
        "recent_news": "Just raised Series B funding",
        "our_solution_relevance": "Can help with ML ops automation"
    })
    
    # Submit campaign prep task
    task_id = await swarm.execute(
        "Research TechCorp Inc: analyze their tech stack, identify decision makers, "
        "research their recent news, create 3 personalized outreach angles",
        priority=7
    )
    print(f"    ✓ Campaign prep task: {task_id}")
    
    await asyncio.sleep(1)
    
    result = swarm.get_results(task_id)
    print(f"\n[2] Campaign ready:")
    print(f"    Status: {result['status']}")
    
    await swarm.shutdown()


# ============================================================================
# MAIN RUNNER
# ============================================================================


async def run_all_examples():
    """Run all example demonstrations."""
    print("\n" + "="*80)
    print("UNIVERSE SWARM PATTERNS - PRACTICAL EXAMPLES")
    print("="*80)
    print("Running 10 real-world examples of swarm pattern usage...\n")
    
    examples = [
        ("Research Swarm: Competitive Analysis", example_research_competitors),
        ("Research Swarm: Trend Analysis", example_research_trends),
        ("Development Swarm: Feature Development", example_develop_feature),
        ("Development Swarm: Code Review", example_code_review),
        ("Operations Swarm: Incident Response", example_incident_response),
        ("Operations Swarm: Performance Optimization", example_performance_optimization),
        ("Content Swarm: Blog Post Creation", example_create_blog_post),
        ("Content Swarm: Documentation", example_create_documentation),
        ("Sales Swarm: Lead Generation", example_lead_generation),
        ("Sales Swarm: Campaign Preparation", example_campaign_preparation),
    ]
    
    for i, (name, example_func) in enumerate(examples, 1):
        print(f"\nRunning Example {i}/10: {name}")
        try:
            await example_func()
            print(f"✓ Example {i} completed successfully")
        except Exception as e:
            print(f"✗ Example {i} failed: {e}")
    
    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETED")
    print("="*80)
    print("\nYou can now:")
    print("1. Pick a swarm pattern that matches your use case")
    print("2. Use the example as a template for your own tasks")
    print("3. Customize agent count, specializations, and tools")
    print("4. Deploy to production")


if __name__ == "__main__":
    asyncio.run(run_all_examples())
