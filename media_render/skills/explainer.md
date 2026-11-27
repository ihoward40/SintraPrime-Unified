---
name: explainer
description: Turn a script into a kinetic-typography explainer video job for the media_render pipeline.
---

# explainer (media_render skill)

You turn a script into a visual explainer video. This mirrors the hyperframes
`/faceless-explainer` workflow, but targets the `media_render` Python package
so renders are repeatable jobs.

## Inputs you need

1. **Script** — raw text (`script_text`) or a path to a text/markdown file
   (`script_path`). Exactly one of the two.
2. **Narration (optional)** — `media_render` does not synthesize speech. If the
   video needs voiceover, the audio must come from an external TTS step first;
   attach it with `NarrationOptions(engine="external-file",
   narration_audio_path=...)`. Otherwise leave the default (`engine="none"`)
   for a typography-only render.
3. **Style** — a `media_render` theme plus optional `title` for the title card.

## Procedure

1. Build the job:
   ```python
   from media_render import ExplainerJob, NarrationOptions

   job = ExplainerJob(
       script_text="Your explainer script goes here. One idea per sentence.",
       output_path="/path/to/explainer.mp4",
       narration=NarrationOptions(engine="none"),
       title="What Is Compound Interest?",
   )
   job.validate()
   ```
   For a long script file, prefer `script_path="/path/to/script.md"`.
2. Preview the scene plan before rendering (no CLI needed):
   ```python
   from media_render import split_explainer_scenes
   for text, start, end in split_explainer_scenes(job):
       print(f"[{start:6.1f}s - {end:6.1f}s] {text[:60]}")
   ```
   Scene timings are estimates (words-per-minute based). If narration audio is
   supplied, replace them with measured timings before rendering.
3. Check dependencies and render, same as the music-to-video skill:
   ```python
   from media_render import MediaRenderer, check_dependencies
   status = check_dependencies()
   assert status.all_available, f"Missing tools: {status.missing}"
   result = MediaRenderer().render(job)
   ```
4. Confirm the output file exists and report path + render time.

## Rules

- Keep scenes short: the builder caps scenes at `max_scene_words` (default 18).
  If a scene reads awkwardly, split the source sentence -- don't hand-edit the
  generated HTML.
- One sentence, one idea. If the script rambles, ask the user to tighten it
  before rendering; rendering is CPU/FFmpeg-heavy, so avoid throwaway renders.
- `lint` failures mean the composition inputs are bad -- fix the script/theme,
  not the pipeline.
- Never present estimated scene timings as measured narration timings.
