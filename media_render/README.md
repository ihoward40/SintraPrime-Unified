# media_render

Hyperframes-backed video rendering for IKE Solutions media work
(Lawful Roots Recordings: music videos, lyric videos, visual educational content).

`media_render` turns **job specs** (Python dataclasses) into rendered MP4s by
generating hyperframes-compatible HTML compositions and shelling out to the
external `npx hyperframes` CLI. It covers two workflows:

| Workflow | Job | What it makes |
|---|---|---|
| music-to-video | `LyricVideoJob` | Karaoke-style lyric video from an audio track + timed lyrics |
| explainer | `ExplainerJob` | Kinetic-typography explainer video from a script |

Agent instructions for both workflows live in `media_render/skills/`
(`music-to-video.md`, `explainer.md`).

## Requirements

- **Python 3.11+**, type hints throughout, stdlib only (no third-party deps).
- **Node.js 22+** and **FFmpeg** installed and on `PATH`.
- **hyperframes CLI** available as `npx hyperframes` (or a local install --
  the command is configurable). The package never vendors hyperframes code;
  it is used strictly as an external tool.

## Quick start

```python
from media_render import (
    LyricVideoJob, LyricLine, PRESET_THEMES,
    MediaRenderer, check_dependencies,
)

job = LyricVideoJob(
    audio_path="track.mp3",
    lyrics=[
        LyricLine("First line of the song", 0.5, 3.2),
        LyricLine("Second line follows", 3.4, 6.1),
    ],
    output_path="lyric-video.mp4",
    theme=PRESET_THEMES["lawful-roots"],
    title="Song Title",
    artist="Artist Name",
)

status = check_dependencies()
if not status.all_available:
    raise SystemExit(f"Missing tools: {status.missing}")

result = MediaRenderer().render(job)
print(result.message)
```

Explainer:

```python
from media_render import ExplainerJob, NarrationOptions, MediaRenderer

job = ExplainerJob(
    script_text="Compound interest is interest on interest. ...",
    output_path="explainer.mp4",
    narration=NarrationOptions(engine="none"),  # typography only
    title="What Is Compound Interest?",
)
result = MediaRenderer().render(job)
```

With narration audio produced by an external TTS step:

```python
job = ExplainerJob(
    script_path="script.md",
    output_path="explainer.mp4",
    narration=NarrationOptions(engine="external-file",
                               narration_audio_path="voiceover.wav"),
)
```

Validate without rendering (no CLI needed):

```python
job.validate()  # raises media_render.JobValidationError with a clear message
```

Preview the scene plan for an explainer (no CLI needed):

```python
from media_render import split_explainer_scenes
for text, start, end in split_explainer_scenes(job):
    print(f"[{start:6.1f}s - {end:6.1f}s] {text[:60]}")
```

Run the unit tests (no CLI needed):

```bash
python -m pytest media_render/tests/ -q
# or: python -m unittest discover -s media_render/tests
```

## Architecture

```
job spec (jobs.py: LyricVideoJob / ExplainerJob, validated)
      |
      v
composition HTML (compositions.py: pure string-template builders)
      |   .clip elements + data-start/data-end timing attributes
      v
pipeline (pipeline.py: MediaRenderer)
      |-- check_dependencies(): node / npx / ffmpeg / hyperframes
      |-- write composition.html + render.log into workdir/<job_id>/
      |-- [optional] `hyperframes lint` on the composition
      |-- `hyperframes render composition.html --output out.mp4` (timeout-guarded)
      v
RenderResult (success, output_path, elapsed_seconds, logs, command)
```

- `jobs.py` -- dataclasses + validation only. Importable and testable with
  nothing installed.
- `compositions.py` -- HTML builders following the hyperframes composition
  contract (`class="clip"`, `data-*` timing). Verify generated HTML with
  `npx hyperframes lint`.
- `pipeline.py` -- orchestration via `subprocess`. Binary path, workdir,
  timeouts, and extra render flags are all configurable through
  `MediaRendererConfig`; nothing is hardcoded to a real machine path.
- Errors are typed: `DependencyError` (missing tool, with install guidance),
  `RenderFailedError` (non-zero exit, carries logs), `RenderTimeoutError`,
  `JobValidationError`.

> **CLI flag drift:** exact hyperframes subcommand flags can change between
> releases. Confirm with `npx hyperframes render --help` on the installed
> version and adapt via `MediaRendererConfig.extra_render_args`.

## Attribution

This package's workflows are inspired by
[heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)
("Write HTML. Render video."), which is used here **as an external CLI tool
only** -- no hyperframes source code is included or vendored in this package.

Hyperframes is licensed under the Apache License, Version 2.0. Per that
license: this package is not affiliated with or endorsed by HeyGen; the
Apache-2.0 license text for hyperframes itself ships with the hyperframes
distribution, not here. If you redistribute hyperframes alongside this
package, include its LICENSE and attribution notices.
