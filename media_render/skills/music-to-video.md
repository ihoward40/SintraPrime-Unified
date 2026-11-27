---
name: music-to-video
description: Turn an audio track plus timed lyrics into a karaoke-style lyric video job for the media_render pipeline.
---

# music-to-video (media_render skill)

You turn a track + lyrics into a rendered lyric video. This mirrors the
hyperframes `/music-to-video` workflow, but targets the `media_render`
Python package so renders are repeatable jobs, not one-off CLI sessions.

## Inputs you need

1. **Audio file** — a local path to the track (mp3/wav/m4a). Confirm it exists
   before doing anything else.
2. **Timed lyrics** — a list of lines with `start`/`end` in seconds. If the
   user only has plain lyrics, ask for (or estimate and clearly label as
   estimated) timestamps; never silently invent precise timings.
3. **Style** — pick a `media_render` theme (`lawful-roots`, `neon-night`,
   `paper`) or a custom `Theme(...)`, plus optional `title`/`artist` for the
   title card.

## Procedure

1. Build the job:
   ```python
   from media_render import LyricVideoJob, LyricLine, PRESET_THEMES

   job = LyricVideoJob(
       audio_path="/path/to/track.mp3",
       lyrics=[
           LyricLine("First line of the song", 0.5, 3.2),
           LyricLine("Second line follows", 3.4, 6.1),
       ],
       output_path="/path/to/output.mp4",
       theme=PRESET_THEMES["lawful-roots"],
       title="Song Title",
       artist="Artist Name",
   )
   job.validate()  # raises JobValidationError on bad input -- fix, don't bypass
   ```
2. Check the environment before rendering:
   ```python
   from media_render import check_dependencies
   status = check_dependencies()
   assert status.all_available, f"Missing tools: {status.missing}"
   ```
   If anything is missing, tell the user exactly what to install (Node.js 22+,
   FFmpeg, `npx hyperframes`) instead of proceeding.
3. Render:
   ```python
   from media_render import MediaRenderer
   result = MediaRenderer().render(job)
   print(result.message)  # e.g. "Rendered /path/to/output.mp4 in 41.2s."
   ```
4. Confirm the output file exists and is non-trivial in size; report the path
   and render time back to the user.

## Rules

- Validation errors are user-facing guidance, not bugs: quote the message and
  ask for corrected input.
- Lyrics must not overlap; keep timestamps monotonic.
- Never hardcode machine-specific paths in reusable code -- take them as
  arguments or configuration.
- The pipeline shells out to the external hyperframes CLI; no hyperframes
  code is vendored here. If `lint` fails, fix the composition inputs (lyrics,
  theme values), not the pipeline.
