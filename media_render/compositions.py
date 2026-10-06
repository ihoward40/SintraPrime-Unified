"""HTML composition builders for hyperframes rendering.

These builders turn job specs (:mod:`media_render.jobs`) into standalone HTML
documents that follow the HyperFrames composition contract:

- timed elements carry ``class="clip"`` plus ``data-start`` / ``data-end``
  timing attributes (seconds),
- the document is a fixed-size stage (1920x1080 by default),
- media (audio) is referenced by absolute ``file://`` URI so the local
  hyperframes render can resolve it.

The builders are pure string templates -- no browser, Node.js, or FFmpeg is
needed to generate the HTML. Fine-grained animation authoring should follow
the hyperframes ``hyperframes-animation`` skill; the markup here is the
deterministic baseline that ``npx hyperframes lint`` can verify.
"""

from __future__ import annotations

import html as _html
import re
from pathlib import Path

from .jobs import ExplainerJob, LyricLine, LyricVideoJob

# ---------------------------------------------------------------------------
# Shared CSS / helpers
# ---------------------------------------------------------------------------

_STAGE_CSS = """
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: {width}px; height: {height}px; overflow: hidden; }}
  body {{
    font-family: {font};
    background: {bg};
    color: {fg};
    display: flex; align-items: center; justify-content: center;
  }}
  .stage {{ position: relative; width: {width}px; height: {height}px; }}
  .clip {{ position: absolute; opacity: 0; }}
"""


def _escape(text: str) -> str:
    return _html.escape(text, quote=True)


def _audio_uri(path: str | Path) -> str:
    return Path(path).expanduser().resolve().as_uri()


def _split_sentences(text: str) -> list[str]:
    """Split script text into sentences (simple, dependency-free)."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip() for part in parts if part.strip()]


# ---------------------------------------------------------------------------
# Lyric video composition
# ---------------------------------------------------------------------------


def build_lyric_video_html(job: LyricVideoJob) -> str:
    """Build a karaoke-style lyric video composition.

    Each :class:`LyricLine` becomes a ``.clip.lyric`` element visible during
    its ``[start, end]`` window. The active line is highlighted with the
    theme accent; previous/next lines are dimmed for context.
    """
    theme = job.theme
    lines = sorted(job.lyrics, key=lambda line: line.start)

    clips: list[str] = []
    for index, line in enumerate(lines):
        text = _escape(line.text.strip())
        clips.append(
            f'    <div class="clip lyric" data-start="{line.start:.3f}" '
            f'data-end="{line.end:.3f}" data-index="{index}">'
            f"<span>{text}</span></div>"
        )
    clips_html = "\n".join(clips)

    header = ""
    if job.title:
        header = (
            f'    <div class="clip title-card" data-start="0.000" '
            f'data-end="{min(4.0, lines[0].start):.3f}" data-index="title">'
            f"<h1>{_escape(job.title)}</h1>"
            + (f"<p>{_escape(job.artist)}</p>" if job.artist else "")
            + "</div>"
        )

    css = f"""
  .lyric {{
    inset: 0; display: flex; align-items: center; justify-content: center;
    padding: 0 120px; text-align: center;
  }}
  .lyric span {{
    font-size: 72px; font-weight: 800; line-height: 1.25; letter-spacing: 0.01em;
    color: {theme.muted}; transition: color 0.25s ease, transform 0.25s ease;
  }}
  .lyric.active span {{
    color: {theme.foreground};
    text-shadow: 0 0 42px {theme.accent};
    transform: scale(1.03);
  }}
  .title-card {{
    inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 18px; text-align: center;
  }}
  .title-card h1 {{ font-size: 96px; font-weight: 900; color: {theme.foreground}; }}
  .title-card p {{ font-size: 44px; color: {theme.accent}; letter-spacing: 0.2em;
    text-transform: uppercase; }}
  .brand {{
    position: absolute; bottom: 48px; right: 64px;
    font-size: 28px; letter-spacing: 0.3em; text-transform: uppercase;
    color: {theme.muted};
  }}
  .progress {{
    position: absolute; bottom: 0; left: 0; height: 6px; width: 100%;
    background: {theme.accent}; transform-origin: left center;
  }}
"""

    script = """
  <script>
    // Seek-driven activation: hyperframes scrubs `window.__hfTime` (seconds).
    // Fallback to wall-clock playback when previewed in a plain browser.
    (function () {
      const clips = Array.from(document.querySelectorAll('.clip.lyric'));
      const bar = document.getElementById('progress');
      const total = parseFloat(document.body.dataset.duration || '0');
      function tick(t) {
        clips.forEach((el) => {
          const s = parseFloat(el.dataset.start), e = parseFloat(el.dataset.end);
          const active = t >= s && t < e;
          el.style.opacity = active ? '1' : '0';
          el.classList.toggle('active', active);
        });
        if (bar && total > 0) bar.style.transform = 'scaleX(' + Math.min(1, t / total) + ')';
      }
      const start = performance.now();
      function loop() {
        const t = (window.__hfTime !== undefined)
          ? window.__hfTime
          : (performance.now() - start) / 1000;
        tick(t);
        requestAnimationFrame(loop);
      }
      loop();
    })();
  </script>
"""

    return f"""<!DOCTYPE html>
<!-- media_render lyric composition | job {job.job_id} -->
<!-- HyperFrames contract: .clip elements with data-start/data-end (seconds). -->
<!-- Verify with: npx hyperframes lint <this file> -->
<html>
<head>
  <meta charset="utf-8">
  <style>
{_STAGE_CSS.format(width=job.width, height=job.height, font=theme.font_family,
                   bg=theme.background_gradient, fg=theme.foreground)}
{css}
  </style>
</head>
<body data-duration="{job.duration_seconds:.3f}">
  <audio id="track" src="{_audio_uri(job.audio_path)}" preload="auto"></audio>
  <div class="stage">
{header}
{clips_html}
    <div class="brand">Lawful Roots Recordings</div>
    <div id="progress" class="progress"></div>
  </div>
{script}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Explainer composition
# ---------------------------------------------------------------------------


def _chunk_sentences(sentences: list[str], max_words: int) -> list[str]:
    """Group sentences into scenes of at most ``max_words`` words."""
    scenes: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        words = len(sentence.split())
        if current and current_words + words > max_words:
            scenes.append(" ".join(current))
            current, current_words = [], 0
        current.append(sentence)
        current_words += words
    if current:
        scenes.append(" ".join(current))
    return scenes


def split_explainer_scenes(job: ExplainerJob, seconds_per_word: float = 0.45) -> list[tuple[str, float, float]]:
    """Split an explainer script into timed ``(text, start, end)`` scenes.

    Timing is estimated at ``seconds_per_word`` per word (plus a 0.8s beat
    per scene); when narration audio is supplied, the agent should replace
    these estimates with measured timings.
    """
    sentences = _split_sentences(job.script)
    scenes = _chunk_sentences(sentences, job.max_scene_words)
    timed: list[tuple[str, float, float]] = []
    cursor = 0.5  # opening beat
    for scene in scenes:
        duration = max(2.0, len(scene.split()) * seconds_per_word + 0.8)
        timed.append((scene, cursor, cursor + duration))
        cursor += duration + 0.4  # transition gap
    return timed


def build_explainer_html(job: ExplainerJob) -> str:
    """Build a kinetic-typography explainer composition from the job script."""
    theme = job.theme
    scenes = split_explainer_scenes(job)

    clips: list[str] = []
    for index, (text, start, end) in enumerate(scenes):
        # Emphasize the first clause as a headline when a colon/comma splits it.
        head, _, rest = text.partition(":")
        if not rest:
            head, _, rest = text.partition(",")
        headline = _escape(head.strip()) if rest else ""
        body = _escape(rest.strip() if rest else text.strip())
        clips.append(
            f'    <div class="clip scene" data-start="{start:.3f}" '
            f'data-end="{end:.3f}" data-index="{index}">'
            + (f"<h2>{headline}</h2>" if headline else "")
            + f"<p>{body}</p></div>"
        )
    clips_html = "\n".join(clips)
    total = scenes[-1][2] + 0.5 if scenes else 1.0

    title_card = ""
    if job.title:
        title_card = (
            '    <div class="clip title-card" data-start="0.000" data-end="3.000" '
            f'data-index="title"><h1>{_escape(job.title)}</h1></div>'
        )

    css = f"""
  .scene {{
    inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 0 140px; text-align: center; gap: 28px;
  }}
  .scene h2 {{
    font-size: 54px; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: {theme.accent};
  }}
  .scene p {{ font-size: 64px; font-weight: 800; line-height: 1.3;
    color: {theme.foreground}; }}
  .scene.visible h2 {{ animation: rise 0.6s ease both; }}
  .scene.visible p {{ animation: rise 0.6s ease 0.12s both; }}
  @keyframes rise {{
    from {{ opacity: 0; transform: translateY(42px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .title-card {{
    inset: 0; display: flex; align-items: center; justify-content: center;
    text-align: center; padding: 0 120px;
  }}
  .title-card h1 {{ font-size: 104px; font-weight: 900; color: {theme.foreground};
    text-shadow: 0 0 48px {theme.accent}; }}
  .scene-index {{
    position: absolute; top: 56px; left: 72px; font-size: 30px;
    letter-spacing: 0.3em; color: {theme.muted};
  }}
"""

    script = """
  <script>
    // Seek-driven scene activation (see lyric composition for the pattern).
    (function () {
      const clips = Array.from(document.querySelectorAll('.clip.scene, .clip.title-card'));
      const start = performance.now();
      function loop() {
        const t = (window.__hfTime !== undefined)
          ? window.__hfTime
          : (performance.now() - start) / 1000;
        clips.forEach((el) => {
          const s = parseFloat(el.dataset.start), e = parseFloat(el.dataset.end);
          const on = t >= s && t < e;
          el.style.opacity = on ? '1' : '0';
          el.classList.toggle('visible', on);
        });
        requestAnimationFrame(loop);
      }
      loop();
    })();
  </script>
"""

    narration_tag = ""
    if job.narration.engine == "external-file" and job.narration.narration_audio_path:
        narration_tag = (
            f'  <audio id="narration" src="'
            f'{_audio_uri(job.narration.narration_audio_path)}" preload="auto"></audio>\n'
        )

    return f"""<!DOCTYPE html>
<!-- media_render explainer composition | job {job.job_id} -->
<!-- HyperFrames contract: .clip elements with data-start/data-end (seconds). -->
<!-- Verify with: npx hyperframes lint <this file> -->
<html>
<head>
  <meta charset="utf-8">
  <style>
{_STAGE_CSS.format(width=job.width, height=job.height, font=theme.font_family,
                   bg=theme.background_gradient, fg=theme.foreground)}
{css}
  </style>
</head>
<body data-duration="{total:.3f}">
{narration_tag}  <div class="stage">
{title_card}
{clips_html}
    <div class="scene-index">EXPLAINER</div>
  </div>
{script}
</body>
</html>
"""


def build_composition_html(job: LyricVideoJob | ExplainerJob) -> str:
    """Dispatch to the right builder for the job type."""
    if isinstance(job, LyricVideoJob):
        return build_lyric_video_html(job)
    if isinstance(job, ExplainerJob):
        return build_explainer_html(job)
    raise TypeError(f"Unsupported job type: {type(job).__name__}")
