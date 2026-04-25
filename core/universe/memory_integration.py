"""
Integration of Memory System with Execution Infrastructure

This module shows how the memory system integrates with the existing
execution_trace, audit_log, and task_registry to enable collective learning.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from memory_system import MemorySystem


class ExecutionAwareMemory:
    """Memory system that integrates with execution infrastructure"""
    
    def __init__(self, db_path: str = "/agent/home/universe/memory.db"):
        self.memory = MemorySystem(db_path)
        self.main_db_path = "/agent/home/universe/universe.db"  # Main execution DB
    
    def record_successful_task(self, task_id: str, execution_id: str,
                              agent_id: str, description: str,
                              techniques_used: List[str] = None,
                              metrics: Dict = None):
        """Record a successful task execution as knowledge"""
        try:
            # Get task details from main database
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT result, completed_at FROM task_registry 
                WHERE task_id = ?
            """, (task_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            task_result, completed_at = result
            
            # Store knowledge about successful execution
            knowledge_content = f"""
Task: {description}
Techniques: {', '.join(techniques_used or [])}
Agent: {agent_id}
Result: {task_result}
Metrics: {metrics or {}}
Completed: {completed_at}
""".strip()
            
            knowledge_id = self.memory.store_knowledge(
                content=knowledge_content,
                knowledge_type="successful_execution",
                source_agent=agent_id,
                metadata={
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "techniques": techniques_used or [],
                    "metrics": metrics or {},
                    "completion_time": completed_at
                }
            )
            
            return knowledge_id
        except Exception as e:
            print(f"Error recording successful task: {e}")
            return None
    
    def record_failed_task_and_trigger_learning(self, task_id: str,
                                               execution_id: str,
                                               agent_id: str,
                                               description: str,
                                               error_message: str,
                                               mentor_agent_id: str = None) -> str:
        """Record failed task and trigger learning session"""
        try:
            # Store the failure as knowledge for pattern recognition
            failure_knowledge = f"""
Failed Task: {description}
Agent: {agent_id}
Error: {error_message}
Execution: {execution_id}
""".strip()
            
            knowledge_id = self.memory.store_knowledge(
                content=failure_knowledge,
                knowledge_type="failure_pattern",
                source_agent=agent_id,
                metadata={
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "error": error_message
                }
            )
            
            # Trigger learning session
            session_id = self.memory.start_learning_session(
                agent_id=agent_id,
                trigger_type="task_failure",
                trigger_task_id=task_id,
                mentor_agent_id=mentor_agent_id
            )
            
            return session_id
        except Exception as e:
            print(f"Error recording failed task: {e}")
            return None
    
    def capture_agent_pattern(self, agent_id: str, pattern_name: str,
                            pattern_description: str,
                            success_rate: float,
                            execution_count: int):
        """Capture a pattern discovered by an agent for sharing"""
        knowledge_id = self.memory.store_knowledge(
            content=f"{pattern_name}: {pattern_description}",
            knowledge_type="execution_pattern",
            source_agent=agent_id,
            metadata={
                "pattern_name": pattern_name,
                "success_rate": success_rate,
                "execution_count": execution_count
            }
        )
        
        # Update knowledge with success metrics
        if knowledge_id:
            for _ in range(int(execution_count * success_rate)):
                self.memory.update_knowledge_usage(knowledge_id, success=True)
            for _ in range(int(execution_count * (1 - success_rate))):
                self.memory.update_knowledge_usage(knowledge_id, success=False)
        
        return knowledge_id
    
    def get_recommended_skills_for_task(self, task_description: str,
                                       agent_id: str,
                                       limit: int = 5) -> List[Dict]:
        """Get recommended skills for an agent to handle a specific task"""
        # Search for relevant skills and knowledge
        skills = self.memory.search_skills(task_description, limit=limit)
        
        # Filter out already-inherited skills
        try:
            conn = sqlite3.connect(self.memory.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT skill_id FROM skill_inheritance WHERE agent_id = ?
            """, (agent_id,))
            inherited = set(row[0] for row in cursor.fetchall())
            conn.close()
            
            # Add recommendation scores
            recommendations = []
            for skill in skills:
                if skill['id'] not in inherited:
                    skill['recommendation_score'] = (
                        skill['success_rate'] * 0.6 +
                        (skill['usage_count'] / 100) * 0.4
                    )
                    recommendations.append(skill)
            
            return sorted(recommendations, 
                        key=lambda x: x['recommendation_score'], 
                        reverse=True)
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def link_related_executions(self, execution_id_1: str,
                               execution_id_2: str,
                               relationship_type: str = "similar"):
        """Link two executions that are related"""
        try:
            # Get knowledge for both executions
            conn = sqlite3.connect(self.memory.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM knowledge_base 
                WHERE metadata LIKE ?
                LIMIT 1
            """, (f"%{execution_id_1}%",))
            k1 = cursor.fetchone()
            
            cursor.execute("""
                SELECT id FROM knowledge_base 
                WHERE metadata LIKE ?
                LIMIT 1
            """, (f"%{execution_id_2}%",))
            k2 = cursor.fetchone()
            
            conn.close()
            
            if k1 and k2:
                self.memory.link_knowledge(
                    k1[0], k2[0],
                    relationship_type=relationship_type,
                    strength=0.8
                )
                return True
        except Exception as e:
            print(f"Error linking executions: {e}")
        
        return False
    
    def analyze_agent_learning_progress(self, agent_id: str) -> Dict:
        """Analyze learning progress for an agent"""
        try:
            # Get learning sessions
            sessions = self.memory.get_learning_sessions(agent_id, limit=10)
            
            # Get performance analytics
            analytics = self.memory.get_agent_analytics(agent_id, days=30)
            
            # Get inherited skills
            conn = sqlite3.connect(self.memory.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(DISTINCT skill_id) FROM skill_inheritance
                WHERE agent_id = ?
            """, (agent_id,))
            skill_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT AVG(performance_score) FROM skill_inheritance
                WHERE agent_id = ?
            """, (agent_id,))
            avg_performance = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                "agent_id": agent_id,
                "learning_sessions": len(sessions),
                "skills_inherited": skill_count,
                "average_skill_performance": avg_performance,
                "performance_metrics": analytics,
                "recent_improvements": [
                    s.get('improvements', {}) for s in sessions
                ]
            }
        except Exception as e:
            print(f"Error analyzing learning: {e}")
            return {}
    
    def get_collective_knowledge_snapshot(self) -> Dict:
        """Get a snapshot of collective knowledge across all agents"""
        try:
            stats = self.memory.get_stats()
            graph = self.memory.export_knowledge_graph(limit=100)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "total_knowledge_entries": stats['total_knowledge'],
                "unique_contributors": stats['knowledge_sources'],
                "active_skills": stats['active_skills'],
                "learning_agents": stats['agents_learning'],
                "completed_learning_sessions": stats['completed_learning_sessions'],
                "agents_tracked": stats['agents_tracked'],
                "knowledge_relationships": stats['knowledge_relationships'],
                "knowledge_graph": graph
            }
        except Exception as e:
            print(f"Error getting snapshot: {e}")
            return {}
    
    def generate_agent_improvement_report(self, agent_id: str) -> Dict:
        """Generate a comprehensive improvement report for an agent"""
        try:
            progress = self.analyze_agent_learning_progress(agent_id)
            
            # Get performance metrics
            conn = sqlite3.connect(self.memory.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM learning_sessions
                WHERE agent_id = ? AND status = 'completed'
            """, (agent_id,))
            completed_learnings = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM agent_performance
                WHERE agent_id = ?
            """, (agent_id,))
            performance_records = cursor.fetchone()[0]
            
            conn.close()
            
            report = {
                "agent_id": agent_id,
                "report_generated": datetime.now().isoformat(),
                "learning_progress": progress,
                "total_performance_records": performance_records,
                "completed_learning_sessions": completed_learnings,
                "recommendation": (
                    "High performer" if progress.get('average_skill_performance', 0) > 0.8
                    else "Moderate performer" if progress.get('average_skill_performance', 0) > 0.6
                    else "Developing skills"
                )
            }
            
            return report
        except Exception as e:
            print(f"Error generating report: {e}")
            return {}
    
    def close(self):
        """Close all connections"""
        self.memory.close()


# Example usage
if __name__ == "__main__":
    print("Memory System Integration Example")
    print("=" * 60)
    
    # Initialize integrated memory
    memory = ExecutionAwareMemory()
    
    # Example: Record successful task
    print("\n1. Recording successful execution...")
    k = memory.record_successful_task(
        task_id="task_001",
        execution_id="exec_001",
        agent_id="agent_001",
        description="Data validation and cleaning",
        techniques_used=["regex_validation", "type_checking"],
        metrics={"accuracy": 0.99, "speed": 1.2}
    )
    print(f"   Recorded knowledge: {k}")
    
    # Example: Record failure and trigger learning
    print("\n2. Recording failure and triggering learning...")
    session = memory.record_failed_task_and_trigger_learning(
        task_id="task_002",
        execution_id="exec_002",
        agent_id="agent_002",
        description="Complex API integration",
        error_message="Timeout in retry logic",
        mentor_agent_id="agent_001"
    )
    print(f"   Started learning session: {session}")
    
    # Example: Get recommendations
    print("\n3. Getting skill recommendations...")
    recommendations = memory.get_recommended_skills_for_task(
        task_description="Input validation and sanitization",
        agent_id="agent_002",
        limit=5
    )
    print(f"   Found {len(recommendations)} recommendations")
    
    # Example: Analyze progress
    print("\n4. Analyzing agent progress...")
    progress = memory.analyze_agent_learning_progress("agent_002")
    print(f"   Skills inherited: {progress.get('skills_inherited', 0)}")
    print(f"   Learning sessions: {progress.get('learning_sessions', 0)}")
    
    # Example: Collective snapshot
    print("\n5. Getting collective knowledge snapshot...")
    snapshot = memory.get_collective_knowledge_snapshot()
    print(f"   Total knowledge entries: {snapshot.get('total_knowledge_entries', 0)}")
    print(f"   Active skills: {snapshot.get('active_skills', 0)}")
    print(f"   Learning agents: {snapshot.get('learning_agents', 0)}")
    
    memory.close()
    print("\n" + "=" * 60)
    print("Integration example completed!")
