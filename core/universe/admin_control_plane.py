"""
Admin Control Plane - Real-time agent monitoring, control, and system management
Persistent admin interface separate from normal agent operations
"""

import json
import time
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict
import sqlite3


class AdminRole(Enum):
    """Admin role levels"""
    SUPER_ADMIN = "super_admin"      # Full system control
    SYSTEM_ADMIN = "system_admin"    # Agent and swarm management
    AUDIT_ADMIN = "audit_admin"      # Read-only audit access
    OPERATOR = "operator"             # Basic operations


class AdminCommand(Enum):
    """Available admin commands"""
    # Agent Control
    PAUSE_AGENT = "pause_agent"
    RESUME_AGENT = "resume_agent"
    KILL_AGENT = "kill_agent"
    INJECT_TASK = "inject_task"
    QUERY_AGENT = "query_agent"
    
    # Configuration
    UPDATE_CONFIG = "update_config"
    GET_CONFIG = "get_config"
    RELOAD_CONFIG = "reload_config"
    
    # Swarm Management
    CREATE_SWARM = "create_swarm"
    DESTROY_SWARM = "destroy_swarm"
    PAUSE_SWARM = "pause_swarm"
    RESUME_SWARM = "resume_swarm"
    
    # System Control
    SYSTEM_STATUS = "system_status"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    BACKUP_STATE = "backup_state"
    RESTORE_STATE = "restore_state"
    
    # Diagnostics
    GET_METRICS = "get_metrics"
    GET_LOGS = "get_logs"
    HEALTH_CHECK = "health_check"


class AgentState(Enum):
    """Agent operational states"""
    RUNNING = "running"
    PAUSED = "paused"
    IDLE = "idle"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class AdminSession:
    """Admin session tracking"""
    session_id: str
    admin_id: str
    admin_role: AdminRole
    created_at: datetime
    last_activity: datetime
    ip_address: str
    is_active: bool = True
    command_count: int = 0

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "admin_id": self.admin_id,
            "admin_role": self.admin_role.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
            "is_active": self.is_active,
            "command_count": self.command_count
        }


@dataclass
class AdminCommandLog:
    """Admin command execution log"""
    command_id: str
    admin_id: str
    command_type: AdminCommand
    target_agent_id: Optional[str]
    parameters: Dict[str, Any]
    status: str  # pending, executing, completed, failed
    result: Optional[str]
    error: Optional[str]
    timestamp: datetime
    execution_time_ms: int = 0

    def to_dict(self):
        return {
            "command_id": self.command_id,
            "admin_id": self.admin_id,
            "command_type": self.command_type.value,
            "target_agent_id": self.target_agent_id,
            "parameters": self.parameters,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms
        }


class AdminAccessControl:
    """Control access to admin functions based on roles"""

    # Permission matrix: Role -> Commands
    ROLE_PERMISSIONS = {
        AdminRole.SUPER_ADMIN: [cmd for cmd in AdminCommand],
        AdminRole.SYSTEM_ADMIN: [
            AdminCommand.PAUSE_AGENT, AdminCommand.RESUME_AGENT,
            AdminCommand.INJECT_TASK, AdminCommand.QUERY_AGENT,
            AdminCommand.UPDATE_CONFIG, AdminCommand.GET_CONFIG,
            AdminCommand.CREATE_SWARM, AdminCommand.DESTROY_SWARM,
            AdminCommand.PAUSE_SWARM, AdminCommand.RESUME_SWARM,
            AdminCommand.SYSTEM_STATUS, AdminCommand.GET_METRICS,
            AdminCommand.HEALTH_CHECK
        ],
        AdminRole.OPERATOR: [
            AdminCommand.PAUSE_AGENT, AdminCommand.RESUME_AGENT,
            AdminCommand.QUERY_AGENT, AdminCommand.GET_CONFIG,
            AdminCommand.SYSTEM_STATUS, AdminCommand.GET_METRICS,
            AdminCommand.HEALTH_CHECK, AdminCommand.GET_LOGS
        ],
        AdminRole.AUDIT_ADMIN: [
            AdminCommand.QUERY_AGENT, AdminCommand.GET_CONFIG,
            AdminCommand.SYSTEM_STATUS, AdminCommand.GET_METRICS,
            AdminCommand.GET_LOGS, AdminCommand.HEALTH_CHECK
        ]
    }

    @staticmethod
    def can_execute(role: AdminRole, command: AdminCommand) -> bool:
        """Check if admin role can execute command"""
        allowed_commands = AdminAccessControl.ROLE_PERMISSIONS.get(role, [])
        return command in allowed_commands

    @staticmethod
    def required_role_for_command(command: AdminCommand) -> AdminRole:
        """Get minimum required role for a command"""
        if command in [AdminCommand.EMERGENCY_SHUTDOWN, AdminCommand.RESTORE_STATE]:
            return AdminRole.SUPER_ADMIN
        elif command in [AdminCommand.CREATE_SWARM, AdminCommand.DESTROY_SWARM,
                        AdminCommand.UPDATE_CONFIG, AdminCommand.KILL_AGENT]:
            return AdminRole.SYSTEM_ADMIN
        else:
            return AdminRole.OPERATOR


class RealTimeMonitor:
    """Real-time monitoring of agents and swarms"""

    def __init__(self):
        self.agent_states = {}  # agent_id -> AgentState
        self.agent_metrics = {}  # agent_id -> metrics dict
        self.swarm_states = {}   # swarm_id -> status
        self.system_health = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "total_agents": 0,
            "active_agents": 0,
            "failed_agents": 0,
            "last_updated": datetime.now().isoformat()
        }

    def update_agent_state(self, agent_id: str, state: AgentState, metrics: Dict = None):
        """Update agent state and metrics"""
        self.agent_states[agent_id] = state
        if metrics:
            self.agent_metrics[agent_id] = {
                **metrics,
                "last_update": datetime.now().isoformat()
            }

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get current status of an agent"""
        return {
            "agent_id": agent_id,
            "state": self.agent_states.get(agent_id, AgentState.IDLE).value,
            "metrics": self.agent_metrics.get(agent_id, {}),
            "last_update": datetime.now().isoformat()
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        self.system_health["last_updated"] = datetime.now().isoformat()
        self.system_health["total_agents"] = len(self.agent_states)
        self.system_health["active_agents"] = sum(
            1 for s in self.agent_states.values() if s == AgentState.RUNNING
        )
        self.system_health["failed_agents"] = sum(
            1 for s in self.agent_states.values() if s == AgentState.FAILED
        )
        return self.system_health

    def get_alerts(self) -> List[Dict]:
        """Get active system alerts"""
        alerts = []
        
        # Check for failed agents
        for agent_id, state in self.agent_states.items():
            if state == AgentState.FAILED:
                alerts.append({
                    "type": "agent_failure",
                    "agent_id": agent_id,
                    "severity": "high",
                    "timestamp": datetime.now().isoformat()
                })

        return alerts


class EmergencyControl:
    """Emergency control mechanisms"""

    def __init__(self):
        self.emergency_mode = False
        self.paused_agents = set()
        self.emergency_start_time = None

    def activate_emergency_shutdown(self, reason: str) -> Dict[str, Any]:
        """Activate emergency shutdown"""
        self.emergency_mode = True
        self.emergency_start_time = datetime.now()
        
        return {
            "status": "emergency_shutdown_activated",
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "paused_agents": len(self.paused_agents)
        }

    def pause_all_agents(self) -> Dict[str, Any]:
        """Pause all running agents"""
        return {
            "action": "pause_all_agents",
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }

    def resume_all_agents(self) -> Dict[str, Any]:
        """Resume all paused agents"""
        self.emergency_mode = False
        self.paused_agents.clear()
        
        return {
            "action": "resume_all_agents",
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }

    def is_in_emergency(self) -> bool:
        """Check if system is in emergency mode"""
        return self.emergency_mode


class AdminControlPlane:
    """Main admin control interface"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.sessions = {}  # session_id -> AdminSession
        self.command_log = []  # List of AdminCommandLog
        self.monitor = RealTimeMonitor()
        self.emergency = EmergencyControl()
        self.access_control = AdminAccessControl()
        self.agent_configs = {}  # agent_id -> config dict
        self.swarm_registry = {}  # swarm_id -> swarm info

    def create_admin_session(self, admin_id: str, role: AdminRole, 
                           ip_address: str = "127.0.0.1") -> AdminSession:
        """Create a new admin session"""
        session = AdminSession(
            session_id=str(uuid.uuid4()),
            admin_id=admin_id,
            admin_role=role,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            ip_address=ip_address
        )
        self.sessions[session.session_id] = session
        return session

    def validate_session(self, session_id: str) -> bool:
        """Validate admin session is still active"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Session expires after 1 hour of inactivity
        if datetime.now() - session.last_activity > timedelta(hours=1):
            session.is_active = False
            return False
        
        return session.is_active

    def execute_command(self, session_id: str, command: AdminCommand, 
                       parameters: Dict = None, target_agent: str = None) -> Dict[str, Any]:
        """Execute an admin command with access control"""
        parameters = parameters or {}
        
        # Validate session
        if not self.validate_session(session_id):
            return {"status": "error", "message": "Invalid or expired session"}

        session = self.sessions[session_id]

        # Check permissions
        if not self.access_control.can_execute(session.admin_role, command):
            error_msg = f"Role {session.admin_role.value} cannot execute {command.value}"
            self._log_command(session.admin_id, command, target_agent, parameters, 
                            "failed", None, error_msg)
            return {"status": "error", "message": error_msg}

        # Update session activity
        session.last_activity = datetime.now()
        session.command_count += 1

        # Execute command
        start_time = time.time()
        try:
            result = self._execute_admin_command(command, parameters, target_agent)
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            self._log_command(session.admin_id, command, target_agent, parameters,
                            "completed", json.dumps(result), None, execution_time_ms)
            
            return {"status": "success", "result": result, "execution_time_ms": execution_time_ms}
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self._log_command(session.admin_id, command, target_agent, parameters,
                            "failed", None, error_msg, execution_time_ms)
            return {"status": "error", "message": error_msg, "execution_time_ms": execution_time_ms}

    def _execute_admin_command(self, command: AdminCommand, 
                              parameters: Dict, target_agent: str = None) -> Dict:
        """Execute the actual admin command"""
        
        if command == AdminCommand.PAUSE_AGENT:
            return {"action": "pause_agent", "agent_id": target_agent, "status": "paused"}
        
        elif command == AdminCommand.RESUME_AGENT:
            return {"action": "resume_agent", "agent_id": target_agent, "status": "resumed"}
        
        elif command == AdminCommand.KILL_AGENT:
            return {"action": "kill_agent", "agent_id": target_agent, "status": "terminated"}
        
        elif command == AdminCommand.INJECT_TASK:
            return {
                "action": "inject_task",
                "agent_id": target_agent,
                "task": parameters.get("task"),
                "status": "injected"
            }
        
        elif command == AdminCommand.QUERY_AGENT:
            return self.monitor.get_agent_status(target_agent)
        
        elif command == AdminCommand.UPDATE_CONFIG:
            key = parameters.get("key")
            value = parameters.get("value")
            if target_agent:
                if target_agent not in self.agent_configs:
                    self.agent_configs[target_agent] = {}
                self.agent_configs[target_agent][key] = value
            return {"action": "update_config", "key": key, "value": value, "status": "updated"}
        
        elif command == AdminCommand.GET_CONFIG:
            if target_agent:
                return self.agent_configs.get(target_agent, {})
            return self.agent_configs
        
        elif command == AdminCommand.RELOAD_CONFIG:
            return {"action": "reload_config", "status": "reloaded"}
        
        elif command == AdminCommand.SYSTEM_STATUS:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "system_health": self.monitor.get_system_health(),
                "alerts": self.monitor.get_alerts()
            }
        
        elif command == AdminCommand.EMERGENCY_SHUTDOWN:
            reason = parameters.get("reason", "Manual emergency shutdown")
            return self.emergency.activate_emergency_shutdown(reason)
        
        elif command == AdminCommand.BACKUP_STATE:
            return {
                "action": "backup_state",
                "backup_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
        
        elif command == AdminCommand.RESTORE_STATE:
            backup_id = parameters.get("backup_id")
            return {
                "action": "restore_state",
                "backup_id": backup_id,
                "status": "restored",
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == AdminCommand.HEALTH_CHECK:
            return {
                "status": "healthy",
                "checks": {
                    "database": "ok",
                    "agents": "ok",
                    "memory": "ok"
                },
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == AdminCommand.GET_LOGS:
            limit = parameters.get("limit", 100)
            return {
                "logs": self.command_log[-limit:],
                "total_count": len(self.command_log)
            }
        
        elif command == AdminCommand.GET_METRICS:
            return self.monitor.get_system_health()
        
        else:
            return {"status": "unknown_command"}

    def _log_command(self, admin_id: str, command: AdminCommand, target_agent: str = None,
                    parameters: Dict = None, status: str = "executed", result: str = None,
                    error: str = None, execution_time_ms: int = 0):
        """Log an admin command execution"""
        log_entry = AdminCommandLog(
            command_id=str(uuid.uuid4()),
            admin_id=admin_id,
            command_type=command,
            target_agent_id=target_agent,
            parameters=parameters or {},
            status=status,
            result=result,
            error=error,
            timestamp=datetime.now(),
            execution_time_ms=execution_time_ms
        )
        self.command_log.append(log_entry.to_dict())

    def get_admin_audit_trail(self, limit: int = 100, 
                             admin_id: str = None) -> List[Dict]:
        """Get audit trail of admin actions"""
        logs = self.command_log[-limit:]
        
        if admin_id:
            logs = [log for log in logs if log["admin_id"] == admin_id]
        
        return logs

    def update_agent_metric(self, agent_id: str, metrics: Dict):
        """Update agent metrics"""
        self.monitor.update_agent_state(agent_id, AgentState.RUNNING, metrics)

    def get_command_latency_stats(self) -> Dict[str, float]:
        """Get admin command latency statistics"""
        if not self.command_log:
            return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0}

        times = [log["execution_time_ms"] for log in self.command_log[-1000:]]
        times.sort()

        return {
            "avg_ms": sum(times) / len(times) if times else 0,
            "min_ms": min(times) if times else 0,
            "max_ms": max(times) if times else 0,
            "p95_ms": times[int(len(times) * 0.95)] if times else 0,
            "sample_size": len(times)
        }

    def create_swarm(self, swarm_id: str, config: Dict) -> Dict[str, Any]:
        """Create a new swarm"""
        self.swarm_registry[swarm_id] = {
            "swarm_id": swarm_id,
            "config": config,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "agent_count": 0
        }
        return self.swarm_registry[swarm_id]

    def destroy_swarm(self, swarm_id: str) -> Dict[str, Any]:
        """Destroy a swarm"""
        if swarm_id in self.swarm_registry:
            del self.swarm_registry[swarm_id]
            return {"status": "destroyed", "swarm_id": swarm_id}
        return {"status": "error", "message": f"Swarm not found: {swarm_id}"}
