"""
Tests for the SintraPrime Autonomous Chat Agent.
All LLM calls are mocked so tests run without an API key.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from agents.chat.chat_agent import (
    ChatAgent, ChatSession, ChatMessage, AgentTask,
    AgentMode, TaskStatus, MessageRole, SINTRA_SYSTEM_PROMPT
)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestChatMessage(unittest.TestCase):
    """Test the ChatMessage data model."""

    def test_message_creation(self):
        msg = ChatMessage(role="user", content="Hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")
        self.assertIsNotNone(msg.message_id)
        self.assertIsNotNone(msg.timestamp)

    def test_to_llm_dict(self):
        msg = ChatMessage(role="assistant", content="Hi there!")
        d = msg.to_llm_dict()
        self.assertEqual(d, {"role": "assistant", "content": "Hi there!"})

    def test_message_with_metadata(self):
        msg = ChatMessage(role="user", content="Test", metadata={"intent": "legal"})
        self.assertEqual(msg.metadata["intent"], "legal")


class TestChatSession(unittest.TestCase):
    """Test the ChatSession data model."""

    def setUp(self):
        self.session = ChatSession(user_id="test_user")

    def test_session_creation(self):
        self.assertEqual(self.session.user_id, "test_user")
        self.assertEqual(self.session.mode, AgentMode.STANDARD.value)
        self.assertEqual(len(self.session.messages), 0)
        self.assertIsNotNone(self.session.session_id)

    def test_add_message(self):
        msg = self.session.add_message("user", "Hello")
        self.assertEqual(len(self.session.messages), 1)
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")

    def test_get_history_empty(self):
        history = self.session.get_history()
        self.assertEqual(history, [])

    def test_get_history_with_messages(self):
        self.session.add_message("user", "Hello")
        self.session.add_message("assistant", "Hi!")
        history = self.session.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_get_history_max_messages(self):
        for i in range(30):
            self.session.add_message("user", f"Message {i}")
        history = self.session.get_history(max_messages=10)
        self.assertEqual(len(history), 10)

    def test_set_get_context(self):
        self.session.set_context("active_case", "Smith v. Jones")
        self.assertEqual(self.session.get_context("active_case"), "Smith v. Jones")

    def test_get_context_default(self):
        result = self.session.get_context("nonexistent", default="fallback")
        self.assertEqual(result, "fallback")

    def test_to_dict(self):
        d = self.session.to_dict()
        self.assertIn("session_id", d)
        self.assertIn("user_id", d)
        self.assertIn("mode", d)
        self.assertIn("message_count", d)
        self.assertEqual(d["user_id"], "test_user")


class TestAgentTask(unittest.TestCase):
    """Test the AgentTask data model."""

    def test_task_creation(self):
        task = AgentTask(task_type="run_tests", description="Run the test suite")
        self.assertEqual(task.task_type, "run_tests")
        self.assertEqual(task.status, TaskStatus.PENDING.value)
        self.assertIsNone(task.result)
        self.assertFalse(task.requires_approval)

    def test_task_with_approval(self):
        task = AgentTask(task_type="deploy", requires_approval=True)
        self.assertTrue(task.requires_approval)
        self.assertFalse(task.approved)


# ---------------------------------------------------------------------------
# ChatAgent Core Tests
# ---------------------------------------------------------------------------

class TestChatAgentInit(unittest.TestCase):
    """Test ChatAgent initialization."""

    def test_default_init(self):
        agent = ChatAgent()
        self.assertEqual(agent.model, "gpt-4o-mini")
        self.assertEqual(agent.default_mode, AgentMode.STANDARD.value)
        self.assertEqual(len(agent._sessions), 0)

    def test_custom_init(self):
        agent = ChatAgent(model="gpt-4o", default_mode=AgentMode.AUTONOMOUS.value)
        self.assertEqual(agent.model, "gpt-4o")
        self.assertEqual(agent.default_mode, AgentMode.AUTONOMOUS.value)

    def test_default_tools_registered(self):
        agent = ChatAgent()
        self.assertIn("draft_document", agent._tool_handlers)
        self.assertIn("search_legal", agent._tool_handlers)
        self.assertIn("crm_lookup", agent._tool_handlers)
        self.assertIn("run_tests", agent._tool_handlers)
        self.assertIn("summarize_file", agent._tool_handlers)
        self.assertIn("schedule_reminder", agent._tool_handlers)


class TestChatAgentSessions(unittest.TestCase):
    """Test session management."""

    def setUp(self):
        self.agent = ChatAgent()

    def test_create_session(self):
        session = self.agent.create_session(user_id="alice")
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "alice")
        self.assertIn(session.session_id, self.agent._sessions)

    def test_create_session_default_user(self):
        session = self.agent.create_session()
        self.assertEqual(session.user_id, "anonymous")

    def test_create_session_with_mode(self):
        session = self.agent.create_session(mode=AgentMode.AUTONOMOUS.value)
        self.assertEqual(session.mode, AgentMode.AUTONOMOUS.value)

    def test_create_session_with_context(self):
        session = self.agent.create_session(initial_context={"firm": "Smith & Associates"})
        self.assertEqual(session.get_context("firm"), "Smith & Associates")

    def test_get_session_exists(self):
        session = self.agent.create_session()
        retrieved = self.agent.get_session(session.session_id)
        self.assertEqual(retrieved, session)

    def test_get_session_not_found(self):
        result = self.agent.get_session("nonexistent-id")
        self.assertIsNone(result)

    def test_delete_session(self):
        session = self.agent.create_session()
        sid = session.session_id
        result = self.agent.delete_session(sid)
        self.assertTrue(result)
        self.assertNotIn(sid, self.agent._sessions)

    def test_delete_nonexistent_session(self):
        result = self.agent.delete_session("nonexistent")
        self.assertFalse(result)

    def test_list_sessions_all(self):
        self.agent.create_session(user_id="alice")
        self.agent.create_session(user_id="bob")
        sessions = self.agent.list_sessions()
        self.assertEqual(len(sessions), 2)

    def test_list_sessions_by_user(self):
        self.agent.create_session(user_id="alice")
        self.agent.create_session(user_id="alice")
        self.agent.create_session(user_id="bob")
        sessions = self.agent.list_sessions(user_id="alice")
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(s["user_id"] == "alice" for s in sessions))


class TestChatAgentFallback(unittest.TestCase):
    """Test fallback responses when no API key is set."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = None  # Force fallback mode

    def test_fallback_greeting(self):
        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "Hello!")
        self.assertIn("SintraPrime", response)

    def test_fallback_help(self):
        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "What can you do?")
        self.assertIn("help", response.lower())

    def test_fallback_status(self):
        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "What is your status?")
        self.assertIn("online", response.lower())

    def test_fallback_unknown(self):
        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "xyzzy frobble")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_chat_adds_messages_to_history(self):
        session = self.agent.create_session()
        self.agent.chat(session.session_id, "Hello")
        self.assertEqual(len(session.messages), 2)  # user + assistant
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[1].role, "assistant")

    def test_chat_invalid_session_raises(self):
        with self.assertRaises(ValueError):
            self.agent.chat("nonexistent-session", "Hello")


class TestChatAgentWithLLM(unittest.TestCase):
    """Test ChatAgent with mocked LLM calls."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = "test-key"

    def _mock_openai_response(self, content: str):
        """Create a mock OpenAI response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage.total_tokens = 100
        return mock_response

    @patch("openai.OpenAI")
    def test_chat_with_llm(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            "I can help you with that legal matter."
        )

        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "Help me with a contract dispute")
        self.assertEqual(response, "I can help you with that legal matter.")
        self.assertEqual(session.token_count, 100)

    @patch("openai.OpenAI")
    def test_chat_llm_error_returns_error_message(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        session = self.agent.create_session()
        response = self.agent.chat(session.session_id, "Hello")
        self.assertIn("error", response.lower())

    @patch("openai.OpenAI")
    def test_god_mode_system_prompt_includes_god_mode(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._mock_openai_response("Done.")

        session = self.agent.create_session(mode=AgentMode.GOD_MODE.value)
        self.agent.chat(session.session_id, "Execute the task")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_msg = messages[0]["content"]
        self.assertIn("GOD MODE", system_msg)

    @patch("openai.OpenAI")
    def test_autonomous_mode_system_prompt(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._mock_openai_response("Done.")

        session = self.agent.create_session(mode=AgentMode.AUTONOMOUS.value)
        self.agent.chat(session.session_id, "Do something")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_msg = messages[0]["content"]
        self.assertIn("AUTONOMOUS MODE", system_msg)


class TestChatAgentTaskExecution(unittest.TestCase):
    """Test autonomous task execution."""

    def setUp(self):
        self.agent = ChatAgent()

    def test_execute_task_autonomously(self):
        session = self.agent.create_session()
        task = self.agent.execute_task_autonomously(
            session.session_id,
            task_type="run_tests",
            task_params={"test_path": "agents/"},
        )
        self.assertIsNotNone(task)
        self.assertEqual(task.task_type, "run_tests")
        self.assertIn(task.task_id, self.agent._tasks)

    def test_execute_task_with_approval_required(self):
        session = self.agent.create_session()
        task = self.agent.execute_task_autonomously(
            session.session_id,
            task_type="deploy",
            task_params={},
            require_approval=True,
        )
        self.assertEqual(task.status, TaskStatus.AWAITING_APPROVAL.value)
        self.assertFalse(task.approved)

    def test_approve_task(self):
        session = self.agent.create_session()
        task = self.agent.execute_task_autonomously(
            session.session_id,
            task_type="run_tests",
            task_params={},
            require_approval=True,
        )
        approved = self.agent.approve_task(task.task_id)
        self.assertTrue(approved.approved)
        self.assertEqual(approved.status, TaskStatus.PENDING.value)

    def test_approve_nonexistent_task(self):
        result = self.agent.approve_task("nonexistent-task-id")
        self.assertIsNone(result)

    def test_get_task_status(self):
        session = self.agent.create_session()
        task = self.agent.execute_task_autonomously(
            session.session_id,
            task_type="run_tests",
            task_params={},
        )
        retrieved = self.agent.get_task_status(task.task_id)
        self.assertEqual(retrieved.task_id, task.task_id)

    def test_list_tasks(self):
        session = self.agent.create_session()
        self.agent.execute_task_autonomously(session.session_id, "run_tests", {})
        self.agent.execute_task_autonomously(session.session_id, "draft_document", {})
        tasks = self.agent.list_tasks()
        self.assertEqual(len(tasks), 2)

    def test_list_tasks_by_status(self):
        session = self.agent.create_session()
        self.agent.execute_task_autonomously(
            session.session_id, "run_tests", {}, require_approval=True
        )
        awaiting = self.agent.list_tasks(status=TaskStatus.AWAITING_APPROVAL.value)
        self.assertEqual(len(awaiting), 1)

    def test_unknown_task_type_fails(self):
        session = self.agent.create_session()
        task = self.agent.execute_task_autonomously(
            session.session_id,
            task_type="nonexistent_task",
            task_params={},
        )
        self.assertEqual(task.status, TaskStatus.FAILED.value)
        self.assertIn("No handler", task.error)


class TestChatAgentTools(unittest.TestCase):
    """Test built-in tool handlers."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = None  # No LLM for tool tests

    def test_tool_search_legal(self):
        result = self.agent._tool_search_legal({"query": "antitrust law"})
        self.assertIn("antitrust law", result)

    def test_tool_crm_lookup(self):
        result = self.agent._tool_crm_lookup({"name": "John Doe"})
        self.assertIn("John Doe", result)

    def test_tool_run_tests(self):
        result = self.agent._tool_run_tests({})
        self.assertIn("Zero Agent", result)

    def test_tool_schedule_reminder(self):
        result = self.agent._tool_schedule_reminder({"message": "File motion by Friday"})
        self.assertIn("File motion by Friday", result)

    def test_tool_summarize_file_no_path(self):
        result = self.agent._tool_summarize_file({})
        self.assertIn("No file path", result)

    def test_tool_summarize_file_not_found(self):
        result = self.agent._tool_summarize_file({"file_path": "/nonexistent/file.txt"})
        self.assertIn("not found", result.lower())

    def test_tool_summarize_existing_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document about legal matters.")
            tmp_path = f.name
        try:
            result = self.agent._tool_summarize_file({"file_path": tmp_path})
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        finally:
            os.unlink(tmp_path)

    def test_register_custom_tool(self):
        def my_tool(params):
            return "custom result"
        self.agent.register_tool("my_custom_tool", my_tool)
        self.assertIn("my_custom_tool", self.agent._tool_handlers)
        result = self.agent._tool_handlers["my_custom_tool"]({})
        self.assertEqual(result, "custom result")


class TestChatAgentAttachments(unittest.TestCase):
    """Test file attachment processing."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = None

    def test_process_text_attachment(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Contract terms: Party A agrees to pay Party B $5,000.")
            tmp_path = f.name
        try:
            result = self.agent._process_attachments([tmp_path])
            self.assertIn("Contract terms", result)
        finally:
            os.unlink(tmp_path)

    def test_process_nonexistent_attachment(self):
        result = self.agent._process_attachments(["/nonexistent/file.pdf"])
        self.assertIn("not found", result.lower())

    def test_process_url_attachment(self):
        result = self.agent._process_attachments(["https://example.com/doc.pdf"])
        self.assertIn("URL", result)

    def test_chat_with_attachment(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document.")
            tmp_path = f.name
        try:
            session = self.agent.create_session()
            response = self.agent.chat(
                session.session_id,
                "Summarize this document",
                attachments=[tmp_path],
            )
            self.assertIsInstance(response, str)
            # The user message should include the attachment content
            user_msg = session.messages[0].content
            self.assertIn("This is a test document", user_msg)
        finally:
            os.unlink(tmp_path)


class TestChatAgentIntentDetection(unittest.TestCase):
    """Test autonomous task intent detection."""

    def setUp(self):
        self.agent = ChatAgent()

    def test_detect_run_tests_intent(self):
        session = self.agent.create_session()
        intent = self.agent._detect_task_intent("Please run the tests", session)
        self.assertEqual(intent, "run_tests")

    def test_detect_draft_document_intent(self):
        session = self.agent.create_session()
        intent = self.agent._detect_task_intent("Draft a demand letter for me", session)
        self.assertEqual(intent, "draft_document")

    def test_detect_crm_intent(self):
        session = self.agent.create_session()
        intent = self.agent._detect_task_intent("Add a new client to the system", session)
        self.assertEqual(intent, "crm_create_contact")

    def test_detect_reminder_intent(self):
        session = self.agent.create_session()
        intent = self.agent._detect_task_intent("Remind me to file the motion tomorrow", session)
        self.assertEqual(intent, "schedule_reminder")

    def test_detect_no_intent(self):
        session = self.agent.create_session()
        intent = self.agent._detect_task_intent("What is the weather like?", session)
        self.assertIsNone(intent)


class TestChatAgentStats(unittest.TestCase):
    """Test agent statistics."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = None

    def test_get_stats_empty(self):
        stats = self.agent.get_stats()
        self.assertEqual(stats["total_sessions"], 0)
        self.assertEqual(stats["total_messages"], 0)
        self.assertEqual(stats["total_tasks"], 0)
        self.assertEqual(stats["model"], "gpt-4o-mini")

    def test_get_stats_with_sessions(self):
        session = self.agent.create_session()
        self.agent.chat(session.session_id, "Hello")
        stats = self.agent.get_stats()
        self.assertEqual(stats["total_sessions"], 1)
        self.assertEqual(stats["total_messages"], 2)  # user + assistant

    def test_get_stats_with_tasks(self):
        session = self.agent.create_session()
        self.agent.execute_task_autonomously(session.session_id, "run_tests", {})
        stats = self.agent.get_stats()
        self.assertEqual(stats["total_tasks"], 1)

    def test_registered_tools_in_stats(self):
        stats = self.agent.get_stats()
        self.assertIn("registered_tools", stats)
        self.assertIn("run_tests", stats["registered_tools"])


class TestChatAgentPersistence(unittest.TestCase):
    """Test session persistence."""

    def setUp(self):
        self.agent = ChatAgent()
        self.agent._openai_key = None

    def test_save_sessions(self):
        session = self.agent.create_session(user_id="alice")
        self.agent.chat(session.session_id, "Hello")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            count = self.agent.save_sessions(tmp_path)
            self.assertEqual(count, 1)
            with open(tmp_path) as f:
                data = json.load(f)
            self.assertIn(session.session_id, data)
        finally:
            os.unlink(tmp_path)

    def test_save_sessions_no_path(self):
        count = self.agent.save_sessions()
        self.assertEqual(count, 0)


class TestSystemPrompt(unittest.TestCase):
    """Test the system prompt content."""

    def test_system_prompt_not_empty(self):
        self.assertGreater(len(SINTRA_SYSTEM_PROMPT), 100)

    def test_system_prompt_mentions_agents(self):
        self.assertIn("Zero Agent", SINTRA_SYSTEM_PROMPT)
        self.assertIn("Sigma Agent", SINTRA_SYSTEM_PROMPT)
        self.assertIn("Nova Agent", SINTRA_SYSTEM_PROMPT)

    def test_system_prompt_mentions_crm(self):
        self.assertIn("CRM", SINTRA_SYSTEM_PROMPT)

    def test_system_prompt_mentions_legal(self):
        self.assertIn("legal", SINTRA_SYSTEM_PROMPT.lower())


if __name__ == "__main__":
    unittest.main()
