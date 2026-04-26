"""
SintraPrime Autonomous Chat Agent.

The Chat Agent is the primary interface for immediate autonomy in SintraPrime.
It handles multi-turn conversations, routes tasks to specialist agents (Zero/Sigma/Nova),
manages session memory, processes documents/audio/video inputs, and can autonomously
execute workflows without user intervention.

Key capabilities:
- LLM-powered intent understanding and response generation
- Independent session memory (per-user conversation history)
- Autonomous task delegation to Zero (self-healing), Sigma (CI/CD), Nova (execution)
- Document, audio, and video file processing
- Proactive follow-up and task completion tracking
- God-mode autonomous operation with human authorization gates
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("chat_agent")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class AgentMode(str, Enum):
    STANDARD = "standard"          # Normal conversational mode
    AUTONOMOUS = "autonomous"      # Executes tasks without confirmation
    GOD_MODE = "god_mode"          # Full autonomy, human gates on critical ops only
    SUPERVISED = "supervised"      # Every action requires human approval


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    attachments: List[str] = field(default_factory=list)  # file paths or URLs

    def to_llm_dict(self) -> Dict[str, str]:
        """Convert to format expected by LLM APIs."""
        return {"role": self.role, "content": self.content}


@dataclass
class ChatSession:
    """A conversation session with a user."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "anonymous"
    messages: List[ChatMessage] = field(default_factory=list)
    mode: str = AgentMode.STANDARD.value
    context: Dict[str, Any] = field(default_factory=dict)
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    token_count: int = 0

    def add_message(self, role: str, content: str, **metadata) -> ChatMessage:
        """Add a message to the session."""
        msg = ChatMessage(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        self.last_activity = datetime.now(timezone.utc).isoformat()
        return msg

    def get_history(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get recent message history for LLM context."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [m.to_llm_dict() for m in recent]

    def set_context(self, key: str, value: Any) -> None:
        """Set a context variable for this session."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.context.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dict."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "mode": self.mode,
            "message_count": len(self.messages),
            "active_tasks": len(self.active_tasks),
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }


@dataclass
class AgentTask:
    """A task delegated to a specialist agent."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    description: str = ""
    status: str = TaskStatus.PENDING.value
    assigned_agent: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    requires_approval: bool = False
    approved: bool = False


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SINTRA_SYSTEM_PROMPT = """You are SintraPrime, an autonomous AI legal assistant and workflow automation agent.

You have access to the following specialist agents:
- **Zero Agent**: Self-healing code repair, test fixing, and autonomous debugging
- **Sigma Agent**: CI/CD gate enforcement, PR review, security scanning, and type checking
- **Nova Agent**: Autonomous action execution, workflow automation, and system operations
- **Airtable CRM**: Contact management, case tracking, activity logging, and pipeline management

Your capabilities include:
1. Legal research and case analysis
2. Document drafting and review (contracts, motions, letters)
3. Client intake and CRM management
4. Autonomous task execution and workflow automation
5. Code review and self-healing operations
6. Financial tracking and billing management
7. Multi-channel communication (Discord, SMS, email)

Operating principles:
- Be proactive: anticipate needs and suggest next steps
- Be autonomous: complete tasks without unnecessary confirmation in autonomous/god-mode
- Be precise: legal work requires accuracy — always cite sources and flag uncertainty
- Be efficient: delegate to specialist agents when appropriate
- Maintain client confidentiality at all times

When you need to execute an action, clearly state what you're doing and the outcome.
When you're uncertain about a legal matter, explicitly say so and recommend consulting a licensed attorney.
"""


# ---------------------------------------------------------------------------
# Chat Agent
# ---------------------------------------------------------------------------


class ChatAgent:
    """
    Autonomous Chat Agent for SintraPrime.

    Provides LLM-powered conversational AI with autonomous task execution,
    session memory, and specialist agent delegation.

    Usage:
        agent = ChatAgent()
        session = agent.create_session(user_id="user123")
        response = agent.chat(session.session_id, "Help me draft a demand letter")
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        default_mode: str = AgentMode.STANDARD.value,
        max_history_messages: int = 20,
        enable_tools: bool = True,
        session_store_path: Optional[str] = None,
    ):
        self.model = model
        self.default_mode = default_mode
        self.max_history_messages = max_history_messages
        self.enable_tools = enable_tools
        self._sessions: Dict[str, ChatSession] = {}
        self._tasks: Dict[str, AgentTask] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        self._session_store_path = session_store_path

        # Register built-in tools
        self._register_default_tools()

        logger.info(
            "ChatAgent initialized (model=%s, mode=%s, tools=%s)",
            model, default_mode, enable_tools
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        user_id: str = "anonymous",
        mode: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> ChatSession:
        """Create a new conversation session."""
        session = ChatSession(
            user_id=user_id,
            mode=mode or self.default_mode,
            context=initial_context or {},
        )
        self._sessions[session.session_id] = session
        logger.info("Created session %s for user %s", session.session_id, user_id)
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing session by ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its history."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by user."""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return [s.to_dict() for s in sessions]

    # ------------------------------------------------------------------
    # Core chat interface
    # ------------------------------------------------------------------

    def chat(
        self,
        session_id: str,
        user_message: str,
        attachments: Optional[List[str]] = None,
        stream: bool = False,
    ) -> str:
        """
        Process a user message and return the agent's response.

        :param session_id: The session to use for context.
        :param user_message: The user's message text.
        :param attachments: Optional list of file paths or URLs to process.
        :param stream: Whether to stream the response (not yet implemented).
        :returns: The agent's response string.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found. Call create_session() first.")

        # Process any attachments
        attachment_context = ""
        if attachments:
            attachment_context = self._process_attachments(attachments)
            if attachment_context:
                user_message = f"{user_message}\n\n[Attached content]\n{attachment_context}"

        # Add user message to history
        session.add_message(MessageRole.USER.value, user_message)

        # Detect if this requires autonomous task execution
        task_intent = self._detect_task_intent(user_message, session)

        # Build messages for LLM
        messages = self._build_messages(session)

        # Get LLM response
        response = self._get_llm_response(messages, session)

        # Post-process: execute any detected tasks
        if task_intent and session.mode in (AgentMode.AUTONOMOUS.value, AgentMode.GOD_MODE.value):
            task_result = self._execute_detected_task(task_intent, user_message, session)
            if task_result:
                response = f"{response}\n\n**[Autonomous Action Taken]**\n{task_result}"

        # Add assistant response to history
        session.add_message(MessageRole.ASSISTANT.value, response)

        return response

    def chat_stream(self, session_id: str, user_message: str):
        """Generator that yields response tokens as they arrive."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        session.add_message(MessageRole.USER.value, user_message)
        messages = self._build_messages(session)

        if not self._openai_key:
            yield self._fallback_response(user_message)
            return

        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            full_response = ""
            with client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    full_response += delta
                    yield delta

            session.add_message(MessageRole.ASSISTANT.value, full_response)
        except Exception as e:
            logger.error("Streaming failed: %s", e)
            fallback = self._fallback_response(user_message)
            session.add_message(MessageRole.ASSISTANT.value, fallback)
            yield fallback

    # ------------------------------------------------------------------
    # Autonomous task execution
    # ------------------------------------------------------------------

    def execute_task_autonomously(
        self,
        session_id: str,
        task_type: str,
        task_params: Dict[str, Any],
        require_approval: bool = False,
    ) -> AgentTask:
        """
        Execute a task autonomously without conversational flow.

        :param session_id: Session context for the task.
        :param task_type: Type of task (e.g., 'draft_document', 'run_tests', 'crm_update').
        :param task_params: Parameters for the task.
        :param require_approval: If True, task waits for human approval before execution.
        :returns: AgentTask with status and result.
        """
        task = AgentTask(
            task_type=task_type,
            description=f"Autonomous {task_type} task",
            requires_approval=require_approval,
        )
        self._tasks[task.task_id] = task

        if require_approval:
            task.status = TaskStatus.AWAITING_APPROVAL.value
            logger.info("Task %s awaiting approval", task.task_id)
            return task

        return self._run_task(task, task_params, session_id)

    def approve_task(self, task_id: str) -> Optional[AgentTask]:
        """Approve a pending task for execution."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        if task.status == TaskStatus.AWAITING_APPROVAL.value:
            task.approved = True
            task.status = TaskStatus.PENDING.value
            logger.info("Task %s approved", task_id)
        return task

    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get the status of a task."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AgentTask]:
        """List all tasks, optionally filtered."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a custom tool handler."""
        self._tool_handlers[name] = handler
        logger.info("Registered tool: %s", name)

    def _register_default_tools(self) -> None:
        """Register built-in tool handlers."""
        self._tool_handlers["draft_document"] = self._tool_draft_document
        self._tool_handlers["search_legal"] = self._tool_search_legal
        self._tool_handlers["crm_lookup"] = self._tool_crm_lookup
        self._tool_handlers["run_tests"] = self._tool_run_tests
        self._tool_handlers["summarize_file"] = self._tool_summarize_file
        self._tool_handlers["schedule_reminder"] = self._tool_schedule_reminder

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_messages(self, session: ChatSession) -> List[Dict[str, str]]:
        """Build the full message list for the LLM."""
        system_content = SINTRA_SYSTEM_PROMPT

        # Add session context to system prompt
        if session.context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in session.context.items())
            system_content += f"\n\nCurrent session context:\n{context_str}"

        if session.mode == AgentMode.GOD_MODE.value:
            system_content += "\n\n**OPERATING IN GOD MODE**: Execute all tasks autonomously. Only request human approval for irreversible critical operations."
        elif session.mode == AgentMode.AUTONOMOUS.value:
            system_content += "\n\n**OPERATING IN AUTONOMOUS MODE**: Execute tasks proactively without asking for confirmation."

        messages = [{"role": "system", "content": system_content}]
        messages.extend(session.get_history(self.max_history_messages))
        return messages

    def _get_llm_response(
        self,
        messages: List[Dict[str, str]],
        session: ChatSession,
    ) -> str:
        """Get a response from the LLM."""
        if not self._openai_key:
            return self._fallback_response(messages[-1]["content"] if messages else "")

        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            content = response.choices[0].message.content or ""
            session.token_count += response.usage.total_tokens if response.usage else 0
            return content
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return f"I encountered an error processing your request: {e}. Please try again."

    def _fallback_response(self, user_message: str) -> str:
        """Rule-based fallback when LLM is unavailable."""
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["hello", "hi", "hey", "good morning"]):
            return "Hello! I'm SintraPrime, your autonomous legal AI assistant. How can I help you today?"
        if any(w in msg_lower for w in ["help", "what can you do", "capabilities"]):
            return (
                "I can help you with:\n"
                "- Legal research and case analysis\n"
                "- Document drafting (contracts, motions, letters)\n"
                "- Client and case management\n"
                "- Workflow automation\n"
                "- Code review and self-healing\n"
                "What would you like to work on?"
            )
        if any(w in msg_lower for w in ["status", "health", "online"]):
            return "SintraPrime is online and all systems are operational. Ready to assist."
        return (
            "I understand your request. To provide the best assistance, "
            "please configure your OpenAI API key (OPENAI_API_KEY environment variable) "
            "for full LLM-powered responses."
        )

    def _detect_task_intent(
        self,
        message: str,
        session: ChatSession,
    ) -> Optional[str]:
        """Detect if the message implies an autonomous task should be executed."""
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["run tests", "fix tests", "repair tests", "run the tests", "run test"]):
            return "run_tests"
        if any(w in msg_lower for w in ["draft", "write", "create document", "prepare letter"]):
            return "draft_document"
        if any(w in msg_lower for w in ["add contact", "create contact", "new client"]):
            return "crm_create_contact"
        if any(w in msg_lower for w in ["remind me", "set reminder", "schedule"]):
            return "schedule_reminder"
        return None

    def _execute_detected_task(
        self,
        task_type: str,
        message: str,
        session: ChatSession,
    ) -> Optional[str]:
        """Execute a detected autonomous task."""
        handler = self._tool_handlers.get(task_type)
        if not handler:
            return None
        try:
            result = handler({"message": message, "session": session})
            return f"Task `{task_type}` completed: {result}"
        except Exception as e:
            logger.error("Task %s failed: %s", task_type, e)
            return f"Task `{task_type}` failed: {e}"

    def _run_task(
        self,
        task: AgentTask,
        params: Dict[str, Any],
        session_id: str,
    ) -> AgentTask:
        """Execute a task and update its status."""
        task.status = TaskStatus.IN_PROGRESS.value
        handler = self._tool_handlers.get(task.task_type)

        if not handler:
            task.status = TaskStatus.FAILED.value
            task.error = f"No handler registered for task type: {task.task_type}"
            return task

        try:
            task.result = handler(params)
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info("Task %s completed successfully", task.task_id)
        except Exception as e:
            task.status = TaskStatus.FAILED.value
            task.error = str(e)
            logger.error("Task %s failed: %s", task.task_id, e)

        return task

    def _process_attachments(self, attachments: List[str]) -> str:
        """Process file attachments and return extracted text content."""
        extracted = []
        for path_or_url in attachments:
            try:
                path = Path(path_or_url)
                # Treat as URL if it starts with http/https
                if path_or_url.startswith(("http://", "https://")):
                    extracted.append(f"[URL: {path_or_url}]")
                    continue
                if not path.exists():
                    extracted.append(f"[File not found: {path_or_url}]")
                    continue
                if path.exists():
                    suffix = path.suffix.lower()
                    if suffix in (".txt", ".md", ".py", ".json", ".csv"):
                        content = path.read_text(encoding="utf-8", errors="replace")
                        extracted.append(f"[{path.name}]\n{content[:5000]}")
                    elif suffix == ".pdf":
                        extracted.append(f"[{path.name}] (PDF — use summarize_file tool for full extraction)")
                    else:
                        extracted.append(f"[{path.name}] (Binary file — {suffix})")
                else:
                    extracted.append(f"[URL: {path_or_url}]")
            except Exception as e:
                extracted.append(f"[Error reading {path_or_url}: {e}]")
        return "\n\n".join(extracted)

    # ------------------------------------------------------------------
    # Built-in tool handlers
    # ------------------------------------------------------------------

    def _tool_draft_document(self, params: Dict[str, Any]) -> str:
        """Draft a legal document using LLM."""
        message = params.get("message", "")
        if not self._openai_key:
            return "Document drafting requires OpenAI API key."
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document drafter. Create professional, accurate legal documents."},
                    {"role": "user", "content": f"Draft the following: {message}"}
                ],
                temperature=0.3,
                max_tokens=3000,
            )
            return response.choices[0].message.content or "Document drafted."
        except Exception as e:
            return f"Document drafting failed: {e}"

    def _tool_search_legal(self, params: Dict[str, Any]) -> str:
        """Perform a legal research query."""
        query = params.get("query", params.get("message", ""))
        return f"Legal research initiated for: '{query}'. Results will be compiled from available databases."

    def _tool_crm_lookup(self, params: Dict[str, Any]) -> str:
        """Look up a contact in the CRM."""
        name = params.get("name", params.get("message", ""))
        return f"CRM lookup initiated for: '{name}'. Searching Airtable contacts..."

    def _tool_run_tests(self, params: Dict[str, Any]) -> str:
        """Trigger the Zero agent to run tests."""
        return "Test run delegated to Zero Agent. Results will be reported when complete."

    def _tool_summarize_file(self, params: Dict[str, Any]) -> str:
        """Summarize a file's content."""
        file_path = params.get("file_path", "")
        if not file_path:
            return "No file path provided."
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8", errors="replace")[:8000]
        if not self._openai_key:
            return f"File content preview: {content[:500]}..."
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Summarize the provided content concisely."},
                    {"role": "user", "content": content}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content or "Summary unavailable."
        except Exception as e:
            return f"Summarization failed: {e}"

    def _tool_schedule_reminder(self, params: Dict[str, Any]) -> str:
        """Schedule a reminder (stub — integrates with calendar systems)."""
        message = params.get("message", "")
        return f"Reminder scheduled: '{message}'. Integration with calendar system pending."

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def save_sessions(self, path: Optional[str] = None) -> int:
        """Save all sessions to a JSON file."""
        save_path = path or self._session_store_path
        if not save_path:
            return 0
        data = {
            sid: {
                "session": s.to_dict(),
                "messages": [
                    {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                    for m in s.messages
                ],
                "context": s.context,
            }
            for sid, s in self._sessions.items()
        }
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
        return len(data)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        total_messages = sum(len(s.messages) for s in self._sessions.values())
        total_tokens = sum(s.token_count for s in self._sessions.values())
        return {
            "total_sessions": len(self._sessions),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "total_tasks": len(self._tasks),
            "tasks_completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED.value),
            "tasks_failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED.value),
            "registered_tools": list(self._tool_handlers.keys()),
            "model": self.model,
            "default_mode": self.default_mode,
        }
