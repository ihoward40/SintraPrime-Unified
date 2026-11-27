# VoiceStudio Sidecar (Optional)

Upstream project: <https://github.com/debpalash/VoiceStudio>

## Status: OPTIONAL AND SEPARATE

Running VoiceStudio is **entirely optional**. It is a separate,
independently-maintained open-source project — it is **not** part of
SintraPrime-Unified, it is not vendored here, and no VoiceStudio source
code is included in this repository. SintraPrime's built-in local voice
pipeline lives in `voice/local_voice.py` and works without this sidecar.

Use the sidecar only if you want the extra capabilities VoiceStudio
provides (its own voice cloning/enrollment, voice design, dubbing,
dictation, and transcription tooling) while keeping it isolated in its
own process.

## License note

VoiceStudio is distributed under the **GNU Affero General Public License
v3.0 (AGPL-3.0)**. If you run or modify it, the AGPL's terms apply to
that separate project — including the network-use (SaaS) provision.
Running it as an unmodified sidecar next to SintraPrime does not change
the license of SintraPrime-Unified itself, but review the AGPL text at
<https://github.com/debpalash/VoiceStudio> before deploying it in any
networked setting.

## 1. Install (on the machine that will host the sidecar)

```bash
# Clone the upstream project (separate directory, outside this repo)
git clone https://github.com/debpalash/VoiceStudio.git
cd VoiceStudio

# Follow the project's own README for prerequisites and install steps,
# e.g. Python version, system audio libraries, and model downloads.
```

## 2. Run as a local sidecar

```bash
cd VoiceStudio
# Start VoiceStudio per its README (it exposes a local interface;
# consult the upstream docs for the exact command and port).
```

Keep it bound to loopback only (e.g. `127.0.0.1`) so it is reachable
solely from the SintraPrime host.

## 3. How SintraPrime talks to it

SintraPrime communicates with the sidecar over a **local interface**
only — plain HTTP/WebSocket on `localhost`. No traffic leaves the
machine:

```
SintraPrime (voice/local_voice.py or voice/voice_api.py)
        │  HTTP / WebSocket, 127.0.0.1 only
        ▼
VoiceStudio sidecar process (separate repo, separate license)
```

Suggested integration pattern:

1. Implement a `LocalVoiceBackend` subclass (see `voice/local_voice.py`)
   whose methods translate to the sidecar's local HTTP endpoints:
   - `enroll_voice()` → sidecar voice enrollment endpoint
   - `synthesize()` → sidecar TTS endpoint
   - `transcribe()` / `transcribe_chunk()` → sidecar STT endpoints
2. Pass that backend into `create_local_voice_pipeline(backend=...)`.
   The rest of the pipeline (registry, dictation sessions, dubbing
   plans) and the `/voice/local/*` API routes work unchanged.
3. Keep credentials out of the repo: any sidecar token or port belongs
   in environment variables or `.env` (see `.env.example`), never in
   committed code.

## 4. Verifying the sidecar

- Confirm the sidecar process is listening on loopback before starting
  SintraPrime.
- Exercise one enrollment and one synthesis through the
  `/voice/local/*` routes and confirm `is_placeholder` is `false` in
  the synthesis result (the built-in stub always returns
  `is_placeholder: true`).
- If the sidecar is down, calls should fail fast with a clear error —
  never silently fall back to the placeholder stub for production audio.

## 5. Uninstall

Delete the cloned `VoiceStudio` directory and stop its process.
SintraPrime continues to work with its built-in pipeline; nothing in
this repository depends on the sidecar.
