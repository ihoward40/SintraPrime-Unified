"""
Practical Examples for UniVerse Agent Types.

This file demonstrates common use cases for each agent type.
"""

import json
import asyncio
from typing import Dict, Any
from agent_types import AgentRegistry


# ============================================================================
# ANALYST AGENT EXAMPLES
# ============================================================================


async def example_analyst_market_research():
    """Analyst Agent: Market research and trend analysis."""
    print("\n" + "="*70)
    print("EXAMPLE: Analyst Agent - Market Research")
    print("="*70)
    
    analyst = AgentRegistry.create_agent("analyst", "MarketResearcher")
    
    task = {
        "query": "AI market growth trends 2024-2026",
        "analysis_type": "trend",
        "depth": "deep",
        "sources": [
            "market_reports",
            "analyst_notes",
            "industry_surveys",
            "patent_data"
        ]
    }
    
    result = await analyst.execute("market_001", json.dumps(task))
    
    if result["status"] == "success":
        analysis = result["result"]
        print(f"\n✓ Analysis completed")
        print(f"  Findings: {analysis['findings']}")
        print(f"  Patterns identified: {len(analysis['patterns'])}")
        print(f"  Confidence: {analysis['confidence']:.1%}")
        print(f"  Recommendations: {len(analysis['recommendations'])}")
        
        # Learn from this analysis
        skill = await analyst.learn("market_001", analysis)
        if skill:
            print(f"\n✓ Acquired skill: {skill}")


async def example_analyst_competitor_analysis():
    """Analyst Agent: Competitive analysis."""
    print("\n" + "="*70)
    print("EXAMPLE: Analyst Agent - Competitor Analysis")
    print("="*70)
    
    analyst = AgentRegistry.create_agent("analyst", "CompetitiveAnalyst")
    
    task = {
        "query": "Compare top 5 AI assistant platforms on features and pricing",
        "analysis_type": "comparison",
        "depth": "medium",
        "sources": ["product_sites", "pricing_pages", "feature_comparisons"]
    }
    
    result = await analyst.execute("comp_001", json.dumps(task))
    
    if result["status"] == "success":
        print(f"✓ Comparison analysis completed")
        print(f"  Findings: {result['result']['findings']}")


# ============================================================================
# EXECUTOR AGENT EXAMPLES
# ============================================================================


async def example_executor_python_script():
    """Executor Agent: Run Python code."""
    print("\n" + "="*70)
    print("EXAMPLE: Executor Agent - Python Execution")
    print("="*70)
    
    executor = AgentRegistry.create_agent("executor", "PythonRunner")
    
    code = """
import json
data = {'agents': 6, 'types': ['analyst', 'executor', 'learner', 'coordinator', 'vision', 'guard']}
print(json.dumps(data, indent=2))
"""
    
    task = {
        "code": code,
        "language": "python",
        "timeout": 30
    }
    
    result = await executor.execute("py_001", json.dumps(task))
    
    if result["status"] == "success":
        print(f"✓ Python code executed")
        print(f"  Output:\n{result['result']['output']}")
        print(f"  Execution time: {result['result']['execution_time_ms']}ms")


async def example_executor_bash_command():
    """Executor Agent: Run bash commands."""
    print("\n" + "="*70)
    print("EXAMPLE: Executor Agent - Bash Execution")
    print("="*70)
    
    executor = AgentRegistry.create_agent("executor", "BashRunner")
    
    task = {
        "code": "echo 'UniVerse Swarm Ecosystem' && echo 'Version 1.0'",
        "language": "bash",
        "timeout": 10
    }
    
    result = await executor.execute("bash_001", json.dumps(task))
    
    if result["status"] == "success":
        print(f"✓ Bash command executed")
        print(f"  Output: {result['result']['output']}")


async def example_executor_data_processing():
    """Executor Agent: Data processing pipeline."""
    print("\n" + "="*70)
    print("EXAMPLE: Executor Agent - Data Processing")
    print("="*70)
    
    executor = AgentRegistry.create_agent("executor", "DataProcessor")
    
    code = """
data = [
    {"name": "AnalystAgent", "role": "research"},
    {"name": "ExecutorAgent", "role": "execution"},
    {"name": "LearnerAgent", "role": "learning"}
]

# Process
result = [d for d in data if d['role'] in ['research', 'learning']]
print(f"Filtered {len(result)} items")
"""
    
    task = {
        "code": code,
        "language": "python",
        "timeout": 20
    }
    
    result = await executor.execute("data_001", json.dumps(task))
    
    if result["status"] == "success":
        print(f"✓ Data processing completed")
        print(f"  Output: {result['result']['output']}")


# ============================================================================
# LEARNER AGENT EXAMPLES
# ============================================================================


async def example_learner_text_transformation():
    """Learner Agent: Learn text transformation skill."""
    print("\n" + "="*70)
    print("EXAMPLE: Learner Agent - Text Transformation Skill")
    print("="*70)
    
    learner = AgentRegistry.create_agent("learner", "TextLearner")
    
    task = {
        "task_examples": [
            {
                "input": "hello world",
                "output": "HELLO WORLD",
                "context": "convert to uppercase"
            },
            {
                "input": "universe",
                "output": "UNIVERSE",
                "context": "convert to uppercase"
            },
            {
                "input": "swarm",
                "output": "SWARM",
                "context": "convert to uppercase"
            }
        ],
        "skill_category": "text_transformation",
        "generalization_level": "general"
    }
    
    result = await learner.execute("learn_001", json.dumps(task))
    
    if result["status"] == "success":
        skill = result["result"]
        print(f"✓ Learned new skill: {skill['skill_name']}")
        print(f"  Skill ID: {skill['skill_id']}")
        print(f"  Confidence: {skill['confidence']:.1%}")
        print(f"  Applicable to: {skill['applicability']}")
        print(f"  Pattern: {skill['pattern']}")


async def example_learner_data_extraction():
    """Learner Agent: Learn data extraction pattern."""
    print("\n" + "="*70)
    print("EXAMPLE: Learner Agent - Data Extraction Pattern")
    print("="*70)
    
    learner = AgentRegistry.create_agent("learner", "DataLearner")
    
    task = {
        "task_examples": [
            {
                "input": "<agent id='1' name='Analyst'/>",
                "output": "1, Analyst",
                "context": "extract XML attributes"
            },
            {
                "input": "<agent id='2' name='Executor'/>",
                "output": "2, Executor",
                "context": "extract XML attributes"
            }
        ],
        "skill_category": "data_extraction",
        "generalization_level": "abstract"
    }
    
    result = await learner.execute("learn_002", json.dumps(task))
    
    if result["status"] == "success":
        skill = result["result"]
        print(f"✓ Learned data extraction skill")
        print(f"  Pattern rules: {skill['pattern']}")


# ============================================================================
# COORDINATOR AGENT EXAMPLES
# ============================================================================


async def example_coordinator_simple_pipeline():
    """Coordinator Agent: Coordinate simple task pipeline."""
    print("\n" + "="*70)
    print("EXAMPLE: Coordinator Agent - Simple Pipeline")
    print("="*70)
    
    coordinator = AgentRegistry.create_agent("coordinator", "PipelineManager")
    
    task = {
        "tasks": [
            {
                "task_id": "analyze_data",
                "type": "analysis",
                "priority": 1,
                "dependencies": []
            },
            {
                "task_id": "process_results",
                "type": "processing",
                "priority": 2,
                "dependencies": ["analyze_data"]
            },
            {
                "task_id": "validate_output",
                "type": "validation",
                "priority": 2,
                "dependencies": ["process_results"]
            }
        ],
        "available_agents": [
            {
                "agent_id": "analyst_1",
                "capabilities": ["analysis"],
                "capacity": 1.0
            },
            {
                "agent_id": "executor_1",
                "capabilities": ["processing"],
                "capacity": 1.0
            },
            {
                "agent_id": "guard_1",
                "capabilities": ["validation"],
                "capacity": 1.0
            }
        ],
        "optimization_goal": "speed"
    }
    
    result = await coordinator.execute("coord_001", json.dumps(task))
    
    if result["status"] == "success":
        plan = result["result"]
        print(f"✓ Coordination plan created")
        print(f"  Total tasks: {len(plan['task_plan'])}")
        print(f"  Estimated duration: {plan['estimated_total_time_ms']}ms")
        print(f"  Risk assessment: {plan['risk_assessment']}")
        print(f"\n  Execution sequence:")
        for step in plan["task_plan"]:
            print(f"    {step['sequence']}. {step['task_id']:20} → {step['assigned_agent']}")


async def example_coordinator_parallel_tasks():
    """Coordinator Agent: Parallel task execution."""
    print("\n" + "="*70)
    print("EXAMPLE: Coordinator Agent - Parallel Tasks")
    print("="*70)
    
    coordinator = AgentRegistry.create_agent("coordinator", "ParallelManager")
    
    task = {
        "tasks": [
            {"task_id": f"task_{i}", "type": "analysis", "priority": 1, "dependencies": []}
            for i in range(5)
        ],
        "available_agents": [
            {
                "agent_id": f"agent_{i}",
                "capabilities": ["analysis"],
                "capacity": 1.0
            }
            for i in range(3)
        ],
        "optimization_goal": "balanced"
    }
    
    result = await coordinator.execute("coord_002", json.dumps(task))
    
    if result["status"] == "success":
        plan = result["result"]
        print(f"✓ Parallel plan created for {len(plan['task_plan'])} tasks")
        print(f"  Agents needed: {plan['resource_allocation']['agents_needed']}")


# ============================================================================
# VISION AGENT EXAMPLES
# ============================================================================


async def example_vision_object_detection():
    """Vision Agent: Detect objects in image."""
    print("\n" + "="*70)
    print("EXAMPLE: Vision Agent - Object Detection")
    print("="*70)
    
    vision = AgentRegistry.create_agent("vision", "ObjectDetector")
    
    task = {
        "image_path": "/path/to/workspace.jpg",
        "analysis_type": "object_detection",
        "focus_areas": ["furniture", "electronics", "people"]
    }
    
    result = await vision.execute("vision_001", json.dumps(task))
    
    if result["status"] == "success":
        analysis = result["result"]
        print(f"✓ Object detection completed")
        print(f"  Scene: {analysis['scene_description']}")
        print(f"  Objects detected: {len(analysis['objects_detected'])}")
        for obj in analysis['objects_detected']:
            print(f"    - {obj['object']:15} (confidence: {obj['confidence']:.2f})")
        print(f"  Insights: {analysis['insights']}")


async def example_vision_ui_analysis():
    """Vision Agent: Analyze UI interface."""
    print("\n" + "="*70)
    print("EXAMPLE: Vision Agent - UI Analysis")
    print("="*70)
    
    vision = AgentRegistry.create_agent("vision", "UIAnalyzer")
    
    task = {
        "image_path": "/path/to/app_screenshot.png",
        "analysis_type": "object_detection",
        "focus_areas": ["buttons", "text", "menus", "forms"]
    }
    
    result = await vision.execute("vision_002", json.dumps(task))
    
    if result["status"] == "success":
        analysis = result["result"]
        print(f"✓ UI analysis completed")
        if analysis['ui_elements']:
            print(f"  UI Elements found:")
            for elem in analysis['ui_elements']:
                print(f"    - {elem['element_type']}: {elem['description']}")


async def example_vision_text_extraction():
    """Vision Agent: Extract text from image."""
    print("\n" + "="*70)
    print("EXAMPLE: Vision Agent - Text Extraction (OCR)")
    print("="*70)
    
    vision = AgentRegistry.create_agent("vision", "OCRReader")
    
    task = {
        "image_path": "/path/to/document.png",
        "analysis_type": "ocr",
        "focus_areas": ["headers", "body_text", "signatures"]
    }
    
    result = await vision.execute("vision_003", json.dumps(task))
    
    if result["status"] == "success":
        analysis = result["result"]
        print(f"✓ Text extraction completed")
        print(f"  Text: {analysis['text_extracted'][:100]}...")


# ============================================================================
# GUARD AGENT EXAMPLES
# ============================================================================


async def example_guard_signature_verification():
    """Guard Agent: Verify code signature."""
    print("\n" + "="*70)
    print("EXAMPLE: Guard Agent - Signature Verification")
    print("="*70)
    
    guard = AgentRegistry.create_agent("guard", "SignatureVerifier")
    
    task = {
        "target": "package_v1.0.0.tar.gz",
        "check_type": "signature",
        "severity_level": "high",
        "policy": {
            "require_signature": True,
            "trusted_signers": ["build_system", "release_manager"]
        }
    }
    
    result = await guard.execute("guard_001", json.dumps(task))
    
    if result["status"] == "success":
        check = result["result"]
        print(f"✓ Signature check completed")
        print(f"  Status: {check['status'].upper()}")
        print(f"  Risk Score: {check['risk_score']:.2f}")
        if check['violations']:
            print(f"  Violations: {len(check['violations'])}")
            for v in check['violations']:
                print(f"    - {v['violation']} ({v['severity']})")
        print(f"  Approval required: {check['approval_required']}")


async def example_guard_compliance_check():
    """Guard Agent: Check compliance with policies."""
    print("\n" + "="*70)
    print("EXAMPLE: Guard Agent - Compliance Check")
    print("="*70)
    
    guard = AgentRegistry.create_agent("guard", "ComplianceChecker")
    
    task = {
        "target": "database_connection",
        "check_type": "compliance",
        "severity_level": "critical",
        "policy": {
            "encryption_required": True,
            "tls_version_min": "1.2",
            "authentication_required": True
        }
    }
    
    result = await guard.execute("guard_002", json.dumps(task))
    
    if result["status"] == "success":
        check = result["result"]
        print(f"✓ Compliance check completed")
        print(f"  Status: {check['status'].upper()}")
        print(f"  Audit trail:")
        for log in check['audit_trail']:
            print(f"    - {log}")


async def example_guard_permission_validation():
    """Guard Agent: Validate permissions."""
    print("\n" + "="*70)
    print("EXAMPLE: Guard Agent - Permission Validation")
    print("="*70)
    
    guard = AgentRegistry.create_agent("guard", "PermissionValidator")
    
    task = {
        "target": "user_id_12345",
        "check_type": "permission",
        "severity_level": "high",
        "policy": {
            "admin_access_requires_approval": True,
            "max_concurrent_sessions": 3,
            "password_expiry_days": 90
        }
    }
    
    result = await guard.execute("guard_003", json.dumps(task))
    
    if result["status"] == "success":
        check = result["result"]
        print(f"✓ Permission check completed")
        print(f"  Status: {check['status'].upper()}")
        print(f"  Risk Score: {check['risk_score']:.2f}")
        print(f"  Approval required: {check['approval_required']}")


# ============================================================================
# AGENT COLLABORATION EXAMPLES
# ============================================================================


async def example_collaboration_analyst_to_executor():
    """Example: Analyst requests executor capabilities."""
    print("\n" + "="*70)
    print("EXAMPLE: Collaboration - Analyst → Executor")
    print("="*70)
    
    analyst = AgentRegistry.create_agent("analyst", "Researcher")
    executor = AgentRegistry.create_agent("executor", "Coder")
    
    # Analyst requests executor capabilities
    message = {
        "request_type": "share_capabilities",
        "context": "Need to execute analysis code"
    }
    
    response = await analyst.collaborate(executor, message)
    
    print(f"✓ Collaboration message sent")
    print(f"  From: Analyst ({response['from_agent'][:8]}...)")
    print(f"  To: Executor ({response['to_agent'][:8]}...)")
    print(f"  Status: {response['status']}")
    print(f"  Timestamp: {response['timestamp']}")


async def example_collaboration_multi_agent():
    """Example: Multi-agent collaboration workflow."""
    print("\n" + "="*70)
    print("EXAMPLE: Collaboration - Multi-Agent Workflow")
    print("="*70)
    
    analyst = AgentRegistry.create_agent("analyst", "DataAnalyst")
    executor = AgentRegistry.create_agent("executor", "Processor")
    vision = AgentRegistry.create_agent("vision", "Validator")
    guard = AgentRegistry.create_agent("guard", "Security")
    
    print(f"✓ Created multi-agent team:")
    print(f"  1. Analyst {analyst.agent_id[:8]}...")
    print(f"  2. Executor {executor.agent_id[:8]}...")
    print(f"  3. Vision {vision.agent_id[:8]}...")
    print(f"  4. Guard {guard.agent_id[:8]}...")
    
    # Simulate workflow
    print(f"\n  Workflow:")
    print(f"    1. Analyst analyzes data")
    msg1 = {"request_type": "share_analysis"}
    resp1 = await analyst.collaborate(executor, msg1)
    print(f"       → Executor receives analysis ({resp1['status']})")
    
    print(f"    2. Executor processes results")
    msg2 = {"request_type": "process_request"}
    resp2 = await executor.collaborate(vision, msg2)
    print(f"       → Vision validates output ({resp2['status']})")
    
    print(f"    3. Vision checks result quality")
    msg3 = {"request_type": "validate"}
    resp3 = await vision.collaborate(guard, msg3)
    print(f"       → Guard approves workflow ({resp3['status']})")


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================


async def run_all_examples():
    """Run all examples."""
    
    print("\n" + "="*70)
    print("UNIVERSE AGENT TYPES - USAGE EXAMPLES")
    print("="*70)
    
    # Analyst examples
    await example_analyst_market_research()
    await example_analyst_competitor_analysis()
    
    # Executor examples
    await example_executor_python_script()
    await example_executor_bash_command()
    await example_executor_data_processing()
    
    # Learner examples
    await example_learner_text_transformation()
    await example_learner_data_extraction()
    
    # Coordinator examples
    await example_coordinator_simple_pipeline()
    await example_coordinator_parallel_tasks()
    
    # Vision examples
    await example_vision_object_detection()
    await example_vision_ui_analysis()
    await example_vision_text_extraction()
    
    # Guard examples
    await example_guard_signature_verification()
    await example_guard_compliance_check()
    await example_guard_permission_validation()
    
    # Collaboration examples
    await example_collaboration_analyst_to_executor()
    await example_collaboration_multi_agent()
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_examples())
