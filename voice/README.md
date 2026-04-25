# SintraPrime AI Voice Interface

## Overview

The SintraPrime Voice Interface gives the platform a conversational "Senior Partner" persona that users can speak to and receive structured legal and financial guidance with professional voice output.

Users can:
- Speak natural language queries about legal and financial matters
- Receive responses in the voice of an experienced senior attorney
- Get structured analysis with complexity scoring and urgency detection
- Enjoy natural language responses formatted for voice delivery

### Key Features

- 🎤 **Voice Recognition**: OpenAI Whisper (primary) + Google Speech-to-Text (fallback)
- 🔊 **Voice Synthesis**: ElevenLabs (primary) + AWS Polly (fallback) + pyttsx3 (offline)
- 🧠 **Intelligent Intent Classification**: 25+ legal intents with confidence scoring
- 👥 **Senior Partner Persona**: 30 years experience, domain-aware, empathetic guidance
- 📍 **Named Entity Extraction**: Identifies people, dates, amounts, statutes, court names
- ⚖️ **Legal Domain Expertise**: Criminal, family, corporate, financial, estate planning
- 🚨 **Urgency Detection**: Identifies critical matters requiring immediate attention
- 🎯 **Escalation Logic**: Detects when human attorney consultation is needed
- 🎙️ **Wake Word Detection**: "Hey SintraPrime", "Counsel", "Advisor" with phonetic matching
- 🔄 **Real-Time Streaming**: WebSocket support for continuous conversation
- 📊 **Response Quality**: SSML formatting for natural prosody and emphasis

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Voice Input (Audio)                   │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Speech Processor   │ (Whisper/Google STT)
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  Wake Word Detector │ (Local)
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────┐
        │   Legal NLP Processor       │
        │ - Intent Classification     │
        │ - Entity Extraction         │
        │ - Complexity Scoring        │
        │ - Urgency Detection         │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │   Senior Partner Persona    │
        │ - Domain Expertise          │
        │ - Tone Calibration          │
        │ - Escalation Detection      │
        │ - Context Memory            │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │   Response Formatter        │
        │ - Markdown Removal          │
        │ - Citation Formatting       │
        │ - SSML Generation           │
        │ - Response Chunking         │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Speech Processor   │ (ElevenLabs/Polly TTS)
        └──────────┬──────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              Voice Output (Audio)                   │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### Requirements

- Python 3.8+
- FastAPI 0.95+
- numpy 1.21+
- pydantic 1.9+

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-openai-key"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
export GOOGLE_APPLICATION_CREDENTIALS="path-to-google-credentials.json"
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
```

### Quick Start

```python
import asyncio
from voice import VoiceEngine, SeniorPartnerPersona, LegalNLPProcessor

async def main():
    # Initialize components
    engine = VoiceEngine()
    persona = SeniorPartnerPersona()
    processor = LegalNLPProcessor()
    
    # Start voice engine
    await engine.start()
    
    # Process a voice query
    query = "I was arrested yesterday. What should I do?"
    nlp_result = processor.process(query)
    
    print(f"Intent: {nlp_result.intent.primary_intent}")
    print(f"Urgency: {nlp_result.urgency_level}")
    print(f"Complexity: {nlp_result.complexity_score}")
    
    # Check escalation
    should_escalate, reason = persona.should_escalate(
        nlp_result.complexity_score,
        nlp_result.intent.primary_intent
    )
    
    if should_escalate:
        print(f"ESCALATION: {reason}")
    
    await engine.stop()

asyncio.run(main())
```

---

## Voice Commands Reference

### Defense & Criminal Law

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Defense Advice | "I was arrested", "I'm facing charges", "I need a lawyer" | Legal advice for criminal defense |
| Explain Charges | "What are the charges?", "What does felony mean?" | Explanation of specific charges |
| Bail Bond | "Can I get bail?", "What about bail hearing?" | Information on bail proceedings |
| Plea Agreement | "Should I take the plea?", "What's plea bargaining?" | Guidance on plea options |
| Sentencing | "What's my likely sentence?", "How much prison?" | Sentencing information & ranges |

### Civil & Litigation

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Draft Complaint | "How do I sue?", "I want to file suit" | Filing procedures & requirements |
| Negotiate Settlement | "Should I settle?", "Is this offer fair?" | Settlement evaluation |
| Discovery Request | "What is discovery?", "Subpoena help" | Discovery process explanation |
| Deposition Prep | "Preparing for deposition", "What to expect?" | Deposition guidance |

### Contracts & Corporate

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Review Contract | "Review this contract", "What does this clause mean?" | Contract analysis |
| Corporate Setup | "How to incorporate?", "LLC or Corporation?" | Business entity formation |
| Merger Acquisition | "We're acquiring another firm", "What's involved?" | M&A process guidance |

### Family Law

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Divorce Guidance | "I'm getting divorced", "Filing for divorce" | Divorce process & requirements |
| Custody Determination | "How is custody decided?", "What is custody?" | Custody evaluation factors |
| Child Support | "What about child support?", "Support calculation" | Child support guidelines |

### Estate Planning

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Will Creation | "I need a will", "How do I create a will?" | Will drafting guidance |
| Trust Setup | "Should I have a trust?", "What's a living trust?" | Trust types & benefits |
| Probate Guidance | "What is probate?", "How does probate work?" | Probate process |
| Estate Tax Planning | "Estate taxes?", "Tax minimization" | Tax planning strategies |

### Financial Law

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Debt Management | "I have debt", "Debt consolidation" | Debt resolution strategies |
| Credit Repair | "Fix my credit", "Credit score issues" | Credit improvement guidance |
| Bankruptcy Options | "I'm considering bankruptcy", "Chapter 7 or 13?" | Bankruptcy guidance |

### General

| Intent | Example Phrases | Response |
|--------|-----------------|----------|
| Legal Research | "Look up", "Find the law on" | Legal research results |
| Statute Explanation | "What's Section 1983?", "Explain this statute" | Statute interpretation |
| Urgent Help | "HELP!", "Emergency!", "Court today!" | High-priority escalation |

---

## WebSocket Streaming Example

Real-time bidirectional voice conversation:

```python
import asyncio
import websockets
import json

async def voice_stream():
    """Connect to voice WebSocket and stream audio."""
    uri = "ws://localhost:8000/voice/stream"
    
    async with websockets.connect(uri) as websocket:
        # Start session
        await websocket.send(json.dumps({
            "type": "start_session",
            "session_id": "session-123"
        }))
        
        # Send audio chunk
        audio_chunk = b"audio data here"
        await websocket.send(audio_chunk)
        
        # Receive transcription
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Transcription: {data['text']}")
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Response: {data}")
        
        # End session
        await websocket.send(json.dumps({
            "type": "end_session"
        }))

asyncio.run(voice_stream())
```

---

## REST API Endpoints

### Transcription

**POST /voice/transcribe**

Transcribe audio file to text.

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@audio.wav" \
  -F "language=en" \
  http://localhost:8000/voice/transcribe
```

Response:
```json
{
  "text": "transcribed text",
  "confidence": 0.95,
  "language": "en",
  "duration_seconds": 5.5,
  "provider": "openai_whisper"
}
```

### Text-to-Speech

**POST /voice/synthesize**

Convert text to speech audio.

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your legal guidance here",
    "voice_id": "senior-partner",
    "speaking_rate": 0.95
  }' \
  http://localhost:8000/voice/synthesize \
  --output response.wav
```

### Voice Query (Full Pipeline)

**POST /voice/query**

Complete voice query: transcription → NLP → response → synthesis.

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I was arrested. What should I do?",
    "session_id": "session-123"
  }' \
  http://localhost:8000/voice/query
```

Response:
```json
{
  "transcription": "I was arrested. What should I do?",
  "intent": "defense_advice",
  "intent_confidence": 0.89,
  "practice_area": "criminal",
  "complexity_score": 7.5,
  "urgency_level": "critical",
  "response": "I understand this is urgent...",
  "entities": [],
  "action_items": [],
  "session_id": "session-123"
}
```

---

## Session Management

### Create Session

**POST /voice/session/new**

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "John Doe",
    "matter_number": "2024-001",
    "practice_area": "criminal"
  }' \
  http://localhost:8000/voice/session/new
```

### Get Session

**GET /voice/session/{session_id}**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/voice/session/session-123
```

### Delete Session

**DELETE /voice/session/{session_id}**

```bash
curl -X DELETE \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/voice/session/session-123
```

---

## Persona Customization

### Modify Senior Partner Persona

```python
from voice import SeniorPartnerPersona, PersonaConfig, LegalDomain

config = PersonaConfig(
    name="Counsel",
    years_experience=35,
    greeting_style="warm",
    specializations=[
        LegalDomain.CORPORATE,
        LegalDomain.MERGERS_ACQUISITIONS,
        LegalDomain.TRUSTS_ESTATES,
    ],
    enable_quotes=True,
    empathy_calibration=0.9,  # Higher = more empathetic
)

persona = SeniorPartnerPersona(config)
```

### Configure Speech

```python
from voice import SpeechConfig, SpeechProvider

config = SpeechConfig(
    stt_primary_provider=SpeechProvider.OPENAI_WHISPER,
    tts_primary_provider=SpeechProvider.ELEVENLABS,
    confidence_threshold=0.8,
    enable_noise_reduction=True,
)
```

### Configure Voice Engine

```python
from voice import VoiceEngine, VoiceConfig

config = VoiceConfig(
    sample_rate=16000,
    enable_noise_reduction=True,
    confidence_threshold=0.7,
    wake_words=["hey sintraPrime", "counsel", "advisor"],
    max_silence_duration=2.0,
)

engine = VoiceEngine(config)
```

---

## Event Handling

Register handlers for voice events:

```python
from voice import EventType

async def on_transcription_complete(event):
    print(f"Transcribed: {event.data['text']}")

async def on_error(event):
    print(f"Error: {event.data['error']}")

engine.register_event_handler(EventType.TRANSCRIPTION_COMPLETE, on_transcription_complete)
engine.register_event_handler(EventType.ERROR_OCCURRED, on_error)
```

---

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest voice/tests/test_voice.py -v

# Run specific test class
pytest voice/tests/test_voice.py::TestIntentClassification -v

# Run with coverage
pytest voice/tests/test_voice.py --cov=voice --cov-report=html
```

### Test Coverage

- ✅ 50+ unit tests
- ✅ Persona greeting generation (7 tests)
- ✅ Intent classification (11+ tests covering all major intents)
- ✅ Entity extraction (6 tests)
- ✅ Complexity scoring (5 tests)
- ✅ Urgency detection (4 tests)
- ✅ Practice area classification (6 tests)
- ✅ Response formatting (7 tests)
- ✅ Wake word detection (7 tests)
- ✅ Integration tests (4 tests)
- ✅ Configuration tests (4 tests)
- ✅ Edge case tests (6 tests)

---

## Performance Characteristics

| Component | Latency | Notes |
|-----------|---------|-------|
| Wake word detection | <50ms | Local, no network |
| Intent classification | <100ms | Rule-based pattern matching |
| Entity extraction | <50ms | Regex-based |
| Complexity scoring | <50ms | Keyword analysis |
| STT (Whisper) | 2-5s | Depends on audio length |
| TTS (ElevenLabs) | 1-3s | Depends on text length |
| Full pipeline | 5-10s | End-to-end |

---

## Troubleshooting

### Audio Quality Issues

- Enable noise reduction: `config.enable_noise_reduction = True`
- Adjust confidence threshold higher for clean audio: `threshold = 0.8`
- Check microphone levels and background noise

### Recognition Failures

- Verify API keys are set correctly
- Check language setting matches spoken language
- Try fallback STT provider (Google)
- Test with pre-recorded high-quality audio

### Synthesis Issues

- Verify TTS API key
- Try fallback provider (AWS Polly or pyttsx3 for offline)
- Check text is properly formatted (no special chars)
- Verify voice_id is valid for selected provider

### Escalation Not Triggering

- Check complexity_score threshold (default: 8.0)
- Verify risk_level is being set correctly
- Check practice area-specific escalation rules

---

## Integration Examples

### With FastAPI Application

```python
from fastapi import FastAPI
from voice.voice_api import create_voice_api_router

app = FastAPI()

# Add voice endpoints
voice_router = create_voice_api_router()
app.include_router(voice_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### With Existing Legal System

```python
from voice import LegalNLPProcessor

# Use NLP for document classification
processor = LegalNLPProcessor()

# Process incoming legal questions
result = processor.process(user_question)

# Use intent to route to appropriate system
if result.intent.primary_intent == Intent.DRAFT_COMPLAINT:
    # Route to complaint generation system
elif result.intent.primary_intent == Intent.SETTLEMENT_NEGOTIATION:
    # Route to settlement system
else:
    # Route to general legal knowledge base
```

---

## Database Schema (Optional)

For session persistence with Redis:

```python
# Session data structure
{
    "session_id": "uuid",
    "user_id": "user123",
    "created_at": "2024-01-01T00:00:00",
    "last_activity": "2024-01-01T00:05:00",
    "client_name": "John Doe",
    "matter_number": "2024-001",
    "practice_area": "criminal",
    "messages": [
        {
            "timestamp": "2024-01-01T00:01:00",
            "user": "I was arrested",
            "assistant": "I understand...",
            "intent": "defense_advice",
            "confidence": 0.89
        }
    ]
}
```

---

## Security Considerations

- ✅ JWT token authentication required on all endpoints
- ✅ Rate limiting to prevent abuse (100 requests/hour)
- ✅ Session ownership verification
- ✅ API key management via environment variables
- ✅ No sensitive data in logs
- ✅ Audio data deleted after processing

---

## Future Enhancements

- [ ] Multi-turn conversation memory across sessions
- [ ] Emotional tone detection in user speech
- [ ] Real-time case law matching
- [ ] Integration with document generation systems
- [ ] Voice quality analysis and feedback
- [ ] Accent-specific pronunciation profiles
- [ ] Expert system integration
- [ ] Machine learning model for escalation prediction
- [ ] Multi-language support expansion
- [ ] Voice emotion synthesis (happy, concerned, urgent)

---

## Contributing

To extend the voice system:

1. Add new intents to `legal_nlp.py::Intent` enum
2. Add intent patterns to `IntentClassifier.INTENT_PATTERNS`
3. Add tests to `test_voice.py`
4. Update documentation in this README

---

## Support

For issues and questions:
- Check troubleshooting section above
- Review test cases for usage examples
- Check API response codes and error messages
- Verify configuration files and environment variables

---

## License

© 2024 SintraPrime Legal Technology. All rights reserved.
