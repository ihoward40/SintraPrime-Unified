"""FastAPI voice interface for SintraPrime voice system.

Provides REST and WebSocket endpoints for voice processing:
- Transcription
- Text-to-speech synthesis
- Real-time voice streaming
- Session management
"""

import logging
import asyncio
import base64
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, WebSocket, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
import jwt

from .local_voice import (
    DubbingJob,
    DubbingSegment,
    LocalVoicePipeline,
    ModelNotAvailableError,
    VoiceDesignSpec,
    VoiceProfileNotFoundError,
    VoiceSample,
    create_local_voice_pipeline,
)

logger = logging.getLogger(__name__)


# ==================== Dependencies ====================

async def verify_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """Verify JWT token.
    
    Args:
        authorization: Bearer token
        
    Returns:
        Token payload
        
    Raises:
        HTTPException if token invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid scheme")

        # Mock JWT verification - in production use real verification
        payload = {
            "sub": "user123",
            "scope": "voice:full",
        }
        return payload

    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== Request/Response Models ====================

class TranscribeRequest:
    """Transcription request (would use Pydantic model in production)."""
    def __init__(self, audio_format: str = "wav"):
        self.audio_format = audio_format


class SynthesizeRequest:
    """Text-to-speech request."""
    def __init__(self, text: str, voice_id: str = "default", language: str = "en"):
        self.text = text
        self.voice_id = voice_id
        self.language = language


class VoiceQueryRequest:
    """Full voice query request."""
    def __init__(self, text: str, context: Optional[Dict] = None):
        self.text = text
        self.context = context or {}


# ==================== Session Storage ====================

class SessionStore:
    """In-memory session storage (use Redis in production)."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def create_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Create new session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Session data
        """
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "messages": [],
            "metadata": {},
        }
        self.sessions[session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, data: Dict) -> bool:
        """Update session data.
        
        Args:
            session_id: Session ID
            data: Data to merge
            
        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id].update(data)
        self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def list_sessions(self, user_id: str) -> List[Dict]:
        """List user's sessions.
        
        Args:
            user_id: User ID
            
        Returns:
            List of sessions
        """
        return [s for s in self.sessions.values() if s.get("user_id") == user_id]


# ==================== Rate Limiter ====================

class RateLimiter:
    """Simple rate limiter for voice endpoints."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    async def check_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit.
        
        Args:
            user_id: User ID
            
        Returns:
            True if within limit
        """
        now = datetime.now().timestamp()
        
        if user_id not in self.requests:
            self.requests[user_id] = []

        # Remove old requests outside window
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if now - t < self.window_seconds
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            return False

        self.requests[user_id].append(now)
        return True


# ==================== Voice API Router ====================

class VoiceAPIRouter:
    """FastAPI router for voice endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/voice", tags=["voice"])
        self.session_store = SessionStore()
        self.rate_limiter = RateLimiter()
        self.local_pipeline: LocalVoicePipeline = create_local_voice_pipeline()
        self._register_routes()

    def _register_routes(self):
        """Register all voice endpoints."""
        self.router.post("/transcribe")(self.transcribe)
        self.router.post("/synthesize")(self.synthesize)
        self.router.post("/query")(self.voice_query)
        self.router.get("/session/{session_id}")(self.get_session)
        self.router.post("/session/new")(self.create_session)
        self.router.delete("/session/{session_id}")(self.delete_session)
        self.router.websocket("/stream")(self.websocket_stream)
        # Local voice pipeline routes (fully on-device)
        self.router.get("/local/voices")(self.local_list_voices)
        self.router.post("/local/enroll")(self.local_enroll)
        self.router.post("/local/synthesize")(self.local_synthesize)
        self.router.post("/local/transcribe")(self.local_transcribe)
        self.router.post("/local/dictation/start")(self.local_dictation_start)
        self.router.post("/local/dictation/stop")(self.local_dictation_stop)
        self.router.post("/local/dubbing/plan")(self.local_dubbing_plan)

    # ==================== Endpoints ====================

    async def transcribe(
        self,
        file: UploadFile = File(...),
        language: str = "en",
        token_data: Dict = Depends(verify_token),
    ):
        """Transcribe audio file to text.
        
        POST /voice/transcribe
        
        Request:
            - file: Audio file (WAV, MP3, OGG, WebM)
            - language: Language code (en, es, fr, etc.)
            
        Response:
            {
                "text": "transcribed text",
                "confidence": 0.95,
                "language": "en",
                "duration_seconds": 5.5,
                "provider": "openai_whisper"
            }
        """
        user_id = token_data.get("sub")

        # Check rate limit
        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            # Read audio file
            audio_data = await file.read()

            # Mock transcription - integrate with actual speech processor
            return {
                "text": f"Transcribed audio from {file.filename}",
                "confidence": 0.92,
                "language": language,
                "duration_seconds": len(audio_data) / 32000,  # Rough estimate
                "provider": "openai_whisper",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def synthesize(
        self,
        request: Dict,
        voice_id: str = "senior-partner",
        token_data: Dict = Depends(verify_token),
    ):
        """Synthesize text to speech audio.
        
        POST /voice/synthesize
        
        Request:
            {
                "text": "text to synthesize",
                "voice_id": "senior-partner",
                "speaking_rate": 0.95
            }
            
        Response:
            Audio stream (audio/wav)
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            text = request.get("text", "")
            
            if not text:
                raise HTTPException(status_code=400, detail="Missing text")

            # Mock synthesis - integrate with actual speech processor
            # In production, would call ElevenLabs, AWS Polly, etc.
            audio_data = b"RIFF" + b"\x00" * 100  # Mock WAV header

            return StreamingResponse(
                iter([audio_data]),
                media_type="audio/wav",
                headers={"Content-Disposition": "attachment; filename=speech.wav"}
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def voice_query(
        self,
        request: Dict,
        session_id: Optional[str] = None,
        token_data: Dict = Depends(verify_token),
    ):
        """Full voice query pipeline: audio → transcription → processing → response.
        
        POST /voice/query
        
        Request:
            {
                "text": "user input",
                "session_id": "uuid",
                "context": {}
            }
            
        Response:
            {
                "transcription": "what user said",
                "intent": "draft_complaint",
                "response": "legal response",
                "audio_url": "/voice/audio/xyz",
                "entities": [],
                "complexity": 7.5
            }
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            text = request.get("text", "")
            session_id = request.get("session_id") or session_id
            context = request.get("context", {})

            if not text:
                raise HTTPException(status_code=400, detail="Missing text")

            # Ensure session exists
            if session_id:
                session = await self.session_store.get_session(session_id)
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
            else:
                raise HTTPException(status_code=400, detail="Session ID required")

            # Mock full pipeline
            response = {
                "transcription": text,
                "intent": "general_inquiry",
                "intent_confidence": 0.82,
                "practice_area": "general",
                "complexity_score": 5.5,
                "urgency_level": "normal",
                "response": f"Mock response to: {text}",
                "entities": [],
                "action_items": [],
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }

            # Update session
            await self.session_store.update_session(
                session_id,
                {"last_message": response}
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Voice query error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session(
        self,
        session_id: str,
        token_data: Dict = Depends(verify_token),
    ):
        """Get session details and history.
        
        GET /voice/session/{session_id}
        
        Response:
            {
                "session_id": "uuid",
                "created_at": "2024-01-01T00:00:00",
                "messages": [],
                "metadata": {}
            }
        """
        session = await self.session_store.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify ownership
        if session.get("user_id") != token_data.get("sub"):
            raise HTTPException(status_code=403, detail="Unauthorized")

        return session

    async def create_session(
        self,
        request: Optional[Dict] = None,
        token_data: Dict = Depends(verify_token),
    ):
        """Create new voice session.
        
        POST /voice/session/new
        
        Request (optional):
            {
                "client_name": "Jane Doe",
                "matter_number": "2024-001",
                "practice_area": "family"
            }
            
        Response:
            {
                "session_id": "uuid",
                "created_at": "2024-01-01T00:00:00"
            }
        """
        import uuid
        
        user_id = token_data.get("sub")
        session_id = str(uuid.uuid4())
        metadata = (request or {}).get("metadata", {})

        session = await self.session_store.create_session(session_id, user_id)
        session["metadata"] = metadata

        logger.info(f"Created session {session_id} for user {user_id}")

        return {
            "session_id": session_id,
            "created_at": session["created_at"],
        }

    async def delete_session(
        self,
        session_id: str,
        token_data: Dict = Depends(verify_token),
    ):
        """Delete session.
        
        DELETE /voice/session/{session_id}
        """
        session = await self.session_store.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify ownership
        if session.get("user_id") != token_data.get("sub"):
            raise HTTPException(status_code=403, detail="Unauthorized")

        success = await self.session_store.delete_session(session_id)

        if success:
            logger.info(f"Deleted session {session_id}")
            return {"status": "deleted"}

        raise HTTPException(status_code=500, detail="Failed to delete session")

    async def websocket_stream(self, websocket: WebSocket):
        """WebSocket for real-time bidirectional voice streaming.
        
        WS /voice/stream
        
        Client can send:
            - Audio chunks as binary frames
            - Control messages as JSON
            
        Server sends:
            - Transcription results
            - Response audio
            - Session events
        """
        await websocket.accept()
        logger.info("WebSocket connection established")

        try:
            while True:
                # Receive data from client
                data = await websocket.receive()

                if "bytes" in data:
                    # Audio chunk
                    audio_chunk = data["bytes"]
                    logger.debug(f"Received audio chunk: {len(audio_chunk)} bytes")

                    # Mock transcription
                    transcription = "Mock transcription of audio"

                    # Send back transcription
                    await websocket.send_json({
                        "type": "transcription",
                        "text": transcription,
                        "confidence": 0.89,
                    })

                elif "text" in data:
                    # Control message
                    message = json.loads(data["text"])

                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif message.get("type") == "start_session":
                        session_id = message.get("session_id")
                        await websocket.send_json({
                            "type": "session_started",
                            "session_id": session_id,
                        })

                    elif message.get("type") == "end_session":
                        logger.info("Client ended session")
                        await websocket.send_json({"type": "session_ended"})
                        break

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await websocket.close()
            logger.info("WebSocket connection closed")

    # ==================== Local Voice Endpoints ====================

    async def local_list_voices(
        self,
        token_data: Dict = Depends(verify_token),
    ):
        """List enrolled local voice profiles.

        GET /voice/local/voices
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        return {
            "voices": [
                {
                    "voice_id": p.voice_id,
                    "display_name": p.display_name,
                    "language": p.language,
                    "sample_count": p.sample_count,
                    "total_sample_seconds": p.total_sample_seconds,
                    "created_at": p.created_at,
                    "backend": p.backend_name,
                    "designed": p.design is not None,
                }
                for p in self.local_pipeline.registry.list()
            ]
        }

    async def local_enroll(
        self,
        request: Dict,
        token_data: Dict = Depends(verify_token),
    ):
        """Enroll a local voice profile from audio samples and/or a design.

        POST /voice/local/enroll

        Request:
            {
                "display_name": "Narrator",
                "language": "en",
                "design": {"name": "boardroom", "pitch_shift": 1.5},
                "samples": [
                    {"label": "sample-1", "audio_base64": "...", "sample_rate": 16000}
                ]
            }
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            display_name = (request or {}).get("display_name", "")
            if not display_name:
                raise HTTPException(status_code=400, detail="Missing display_name")

            samples = []
            for s in (request or {}).get("samples", []):
                samples.append(VoiceSample(
                    label=s.get("label", "sample"),
                    audio_bytes=base64.b64decode(s.get("audio_base64", "")),
                    sample_rate=s.get("sample_rate", 16000),
                    channels=s.get("channels", 1),
                ))

            design = None
            design_data = (request or {}).get("design")
            if design_data:
                design = VoiceDesignSpec(**design_data)

            profile = await self.local_pipeline.enroll(
                display_name,
                samples,
                language=(request or {}).get("language", "en"),
                design=design,
            )
            return {
                "voice_id": profile.voice_id,
                "display_name": profile.display_name,
                "language": profile.language,
                "sample_count": profile.sample_count,
                "total_sample_seconds": profile.total_sample_seconds,
                "created_at": profile.created_at,
                "backend": profile.backend_name,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Local enrollment error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    async def local_synthesize(
        self,
        request: Dict,
        token_data: Dict = Depends(verify_token),
    ):
        """Synthesize text with an enrolled local voice.

        POST /voice/local/synthesize

        Request:
            {"text": "text to synthesize", "voice_id": "local-abc123"}
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            text = (request or {}).get("text", "")
            voice_id = (request or {}).get("voice_id", "")
            if not text:
                raise HTTPException(status_code=400, detail="Missing text")
            if not voice_id:
                raise HTTPException(status_code=400, detail="Missing voice_id")

            result = await self.local_pipeline.synthesize(text, voice_id)
            return StreamingResponse(
                iter([result.audio_bytes]),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=local-speech.wav",
                    "X-Voice-Placeholder": str(result.is_placeholder).lower(),
                    "X-Voice-Backend": result.backend,
                },
            )

        except HTTPException:
            raise
        except VoiceProfileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Local synthesis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def local_transcribe(
        self,
        file: UploadFile = File(...),
        language: str = "en",
        token_data: Dict = Depends(verify_token),
    ):
        """Transcribe audio with the local pipeline.

        POST /voice/local/transcribe

        Returns 501 when no local transcription model is wired.
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            audio_data = await file.read()
            result = await self.local_pipeline.transcribe(audio_data, language)
            return {
                "text": result.text,
                "confidence": result.confidence,
                "language": result.language,
                "is_partial": result.is_partial,
                "backend": result.backend,
                "timestamp": datetime.now().isoformat(),
            }

        except ModelNotAvailableError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except Exception as e:
            logger.error(f"Local transcription error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def local_dictation_start(
        self,
        request: Optional[Dict] = None,
        token_data: Dict = Depends(verify_token),
    ):
        """Start a local dictation session.

        POST /voice/local/dictation/start

        Request (optional):
            {"user_id": "user123", "language": "en"}
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            session_id = await self.local_pipeline.dictation.start_session(
                user_id=(request or {}).get("user_id", user_id),
                language=(request or {}).get("language", "en"),
            )
            return {"session_id": session_id}

        except ModelNotAvailableError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except Exception as e:
            logger.error(f"Local dictation start error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def local_dictation_stop(
        self,
        request: Dict,
        token_data: Dict = Depends(verify_token),
    ):
        """Stop a local dictation session and return the transcript summary.

        POST /voice/local/dictation/stop

        Request:
            {"session_id": "dict-abc123"}
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            session_id = (request or {}).get("session_id", "")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id")
            return await self.local_pipeline.dictation.stop_session(session_id)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Local dictation stop error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    async def local_dubbing_plan(
        self,
        request: Dict,
        token_data: Dict = Depends(verify_token),
    ):
        """Build a dubbing render plan from a job spec.

        POST /voice/local/dubbing/plan

        Request:
            {
                "source_audio_seconds": 60.0,
                "target_voice_id": "local-abc123",
                "language": "en",
                "segments": [
                    {"index": 0, "start_seconds": 0.0, "end_seconds": 10.0,
                     "source_text": "Hello", "target_text": "Hola"}
                ]
            }
        """
        user_id = token_data.get("sub")

        if not await self.rate_limiter.check_limit(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            job = DubbingJob(
                source_audio_seconds=float((request or {}).get("source_audio_seconds", 0)),
                target_voice_id=(request or {}).get("target_voice_id", ""),
                language=(request or {}).get("language", "en"),
                segments=[
                    DubbingSegment(
                        index=s.get("index", i),
                        start_seconds=float(s.get("start_seconds", 0)),
                        end_seconds=float(s.get("end_seconds", 0)),
                        source_text=s.get("source_text", ""),
                        target_text=s.get("target_text"),
                    )
                    for i, s in enumerate((request or {}).get("segments", []))
                ],
            )
            plan = self.local_pipeline.plan_dubbing(job)
            return {
                "job_id": plan.job_id,
                "target_voice_id": plan.target_voice_id,
                "source_audio_seconds": plan.source_audio_seconds,
                "segment_count": plan.segment_count,
                "planned_segments": plan.planned_segments,
                "estimated_render_seconds": plan.estimated_render_seconds,
                "steps": plan.steps,
            }

        except (VoiceProfileNotFoundError, Exception) as e:
            status = 404 if isinstance(e, VoiceProfileNotFoundError) else 400
            logger.error(f"Local dubbing plan error: {e}")
            raise HTTPException(status_code=status, detail=str(e))

    # ==================== Helper Methods ====================

    async def get_router(self) -> APIRouter:
        """Get configured FastAPI router."""
        return self.router


# ==================== Factory ====================

def create_voice_api_router() -> APIRouter:
    """Create and return configured voice API router.
    
    Returns:
        FastAPI APIRouter with all voice endpoints
    """
    voice_router = VoiceAPIRouter()
    return voice_router.router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
