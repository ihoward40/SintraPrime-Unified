"""
Specialized Agent Types for UniVerse Swarm Ecosystem.

Implements 6 core agent types with distinct capabilities:
- AnalystAgent: Research, analysis, pattern identification
- ExecutorAgent: Code execution, API calls, deployments
- LearnerAgent: Skill generation from examples
- CoordinatorAgent: Task delegation, negotiation
- VisionAgent: Image/video processing, UI understanding
- GuardAgent: Security, validation, compliance
"""

import asyncio
import json
import uuid
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DEFINITIONS
# ============================================================================


class InputSchema:
    """Defines input requirements for each agent type."""

    ANALYST = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Research query"},
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Data sources to analyze",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["summary", "pattern", "trend", "comparison"],
                "description": "Type of analysis to perform",
            },
            "depth": {
                "type": "string",
                "enum": ["shallow", "medium", "deep"],
                "description": "Analysis depth level",
            },
        },
        "required": ["query", "analysis_type"],
    }

    EXECUTOR = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to execute"},
            "language": {
                "type": "string",
                "enum": ["python", "bash", "javascript", "sql"],
                "description": "Programming language",
            },
            "environment": {
                "type": "object",
                "description": "Execution environment variables",
            },
            "timeout": {"type": "integer", "description": "Execution timeout in seconds"},
        },
        "required": ["code", "language"],
    }

    LEARNER = {
        "type": "object",
        "properties": {
            "task_examples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "output": {"type": "string"},
                        "context": {"type": "string"},
                    },
                },
                "description": "Examples to learn from",
            },
            "skill_category": {
                "type": "string",
                "description": "Category of skill to generate",
            },
            "generalization_level": {
                "type": "string",
                "enum": ["specific", "general", "abstract"],
                "description": "How generalizable the skill should be",
            },
        },
        "required": ["task_examples", "skill_category"],
    }

    COORDINATOR = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "type": {"type": "string"},
                        "priority": {"type": "integer"},
                        "dependencies": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "description": "Tasks to coordinate",
            },
            "available_agents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "capabilities": {"type": "array", "items": {"type": "string"}},
                        "capacity": {"type": "number"},
                    },
                },
                "description": "Available agents for allocation",
            },
            "optimization_goal": {
                "type": "string",
                "enum": ["speed", "quality", "cost", "balanced"],
                "description": "Optimization target",
            },
        },
        "required": ["tasks", "available_agents"],
    }

    VISION = {
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Path to image/video"},
            "analysis_type": {
                "type": "string",
                "enum": ["object_detection", "ocr", "scene_understanding", "diagram_parsing"],
                "description": "Type of visual analysis",
            },
            "focus_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific areas to focus on",
            },
        },
        "required": ["image_path", "analysis_type"],
    }

    GUARD = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target to validate"},
            "check_type": {
                "type": "string",
                "enum": ["signature", "compliance", "audit", "permission"],
                "description": "Type of security check",
            },
            "policy": {"type": "object", "description": "Security policy to apply"},
            "severity_level": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Severity level for violations",
            },
        },
        "required": ["target", "check_type"],
    }


class OutputSchema:
    """Defines output format for each agent type."""

    ANALYST = {
        "type": "object",
        "properties": {
            "analysis_type": {"type": "string"},
            "findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key findings",
            },
            "patterns": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Identified patterns",
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recommendations",
            },
            "confidence": {"type": "number"},
            "sources_used": {"type": "array", "items": {"type": "string"}},
        },
    }

    EXECUTOR = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["success", "failure", "timeout"],
            },
            "output": {"type": "string", "description": "Execution output"},
            "error": {"type": "string", "description": "Error message if failed"},
            "execution_time_ms": {"type": "integer"},
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Created artifacts",
            },
        },
    }

    LEARNER = {
        "type": "object",
        "properties": {
            "skill_id": {"type": "string"},
            "skill_name": {"type": "string"},
            "skill_description": {"type": "string"},
            "pattern": {"type": "object", "description": "Learned pattern"},
            "applicability": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Applicable use cases",
            },
            "confidence": {"type": "number"},
            "documentation": {"type": "string"},
        },
    }

    COORDINATOR = {
        "type": "object",
        "properties": {
            "task_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "assigned_agent": {"type": "string"},
                        "sequence": {"type": "integer"},
                        "estimated_duration_ms": {"type": "integer"},
                    },
                },
            },
            "resource_allocation": {
                "type": "object",
                "description": "Resource distribution",
            },
            "estimated_total_time_ms": {"type": "integer"},
            "risk_assessment": {"type": "string"},
            "contingency_plans": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }

    VISION = {
        "type": "object",
        "properties": {
            "analysis_type": {"type": "string"},
            "objects_detected": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "object": {"type": "string"},
                        "confidence": {"type": "number"},
                        "location": {"type": "object"},
                    },
                },
            },
            "text_extracted": {"type": "string"},
            "scene_description": {"type": "string"},
            "insights": {
                "type": "array",
                "items": {"type": "string"},
            },
            "ui_elements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "element_type": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
        },
    }

    GUARD = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["approved", "rejected", "review_needed"]},
            "check_type": {"type": "string"},
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "violation": {"type": "string"},
                        "severity": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                },
            },
            "risk_score": {"type": "number"},
            "audit_trail": {
                "type": "array",
                "items": {"type": "string"},
            },
            "approval_required": {"type": "boolean"},
        },
    }


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================


class PromptTemplates:
    """Claude integration prompts for each agent type."""

    ANALYST = """You are an AnalystAgent specializing in research and pattern identification.

Your task: {task}
Query: {query}
Analysis Type: {analysis_type}
Depth: {depth}

Instructions:
1. Research the query thoroughly across available sources
2. Identify key findings and patterns
3. Provide actionable recommendations
4. Rate confidence level (0-1)
5. Document all sources used

Format your response as JSON with: findings, patterns, recommendations, confidence, sources_used"""

    EXECUTOR = """You are an ExecutorAgent tasked with code execution and deployment.

Task: {task}
Code Language: {language}
Timeout: {timeout}s

Security Note: Only execute trusted code in isolated environments.

Instructions:
1. Parse the code carefully
2. Set up execution environment
3. Execute with timeout protection
4. Capture output and errors
5. Report execution metrics

Return JSON with: status, output, error (if any), execution_time_ms, artifacts"""

    LEARNER = """You are a LearnerAgent that generates reusable skills from examples.

Task: {task}
Skill Category: {skill_category}
Generalization Level: {generalization_level}

Examples Provided: {example_count}

Instructions:
1. Analyze the provided examples carefully
2. Extract the underlying pattern or algorithm
3. Generalize to broader applicability
4. Create documentation and usage guide
5. Identify edge cases and limitations

Return JSON with: skill_id, skill_name, skill_description, pattern, applicability, confidence, documentation"""

    COORDINATOR = """You are a CoordinatorAgent managing task delegation and resource allocation.

Tasks to Coordinate: {task_count}
Available Agents: {agent_count}
Optimization Goal: {optimization_goal}

Instructions:
1. Analyze task dependencies and priorities
2. Match tasks to agent capabilities
3. Create execution sequence
4. Allocate resources optimally
5. Identify risks and contingencies

Return JSON with: task_plan, resource_allocation, estimated_total_time_ms, risk_assessment, contingency_plans"""

    VISION = """You are a VisionAgent specializing in image and video analysis.

Task: {task}
Analysis Type: {analysis_type}
Image/Video Path: {media_path}

Instructions:
1. Load and examine the visual media
2. Perform requested analysis type
3. Extract text if present (OCR)
4. Identify objects and scene context
5. For UI: identify interactive elements and layout

Return JSON with: analysis_type, objects_detected, text_extracted, scene_description, insights, ui_elements"""

    GUARD = """You are a GuardAgent ensuring security, compliance, and validation.

Task: {task}
Target: {target}
Check Type: {check_type}
Severity Level: {severity_level}

Instructions:
1. Verify authenticity and integrity
2. Check against security policy
3. Identify violations and risks
4. Generate audit trail
5. Provide recommendations

Return JSON with: status, check_type, violations, risk_score, audit_trail, approval_required"""


# ============================================================================
# AGENT IMPLEMENTATIONS
# ============================================================================


class AnalystAgent(BaseAgent):
    """
    AnalystAgent: Research, analysis, and pattern identification.

    Specializes in:
    - Research and data gathering
    - Pattern recognition
    - Trend analysis
    - Report generation
    - Recommendation synthesis
    """

    def __init__(
        self,
        name: str = "Analyst",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "analyst", specialization, model)
        self.input_schema = InputSchema.ANALYST
        self.output_schema = OutputSchema.ANALYST
        self.analysis_history: List[Dict[str, Any]] = []

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute analysis task."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            # Parse command as JSON for structured input
            task_input = json.loads(command)

            prompt = PromptTemplates.ANALYST.format(
                task=task_id,
                query=task_input.get("query", ""),
                analysis_type=task_input.get("analysis_type", "summary"),
                depth=task_input.get("depth", "medium"),
                example_count=len(task_input.get("sources", [])),
            )

            # Simulate analysis execution
            analysis_result = await self._perform_analysis(task_input)

            # Store in history
            self.analysis_history.append(
                {
                    "task_id": task_id,
                    "input": task_input,
                    "result": analysis_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": analysis_result,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _perform_analysis(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual analysis."""
        analysis_type = task_input.get("analysis_type", "summary")

        # Simulate different analysis types
        if analysis_type == "summary":
            findings = [
                "Data point 1",
                "Data point 2",
                "Data point 3",
            ]
            patterns = [
                {"name": "pattern_1", "frequency": 0.8},
                {"name": "pattern_2", "frequency": 0.6},
            ]
        elif analysis_type == "pattern":
            findings = ["Pattern A identified", "Pattern B identified"]
            patterns = [
                {"name": "recurring_pattern", "strength": 0.85},
                {"name": "seasonal_pattern", "period": "quarterly"},
            ]
        elif analysis_type == "trend":
            findings = ["Upward trend detected", "Acceleration observed"]
            patterns = [
                {"name": "trend", "direction": "up", "rate": 0.15},
            ]
        else:  # comparison
            findings = ["Item A outperforms Item B", "Key differences identified"]
            patterns = [
                {"name": "performance_gap", "magnitude": 0.25},
            ]

        return {
            "analysis_type": analysis_type,
            "findings": findings,
            "patterns": patterns,
            "recommendations": [
                f"Action based on {findings[0]}",
                f"Action based on {findings[1]}",
            ],
            "confidence": 0.87,
            "sources_used": task_input.get("sources", []),
        }

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Learn patterns from analysis results."""
        try:
            # Extract patterns that could become reusable skills
            patterns = result.get("patterns", [])

            if patterns:
                skill_id = f"skill_{task_id[:8]}"
                skill_def = {
                    "type": "analysis_pattern",
                    "patterns": patterns,
                    "source_task": task_id,
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id

            return None
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collaborate with other agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "received",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "share_analysis":
            response["analysis_history"] = self.analysis_history[-3:]  # Last 3 analyses

        return response


class ExecutorAgent(BaseAgent):
    """
    ExecutorAgent: Code execution, API calls, deployments.

    Specializes in:
    - Python, bash, JavaScript execution
    - API calls and integrations
    - Deployment and provisioning
    - System operations
    - Database operations
    """

    def __init__(
        self,
        name: str = "Executor",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "executor", specialization, model)
        self.input_schema = InputSchema.EXECUTOR
        self.output_schema = OutputSchema.EXECUTOR
        self.execution_log: List[Dict[str, Any]] = []

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute code or command."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            task_input = json.loads(command)
            language = task_input.get("language", "python")
            code = task_input.get("code", "")
            timeout = task_input.get("timeout", 30)

            start_time = datetime.now()

            # Execute based on language
            output, error, artifacts = await self._execute_code(
                code, language, timeout
            )

            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            result = {
                "status": "success" if not error else "failure",
                "output": output,
                "error": error,
                "execution_time_ms": execution_time_ms,
                "artifacts": artifacts,
            }

            self.execution_log.append(
                {
                    "task_id": task_id,
                    "language": language,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Execution failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _execute_code(
        self, code: str, language: str, timeout: int
    ) -> Tuple[str, str, List[str]]:
        """Execute code in isolated environment."""
        # Simulate execution with safety checks
        if language == "python":
            # Check for dangerous patterns
            dangerous_patterns = ["__import__", "eval", "exec", "os.system"]
            if any(pattern in code for pattern in dangerous_patterns):
                return "", "Security: Dangerous pattern detected", []

            # Simulate Python execution
            output = f"Python execution result for {len(code)} chars of code"
            return output, "", ["output.txt"]

        elif language == "bash":
            # Simulate bash execution
            output = f"Command executed: {code[:50]}"
            return output, "", []

        elif language == "javascript":
            # Simulate JavaScript execution
            output = f"JavaScript result from {len(code)} chars"
            return output, "", ["result.json"]

        elif language == "sql":
            # Simulate SQL execution
            output = "Query executed: 42 rows affected"
            return output, "", ["query_result.csv"]

        return "", "Unknown language", []

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Learn executable patterns from successful executions."""
        try:
            if result.get("status") == "success":
                skill_id = f"exec_skill_{task_id[:8]}"
                skill_def = {
                    "type": "executable_pattern",
                    "execution_log_index": len(self.execution_log) - 1,
                    "success": True,
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id

            return None
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collaborate with other agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "received",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "share_capabilities":
            response["capabilities"] = [
                "python_execution",
                "bash_execution",
                "api_calls",
                "database_ops",
            ]

        return response


class LearnerAgent(BaseAgent):
    """
    LearnerAgent: Generates new skills from task examples.

    Specializes in:
    - Pattern extraction from examples
    - Skill generalization
    - Knowledge synthesis
    - Documentation generation
    - Best practice identification
    """

    def __init__(
        self,
        name: str = "Learner",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "learner", specialization, model)
        self.input_schema = InputSchema.LEARNER
        self.output_schema = OutputSchema.LEARNER
        self.generated_skills: List[Dict[str, Any]] = []

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute skill generation from examples."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            task_input = json.loads(command)

            prompt = PromptTemplates.LEARNER.format(
                task=task_id,
                skill_category=task_input.get("skill_category", ""),
                generalization_level=task_input.get("generalization_level", "general"),
                example_count=len(task_input.get("task_examples", [])),
            )

            # Generate skill from examples
            skill = await self._generate_skill(task_input)

            self.generated_skills.append(skill)
            self.add_skill(skill["skill_id"], skill)

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": skill,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Skill generation failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _generate_skill(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new skill from examples."""
        examples = task_input.get("task_examples", [])
        category = task_input.get("skill_category", "general")
        gen_level = task_input.get("generalization_level", "general")

        # Analyze examples to extract pattern
        if examples:
            # Extract common patterns from inputs/outputs
            pattern_rules = []
            for example in examples:
                # Simple pattern extraction simulation
                pattern_rules.append(
                    {
                        "input_length": len(example.get("input", "")),
                        "output_length": len(example.get("output", "")),
                    }
                )

            skill_id = f"skill_{uuid.uuid4().hex[:8]}"
            return {
                "skill_id": skill_id,
                "skill_name": f"{category.title()} Skill",
                "skill_description": f"Learned skill for {category} tasks at {gen_level} level",
                "pattern": {
                    "type": category,
                    "rules": pattern_rules,
                    "generalization": gen_level,
                },
                "applicability": [f"{category}_task_1", f"{category}_task_2"],
                "confidence": 0.82,
                "documentation": f"Skill generated from {len(examples)} examples",
                "created_at": datetime.now().isoformat(),
            }

        return {
            "skill_id": None,
            "error": "No examples provided",
        }

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Meta-learning: learn about learning from this task."""
        try:
            if result.get("status") == "success":
                skill_id = f"meta_skill_{task_id[:8]}"
                skill_def = {
                    "type": "meta_learning",
                    "learned_skill_count": len(self.generated_skills),
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id
            return None
        except Exception as e:
            logger.error(f"Meta-learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Share generated skills with other agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "received",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "share_skills":
            response["available_skills"] = [
                skill["skill_id"] for skill in self.generated_skills
            ]
            response["skill_count"] = len(self.generated_skills)

        return response


class CoordinatorAgent(BaseAgent):
    """
    CoordinatorAgent: Task delegation and resource management.

    Specializes in:
    - Task dependency analysis
    - Agent capability matching
    - Resource allocation
    - Execution planning
    - Load balancing
    - Risk assessment
    """

    def __init__(
        self,
        name: str = "Coordinator",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "coordinator", specialization, model)
        self.input_schema = InputSchema.COORDINATOR
        self.output_schema = OutputSchema.COORDINATOR
        self.task_plans: List[Dict[str, Any]] = []

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Create task coordination plan."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            task_input = json.loads(command)

            prompt = PromptTemplates.COORDINATOR.format(
                task_count=len(task_input.get("tasks", [])),
                agent_count=len(task_input.get("available_agents", [])),
                optimization_goal=task_input.get("optimization_goal", "balanced"),
            )

            # Generate coordination plan
            plan = await self._create_task_plan(task_input)

            self.task_plans.append(
                {
                    "task_id": task_id,
                    "plan": plan,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": plan,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Coordination failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _create_task_plan(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Create optimized task execution plan."""
        tasks = task_input.get("tasks", [])
        agents = task_input.get("available_agents", [])
        optimization = task_input.get("optimization_goal", "balanced")

        # Create task plan with agent assignments
        task_plan = []
        for i, task in enumerate(tasks):
            # Simple round-robin assignment
            agent = agents[i % len(agents)] if agents else {}

            task_plan.append(
                {
                    "task_id": task.get("task_id"),
                    "assigned_agent": agent.get("agent_id", f"agent_{i}"),
                    "sequence": i + 1,
                    "estimated_duration_ms": 5000 + (i * 1000),
                }
            )

        # Resource allocation
        resource_allocation = {
            "cpu_cores": len(agents),
            "memory_gb": len(agents) * 2,
            "agents_needed": len(agents),
        }

        # Risk assessment
        risks = []
        if len(tasks) > len(agents):
            risks.append("More tasks than available agents - sequential execution needed")

        return {
            "task_plan": task_plan,
            "resource_allocation": resource_allocation,
            "estimated_total_time_ms": sum(
                t["estimated_duration_ms"] for t in task_plan
            ),
            "risk_assessment": " | ".join(risks) if risks else "Low risk",
            "contingency_plans": [
                "Scale up agent pool if needed",
                "Implement fallback agents",
            ],
        }

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Learn coordination patterns from successful plans."""
        try:
            if result.get("status") == "success":
                skill_id = f"coord_skill_{task_id[:8]}"
                skill_def = {
                    "type": "coordination_pattern",
                    "task_count": len(result.get("task_plan", [])),
                    "optimization_goal": result.get("optimization_goal", "balanced"),
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id
            return None
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Broadcast coordination plan to agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "plan_shared",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "get_task_plan":
            if self.task_plans:
                response["latest_plan"] = self.task_plans[-1]["plan"]

        return response


class VisionAgent(BaseAgent):
    """
    VisionAgent: Image and video processing, UI understanding.

    Specializes in:
    - Object detection
    - Optical character recognition (OCR)
    - Scene understanding
    - Diagram parsing
    - UI element identification
    - Visual relationship analysis
    """

    def __init__(
        self,
        name: str = "Vision",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "vision", specialization, model)
        self.input_schema = InputSchema.VISION
        self.output_schema = OutputSchema.VISION
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute visual analysis task."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            task_input = json.loads(command)
            image_path = task_input.get("image_path", "")
            analysis_type = task_input.get("analysis_type", "object_detection")

            # Check cache
            if image_path in self.analysis_cache:
                cached_result = self.analysis_cache[image_path]
                self.set_status("idle")
                return {
                    "status": "success",
                    "task_id": task_id,
                    "result": cached_result,
                    "from_cache": True,
                }

            prompt = PromptTemplates.VISION.format(
                task=task_id,
                analysis_type=analysis_type,
                media_path=image_path,
            )

            # Perform visual analysis
            result = await self._analyze_visual_content(task_input)

            # Cache result
            self.analysis_cache[image_path] = result

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Vision analysis failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _analyze_visual_content(
        self, task_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze visual content based on requested analysis type."""
        analysis_type = task_input.get("analysis_type", "object_detection")

        if analysis_type == "object_detection":
            objects = [
                {"object": "person", "confidence": 0.95, "location": {"x": 100, "y": 50}},
                {"object": "laptop", "confidence": 0.88, "location": {"x": 200, "y": 150}},
                {
                    "object": "desk",
                    "confidence": 0.92,
                    "location": {"x": 150, "y": 250},
                },
            ]
            return {
                "analysis_type": "object_detection",
                "objects_detected": objects,
                "text_extracted": "",
                "scene_description": "Office workspace with person at laptop",
                "insights": [
                    "Person appears to be working",
                    "Professional environment",
                ],
                "ui_elements": [],
            }

        elif analysis_type == "ocr":
            return {
                "analysis_type": "ocr",
                "objects_detected": [],
                "text_extracted": "Sample text extracted from image",
                "scene_description": "Document with text content",
                "insights": ["Text is readable", "High contrast"],
                "ui_elements": [],
            }

        elif analysis_type == "scene_understanding":
            return {
                "analysis_type": "scene_understanding",
                "objects_detected": [
                    {"object": "outdoor", "confidence": 0.9, "location": {}}
                ],
                "text_extracted": "",
                "scene_description": "Outdoor urban environment with multiple buildings",
                "insights": [
                    "Daytime scene",
                    "Multiple architectural styles",
                    "Pedestrian activity present",
                ],
                "ui_elements": [],
            }

        else:  # diagram_parsing
            return {
                "analysis_type": "diagram_parsing",
                "objects_detected": [
                    {"object": "flowchart_box", "confidence": 0.85, "location": {}},
                    {"object": "arrow", "confidence": 0.88, "location": {}},
                ],
                "text_extracted": "Process A -> Process B -> Process C",
                "scene_description": "Process flow diagram",
                "insights": [
                    "Sequential flow detected",
                    "3 main process stages",
                ],
                "ui_elements": [
                    {
                        "element_type": "box",
                        "description": "Process container",
                    },
                    {"element_type": "arrow", "description": "Flow connector"},
                ],
            }

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Learn visual patterns from analysis results."""
        try:
            if result.get("status") == "success":
                skill_id = f"vision_skill_{task_id[:8]}"
                skill_def = {
                    "type": "vision_pattern",
                    "objects_analyzed": len(result.get("objects_detected", [])),
                    "analysis_type": result.get("analysis_type"),
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id
            return None
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Share visual insights with other agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "received",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "share_analysis":
            response["cached_analyses"] = list(self.analysis_cache.keys())

        return response


class GuardAgent(BaseAgent):
    """
    GuardAgent: Security, validation, and compliance.

    Specializes in:
    - Signature verification
    - Compliance checking
    - Audit logging
    - Permission validation
    - Risk assessment
    - Security policy enforcement
    """

    def __init__(
        self,
        name: str = "Guard",
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        super().__init__(name, "guard", specialization, model)
        self.input_schema = InputSchema.GUARD
        self.output_schema = OutputSchema.GUARD
        self.audit_log: List[Dict[str, Any]] = []

    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute security/compliance check."""
        self.current_task_id = task_id
        self.set_status("executing")

        try:
            task_input = json.loads(command)
            target = task_input.get("target", "")
            check_type = task_input.get("check_type", "compliance")

            prompt = PromptTemplates.GUARD.format(
                task=task_id,
                target=target,
                check_type=check_type,
                severity_level=task_input.get("severity_level", "medium"),
            )

            # Perform security check
            result = await self._perform_security_check(task_input)

            # Log to audit trail
            self.audit_log.append(
                {
                    "task_id": task_id,
                    "check_type": check_type,
                    "target": target,
                    "status": result.get("status"),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.set_status("idle")
            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
            }

        except Exception as e:
            self.set_status("idle")
            logger.error(f"Security check failed: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }

    async def _perform_security_check(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security and compliance checks."""
        check_type = task_input.get("check_type", "compliance")
        target = task_input.get("target", "")
        severity = task_input.get("severity_level", "medium")

        violations = []
        approval_required = False

        # Simulate different check types
        if check_type == "signature":
            # Check if target has valid signature
            if "malware" in target.lower():
                violations.append(
                    {
                        "violation": "Malicious signature detected",
                        "severity": "critical",
                        "recommendation": "Quarantine immediately",
                    }
                )
                approval_required = True

        elif check_type == "compliance":
            # Check compliance with policies
            if "unencrypted" in target.lower():
                violations.append(
                    {
                        "violation": "Data not encrypted",
                        "severity": "high",
                        "recommendation": "Enable encryption",
                    }
                )

        elif check_type == "audit":
            # Audit log review
            violations.append(
                {
                    "violation": "Unusual access pattern",
                    "severity": "medium",
                    "recommendation": "Review access logs",
                }
            )

        elif check_type == "permission":
            # Permission validation
            if "admin" in target.lower() and severity == "critical":
                violations.append(
                    {
                        "violation": "Elevated privileges requested",
                        "severity": "high",
                        "recommendation": "Require approval for admin access",
                    }
                )
                approval_required = True

        status = "approved" if not violations else "review_needed"
        if violations and any(v["severity"] == "critical" for v in violations):
            status = "rejected"

        risk_score = len(violations) * 0.2  # Simple risk calculation

        return {
            "status": status,
            "check_type": check_type,
            "violations": violations,
            "risk_score": min(risk_score, 1.0),
            "audit_trail": [
                f"Check {check_type} performed on {target}",
                f"Violations found: {len(violations)}",
            ],
            "approval_required": approval_required,
        }

    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """Learn security patterns from checks performed."""
        try:
            if result.get("status") in ["approved", "review_needed", "rejected"]:
                skill_id = f"guard_skill_{task_id[:8]}"
                skill_def = {
                    "type": "security_pattern",
                    "checks_performed": len(self.audit_log),
                    "created_at": datetime.now().isoformat(),
                }
                self.add_skill(skill_id, skill_def)
                return skill_id
            return None
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
            return None

    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Share security status with other agents."""
        response = {
            "from_agent": self.agent_id,
            "to_agent": other_agent.agent_id,
            "status": "received",
            "timestamp": datetime.now().isoformat(),
        }

        if message.get("request_type") == "share_security_status":
            response["audit_log_length"] = len(self.audit_log)
            response["last_check"] = (
                self.audit_log[-1] if self.audit_log else "No checks performed"
            )

        return response


# ============================================================================
# AGENT REGISTRY AND FACTORY
# ============================================================================


class AgentRegistry:
    """Registry for all agent types."""

    AGENT_TYPES = {
        "analyst": AnalystAgent,
        "executor": ExecutorAgent,
        "learner": LearnerAgent,
        "coordinator": CoordinatorAgent,
        "vision": VisionAgent,
        "guard": GuardAgent,
    }

    @classmethod
    def create_agent(
        cls,
        agent_type: str,
        name: str,
        specialization: Optional[str] = None,
    ) -> BaseAgent:
        """Factory method to create agents."""
        if agent_type not in cls.AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = cls.AGENT_TYPES[agent_type]
        return agent_class(name=name, specialization=specialization)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available agent types."""
        return list(cls.AGENT_TYPES.keys())

    @classmethod
    def get_agent_schema(cls, agent_type: str) -> Dict[str, Dict[str, Any]]:
        """Get input/output schemas for an agent type."""
        if agent_type not in cls.AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Map agent type to schema
        schema_map = {
            "analyst": (InputSchema.ANALYST, OutputSchema.ANALYST),
            "executor": (InputSchema.EXECUTOR, OutputSchema.EXECUTOR),
            "learner": (InputSchema.LEARNER, OutputSchema.LEARNER),
            "coordinator": (InputSchema.COORDINATOR, OutputSchema.COORDINATOR),
            "vision": (InputSchema.VISION, OutputSchema.VISION),
            "guard": (InputSchema.GUARD, OutputSchema.GUARD),
        }

        input_schema, output_schema = schema_map[agent_type]
        return {"input_schema": input_schema, "output_schema": output_schema}
