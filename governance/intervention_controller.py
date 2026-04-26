"""
intervention_controller.py — Stop/pause/modify running agents.

Provides emergency controls for halting agent activity, including:
- Individual agent pause/resume
- Task termination (graceful + forced)
- Action rollback for reversible operations
- Runtime guardrails
- Emergency stop (kills ALL agents)
- Dead man's switch (auto-pause if no human activity for N hours)
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from governance.risk_types import AgentStatus

logger = logging.getLogger(__name__)


class InterventionController:
    """
    Runtime control plane for agent supervision.

    Inspired by Claude Computer Use's approval gates and GPT-5.5's
    human-in-loop verification for high-stakes task management.

    Example::

        ctrl = InterventionController(dead_mans_switch_hours=8)
        ctrl.register_agent("agent-1", "legal_research")
        ctrl.pause_agent("agent-1")
        ctrl.resume_agent("agent-1")
        ctrl.emergency_stop()
    """

    def __init__(
        self,
        dead_mans_switch_hours: float = 8.0,
        on_emergency_stop: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Args:
            dead_mans_switch_hours: Auto-pause ALL agents if no human
                                     activity detected for this many hours.
            on_emergency_stop: Optional callback invoked on emergency stop.
        """
        self._agents: Dict[str, AgentStatus] = {}
        self._guardrails: List[str] = []
        self._rollback_log: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._emergency_stopped = False
        self._on_emergency_stop = on_emergency_stop

        # Dead man's switch
        self._dead_mans_hours = dead_mans_switch_hours
        self._last_human_activity: datetime = datetime.now(timezone.utc)
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_running = False

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        current_task: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AgentStatus:
        """Register a new running agent for supervision."""
        status = AgentStatus(
            agent_id=agent_id,
            status="running",
            current_task=current_task,
            started_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        with self._lock:
            self._agents[agent_id] = status
        logger.info("Agent '%s' registered (task=%s)", agent_id, current_task)
        return status

    def deregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from supervision (clean exit)."""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info("Agent '%s' deregistered", agent_id)
                return True
        return False

    def get_running_agents(self) -> List[AgentStatus]:
        """Return all currently registered agents and their statuses."""
        with self._lock:
            return list(self._agents.values())

    # ------------------------------------------------------------------
    # Pause / Resume
    # ------------------------------------------------------------------

    def pause_all(self) -> int:
        """
        Pause ALL running agents (emergency brake).

        Returns count of agents paused.
        """
        count = 0
        with self._lock:
            for agent in self._agents.values():
                if agent.status == "running":
                    agent.status = "paused"
                    agent.paused_at = datetime.now(timezone.utc)
                    count += 1
        logger.warning("PAUSE ALL: %d agents paused", count)
        return count

    def pause_agent(self, agent_id: str) -> bool:
        """
        Pause a specific agent.

        Returns True if paused successfully.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                logger.warning("pause_agent: agent '%s' not found", agent_id)
                return False
            if agent.status != "running":
                return False
            agent.status = "paused"
            agent.paused_at = datetime.now(timezone.utc)
        logger.info("Agent '%s' paused", agent_id)
        return True

    def resume_agent(self, agent_id: str) -> bool:
        """
        Resume a paused agent.

        Returns True if resumed successfully.
        """
        if self._emergency_stopped:
            logger.warning("Cannot resume '%s': emergency stop is active", agent_id)
            return False

        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.status != "paused":
                return False
            agent.status = "running"
            agent.paused_at = None
        self._record_human_activity()
        logger.info("Agent '%s' resumed", agent_id)
        return True

    # ------------------------------------------------------------------
    # Task termination
    # ------------------------------------------------------------------

    def terminate_task(self, task_id: str, reason: str) -> bool:
        """
        Gracefully stop a task, allowing cleanup.

        Returns True if the task was found and marked for termination.
        """
        with self._lock:
            for agent in self._agents.values():
                if agent.current_task == task_id:
                    agent.status = "terminating"
                    agent.metadata["termination_reason"] = reason
                    agent.metadata["terminated_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info("Task '%s' graceful termination requested: %s", task_id, reason)
                    return True
        logger.warning("terminate_task: task '%s' not found", task_id)
        return False

    def force_kill(self, task_id: str) -> bool:
        """
        Emergency-stop a specific task immediately (no cleanup).

        Returns True if found and killed.
        """
        with self._lock:
            for agent_id, agent in list(self._agents.items()):
                if agent.current_task == task_id:
                    agent.status = "killed"
                    agent.metadata["kill_reason"] = "force_kill"
                    agent.metadata["killed_at"] = datetime.now(timezone.utc).isoformat()
                    logger.warning("FORCE KILL: task '%s' (agent='%s')", task_id, agent_id)
                    return True
        return False

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def record_action_for_rollback(
        self,
        task_id: str,
        action: str,
        undo_payload: Dict[str, Any],
    ) -> None:
        """
        Record an action's undo payload for potential rollback.

        Should be called BEFORE executing a reversible action.
        """
        with self._lock:
            self._rollback_log.setdefault(task_id, []).append({
                "action": action,
                "undo_payload": undo_payload,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })

    def rollback(self, task_id: str) -> bool:
        """
        Undo the last recorded action for a task (if reversible).

        Returns True if a rollback entry was found and processed.
        In a real system, this would call the appropriate undo API.
        """
        with self._lock:
            entries = self._rollback_log.get(task_id, [])
            if not entries:
                logger.warning("rollback: no rollback entries for task '%s'", task_id)
                return False
            last = entries.pop()

        logger.info(
            "ROLLBACK: task '%s', action='%s', payload=%s",
            task_id, last["action"], last["undo_payload"]
        )
        # In production: dispatch the undo_payload to the relevant service
        return True

    # ------------------------------------------------------------------
    # Guardrails
    # ------------------------------------------------------------------

    def set_guardrail(self, rule: str) -> None:
        """
        Add a runtime constraint that all agents must respect.

        Example rules:
          - "no_external_api_calls"
          - "read_only_mode"
          - "max_payment_amount:1000"
        """
        with self._lock:
            if rule not in self._guardrails:
                self._guardrails.append(rule)
        logger.info("Guardrail set: '%s'", rule)

    def remove_guardrail(self, rule: str) -> bool:
        """Remove a runtime guardrail. Returns True if it existed."""
        with self._lock:
            if rule in self._guardrails:
                self._guardrails.remove(rule)
                logger.info("Guardrail removed: '%s'", rule)
                return True
        return False

    def get_guardrails(self) -> List[str]:
        """Return the current list of active guardrails."""
        with self._lock:
            return list(self._guardrails)

    def check_guardrail(self, action: str) -> bool:
        """
        Check if an action is blocked by any active guardrail.

        Returns True if the action is ALLOWED, False if blocked.
        """
        with self._lock:
            guardrails = list(self._guardrails)

        for rule in guardrails:
            if rule == "read_only_mode" and action not in ("read_data", "search_database", "list_records", "get_status"):
                if action.startswith(("send_", "update_", "delete_", "publish_", "sign_", "file_", "create_")):
                    logger.warning("Guardrail 'read_only_mode' blocked action '%s'", action)
                    return False
            if rule == "no_external_api_calls" and "external" in action:
                logger.warning("Guardrail 'no_external_api_calls' blocked action '%s'", action)
                return False

        return True

    # ------------------------------------------------------------------
    # Emergency stop
    # ------------------------------------------------------------------

    def emergency_stop(self) -> int:
        """
        Immediately halt ALL agent activity system-wide.

        This is the ultimate kill switch. All agents are paused and no
        new actions may be started until a human clears the stop.

        Returns total agents stopped.
        """
        with self._lock:
            self._emergency_stopped = True
            count = 0
            for agent in self._agents.values():
                if agent.status not in ("killed", "terminated"):
                    agent.status = "emergency_stopped"
                    count += 1

        logger.critical(
            "🚨 EMERGENCY STOP ACTIVATED — %d agents halted. "
            "No agent actions will proceed until cleared.",
            count
        )

        if self._on_emergency_stop:
            try:
                self._on_emergency_stop()
            except Exception as exc:  # noqa: BLE001
                logger.error("Emergency stop callback failed: %s", exc)

        return count

    def clear_emergency_stop(self, authorized_by: str) -> None:
        """
        Clear the emergency stop (requires authorized human).

        Args:
            authorized_by: ID of the human operator clearing the stop.
        """
        with self._lock:
            self._emergency_stopped = False
        self._record_human_activity()
        logger.warning("Emergency stop CLEARED by '%s'", authorized_by)

    @property
    def is_emergency_stopped(self) -> bool:
        """Return True if emergency stop is currently active."""
        return self._emergency_stopped

    # ------------------------------------------------------------------
    # Dead man's switch
    # ------------------------------------------------------------------

    def start_dead_mans_switch(self) -> None:
        """
        Start the background watchdog for the dead man's switch.

        If no human activity is recorded for `dead_mans_switch_hours`,
        all agents are automatically paused.
        """
        if self._watchdog_running:
            return
        self._watchdog_running = True
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="governance-watchdog",
        )
        self._watchdog_thread.start()
        logger.info(
            "Dead man's switch active: auto-pause after %.1f hours of inactivity",
            self._dead_mans_hours
        )

    def stop_dead_mans_switch(self) -> None:
        """Stop the watchdog thread."""
        self._watchdog_running = False

    def record_human_activity(self) -> None:
        """Notify the watchdog that a human is present (resets the timer)."""
        self._record_human_activity()

    def _record_human_activity(self) -> None:
        with self._lock:
            self._last_human_activity = datetime.now(timezone.utc)

    def _watchdog_loop(self) -> None:
        """Background thread: check for human inactivity."""
        while self._watchdog_running:
            time.sleep(60)  # check every minute
            with self._lock:
                last = self._last_human_activity
            elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 3600
            if elapsed >= self._dead_mans_hours and not self._emergency_stopped:
                logger.warning(
                    "Dead man's switch triggered: no human activity for %.1f hours", elapsed
                )
                self.pause_all()
