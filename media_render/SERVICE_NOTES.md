# media_render — Service Notes

Operational notes for running the `media_render` pipeline. This is not user
documentation; see `README.md` for setup and usage.

## Resource requirements

- Rendering is **CPU- and FFmpeg-heavy**. A 1080p30 lyric video renders
  roughly in real time or slower on a modest VM; 4K or long-form work should
  run on a machine with spare cores, not alongside latency-sensitive services.
- `npx hyperframes` launches a headless browser (Puppeteer/Chromium) plus
  FFmpeg. Expect transient spikes of several hundred MB RAM per render.
- First run may download the hyperframes package via npx -- allow network
  access or pre-install it (`npm install -g hyperframes`) and point
  `MediaRendererConfig.hyperframes_command` at the local binary.

## Suggested queueing

- Serialize renders per machine: one `MediaRenderer.render()` at a time per
  host unless the host is sized for parallel FFmpeg encodes. A simple FIFO
  (e.g. a scheduler cron or a lightweight task queue) is enough; do not build
  a bespoke render farm unless volume justifies it.
- Default render timeout is 30 minutes (`render_timeout_seconds`). Long-form
  videos (>10 min) should raise it explicitly per job.
- Each job gets an isolated directory: `<workdir>/<job_id>/` containing
  `composition.html` and `render.log`. Keep these for post-mortems; they are
  small (HTML + logs).

## Output storage conventions

- Name outputs deterministically: `<slug>-<job_id>.mp4`
  (e.g. `lawful-roots-anthem-a1b2c3d4e5f6.mp4`). The `job_id` in the filename
  ties the artifact back to its `render.log`.
- Store finished videos outside the workdir (the workdir is scratch).
  Suggested layout: `<media_root>/<YYYY-MM-DD>/<slug>-<job_id>.mp4`.
- Retain `render.log` alongside the output for at least 30 days; it is the
  audit trail for what command produced the file.
- Treat `composition.html` as a build intermediate: reproducible from the job
  spec, safe to discard after the render log is archived.

## Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `DependencyError` listing missing tools | Node/FFmpeg/hyperframes not installed | Follow the install guidance in the error message |
| `RenderFailedError` from `lint` | Composition inputs invalid (bad theme values, malformed lyrics) | Fix job inputs; do not patch the pipeline |
| `RenderFailedError` from `render`, exit != 0 | FFmpeg/Chromium failure; see `render.log` | Check disk space, memory, and the tail of the log |
| `RenderTimeoutError` | Machine too slow or job too long | Raise `render_timeout_seconds` or move to a bigger host |
| Output file missing after "success" | CLI version changed its output flag behavior | Confirm with `npx hyperframes render --help`; adapt `extra_render_args` |

## Security notes

- No secrets, API keys, or credentials appear anywhere in this package, and
  none are needed: rendering is fully local.
- `audio_path` / `script_path` are read from disk; `output_path` is written to
  disk. Run the pipeline with the least-privilege filesystem scope that still
  reaches the media library and the output directory.
- Composition HTML embeds local `file://` audio URIs. Do not serve the
  workdir over HTTP; it is scratch, not a web root.
