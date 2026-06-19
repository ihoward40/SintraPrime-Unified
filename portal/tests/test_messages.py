"""
Tests for Portal Message Persistence.
Covers: CRUD operations, validation, encryption round-trip, idempotency, duplicate prevention.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.message import Message, MessageAttachment, MessageThread
from portal.routers.messages import send_message, list_messages, create_thread, get_thread
from portal.schemas.message import MessageSend, ThreadCreate


class TestMessageModel:
    """Test Message ORM model fields and defaults."""

    def test_message_thread_required_fields(self):
        thread = MessageThread(
            tenant_id=uuid.uuid4(),
            subject="Test Thread",
            category="general",
            participants=[str(uuid.uuid4())],
            created_by=uuid.uuid4(),
            is_encrypted=True,
            is_archived=False,
            is_pinned=False,
            message_count=0,
        )
        assert thread.subject == "Test Thread"
        assert thread.category == "general"
        assert thread.is_encrypted is True
        assert thread.message_count == 0
        assert thread.is_archived is False
        assert thread.is_pinned is False

    def test_message_required_fields(self):
        msg = Message(
            thread_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            content="encrypted_content",
            content_encrypted=True,
            encryption_iv="abc123",
            is_deleted=False,
            is_edited=False,
            mentions=[],
            read_by={},
        )
        assert msg.content == "encrypted_content"
        assert msg.content_encrypted is True
        assert msg.encryption_iv == "abc123"
        assert msg.is_deleted is False
        assert msg.is_edited is False
        assert msg.mentions == []
        assert msg.read_by == {}

    def test_message_optional_fields_defaults(self):
        msg = Message(
            thread_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            content="test",
            mentions=[],
            read_by={},
            is_deleted=False,
            is_edited=False,
        )
        assert msg.mentions == []
        assert msg.read_by == {}
        assert msg.is_deleted is False
        assert msg.is_edited is False
        assert msg.deleted_at is None
        assert msg.deleted_by is None
        assert msg.edited_at is None
        assert msg.reply_to_id is None


class TestMessageSchemaValidation:
    """Test Pydantic schema validation."""

    def test_thread_create_valid(self):
        data = {
            "subject": "Legal Discussion",
            "category": "case_discussion",
            "participant_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        }
        thread = ThreadCreate(**data)
        assert thread.subject == "Legal Discussion"
        assert thread.category == "case_discussion"
        assert len(thread.participant_ids) == 2

    def test_thread_create_invalid_category(self):
        with pytest.raises(ValueError):
            ThreadCreate(
                subject="Test",
                category="invalid_category",
                participant_ids=[str(uuid.uuid4())],
            )

    def test_thread_create_empty_participants_fails(self):
        with pytest.raises(ValueError):
            ThreadCreate(
                subject="Test",
                participant_ids=[],
            )

    def test_message_send_valid(self):
        data = {
            "content": "Hello, this is a test message",
            "mentions": [str(uuid.uuid4())],
            "reply_to_id": str(uuid.uuid4()),
            "idempotency_key": "idem-123",
        }
        msg = MessageSend(**data)
        assert msg.content == "Hello, this is a test message"
        assert msg.idempotency_key == "idem-123"

    def test_message_send_empty_content_fails(self):
        with pytest.raises(ValueError):
            MessageSend(content="")

    def test_message_send_content_too_long_fails(self):
        with pytest.raises(ValueError):
            MessageSend(content="x" * 50001)

    def test_message_send_idempotency_key_too_long_fails(self):
        with pytest.raises(ValueError):
            MessageSend(content="test", idempotency_key="x" * 65)


class TestMessageCRUD:
    """Test message CRUD operations with mocked database."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def mock_current_user(self):
        user = MagicMock()
        user.user_id = uuid.uuid4()
        user.tenant_id = uuid.uuid4()
        return user

    @pytest.fixture
    def mock_thread(self, mock_current_user):
        thread = MagicMock(spec=MessageThread)
        thread.id = uuid.uuid4()
        thread.tenant_id = mock_current_user.tenant_id
        thread.subject = "Test Thread"
        thread.category = "general"
        thread.participants = [str(mock_current_user.user_id), str(uuid.uuid4())]
        thread.message_count = 0
        thread.last_message_at = None
        thread.is_archived = False
        thread.is_pinned = False
        thread.is_encrypted = True
        thread.created_by = mock_current_user.user_id
        thread.created_at = datetime.now(UTC)
        thread.updated_at = datetime.now(UTC)
        thread.deleted_at = None
        thread.client_id = None
        thread.case_id = None
        thread.retention_days = None
        thread.purge_after = None
        return thread

    @pytest.fixture
    def mock_message(self, mock_current_user):
        msg = MagicMock(spec=Message)
        msg.id = uuid.uuid4()
        msg.thread_id = uuid.uuid4()
        msg.tenant_id = mock_current_user.tenant_id
        msg.sender_id = mock_current_user.user_id
        msg.content = "encrypted_content"
        msg.content_encrypted = True
        msg.encryption_iv = "aabbccddeeff001122334455"  # Valid 12-byte hex (24 chars)
        msg.mentions = []
        msg.is_edited = False
        msg.edited_at = None
        msg.is_deleted = False
        msg.deleted_at = None
        msg.deleted_by = None
        msg.reply_to_id = None
        msg.read_by = {}
        msg.attachments = []
        msg.created_at = datetime.now(UTC)
        msg.updated_at = datetime.now(UTC)
        return msg

    @pytest.mark.asyncio
    async def test_create_thread_success(self, mock_db, mock_current_user, mock_thread):
        with patch("portal.routers.messages.audit", new_callable=AsyncMock):
            with patch("portal.routers.messages.MessageThread", return_value=mock_thread) as mock_thread_class:
                thread_data = ThreadCreate(
                    subject="New Thread",
                    category="general",
                    participant_ids=[str(uuid.uuid4())],
                )
                result = await create_thread(thread_data, mock_current_user, mock_db)

                # Verify MessageThread was instantiated with correct args
                mock_thread_class.assert_called_once()
                call_kwargs = mock_thread_class.call_args[1]
                assert call_kwargs["subject"] == "New Thread"
                assert call_kwargs["category"] == "general"
                
                mock_db.add.assert_called()
                mock_db.commit.assert_awaited()
                mock_db.refresh.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_db, mock_current_user, mock_thread, mock_message):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_db.execute.return_value = mock_result

        with patch("portal.routers.messages.encrypt_text", return_value=("encrypted", b"iv123")):
            with patch("portal.routers.messages.Message", return_value=mock_message):
                with patch("portal.routers.messages.ws_manager.send_to_user", new_callable=AsyncMock):
                    with patch("portal.routers.messages.notify_users", new_callable=AsyncMock):
                        with patch("portal.routers.messages.audit", new_callable=AsyncMock):
                            msg_data = MessageSend(
                                content="Hello world",
                                idempotency_key="idem-test-1",
                            )
                            result = await send_message(mock_thread.id, msg_data, mock_current_user, mock_db)

                            assert result.content == "Hello world"
                            mock_db.add.assert_called()
                            mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_message_thread_not_found(self, mock_db, mock_current_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        msg_data = MessageSend(content="Hello")
        with pytest.raises(HTTPException) as exc:
            await send_message(uuid.uuid4(), msg_data, mock_current_user, mock_db)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message_not_participant(self, mock_db, mock_current_user):
        thread_id = uuid.uuid4()
        mock_thread = MagicMock()
        mock_thread.id = thread_id
        mock_thread.tenant_id = mock_current_user.tenant_id
        mock_thread.participants = [str(uuid.uuid4())]  # Different user
        mock_thread.subject = "Test Thread"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_db.execute.return_value = mock_result

        msg_data = MessageSend(content="Hello")
        with pytest.raises(HTTPException) as exc:
            await send_message(thread_id, msg_data, mock_current_user, mock_db)
        @pytest.mark.asyncio
        async def test_send_message_duplicate_idempotency_key(self, mock_db, mock_current_user, mock_thread):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_thread
            mock_db.execute.return_value = mock_result

            # Simulate IntegrityError on commit with the right error message
            integrity_error = IntegrityError(
                'duplicate key value violates unique constraint "ix_messages_idempotency_key"',
                "params",
                None,
            )
            mock_db.commit.side_effect = integrity_error

            with patch("portal.routers.messages.encrypt_text", return_value=("encrypted", b"iv123")):
                with patch("portal.routers.messages.Message"):
                    msg_data = MessageSend(content="Hello", idempotency_key="duplicate-key")
                    with pytest.raises(HTTPException) as exc:
                        await send_message(mock_thread.id, msg_data, mock_current_user, mock_db)
                    assert exc.value.status_code == 409
                    assert "idempotency key already exists" in exc.value.detail

    @pytest.mark.asyncio
    async def test_list_messages_success(self, mock_db, mock_current_user, mock_thread, mock_message):
        thread_id = mock_thread.id
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = mock_thread

        msg_result = MagicMock()
        msg_result.scalars.return_value.all.return_value = [mock_message]

        count_result = MagicMock()
        count_result.scalar.return_value = 1

        mock_db.execute.side_effect = [thread_result, count_result, msg_result]

        # Patch the function where it's used (router module)
        import portal.routers.messages as router_module
        with patch.object(router_module, 'decrypt_text', return_value="decrypted content") as mock_decrypt:
            result = await list_messages(thread_id, None, 1, 50, mock_current_user, mock_db)

            assert result.total == 1
            assert len(result.items) == 1
            assert result.items[0].content == "decrypted content"
            mock_decrypt.assert_called_once_with("encrypted_content", bytes.fromhex("aabbccddeeff001122334455"))

    @pytest.mark.asyncio
    async def test_list_messages_not_participant(self, mock_db, mock_current_user):
        thread_id = uuid.uuid4()
        mock_thread = MagicMock()
        mock_thread.id = thread_id
        mock_thread.participants = [str(uuid.uuid4())]  # Different user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await list_messages(thread_id, None, 1, 50, mock_current_user, mock_db)
        assert exc.value.status_code == 403


class TestEncryptionRoundTrip:
    """Test encryption/decryption round-trip for messages."""

    def test_encrypt_decrypt_text(self):
        from portal.services.encryption_service import encrypt_text, decrypt_text

        plaintext = "This is a secret legal message"
        ciphertext_b64, nonce = encrypt_text(plaintext)
        decrypted = decrypt_text(ciphertext_b64, nonce)
        assert decrypted == plaintext

    def test_encrypt_decrypt_empty_string(self):
        from portal.services.encryption_service import encrypt_text, decrypt_text

        plaintext = ""
        ciphertext_b64, nonce = encrypt_text(plaintext)
        decrypted = decrypt_text(ciphertext_b64, nonce)
        assert decrypted == plaintext

    def test_encrypt_decrypt_unicode(self):
        from portal.services.encryption_service import encrypt_text, decrypt_text

        plaintext = "Legal terms: §123, €5000, 日本語"
        ciphertext_b64, nonce = encrypt_text(plaintext)
        decrypted = decrypt_text(ciphertext_b64, nonce)
        assert decrypted == plaintext


class TestMessageIdempotency:
    """Test idempotency key behavior."""

    def test_idempotency_key_optional_in_schema(self):
        msg = MessageSend(content="test")
        assert msg.idempotency_key is None

    def test_idempotency_key_accepted(self):
        msg = MessageSend(content="test", idempotency_key="my-unique-key-123")
        assert msg.idempotency_key == "my-unique-key-123"

    def test_idempotency_key_max_length(self):
        msg = MessageSend(content="test", idempotency_key="x" * 64)
        assert len(msg.idempotency_key) == 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])