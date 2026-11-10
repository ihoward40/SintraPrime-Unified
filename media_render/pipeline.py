"""Render pipeline: orchestrate hyperframes CLI runs via subprocess.

The pipeline never vendors hyperframes code -- it shells out to the external
``npx hyperframes`` CLI (Apache-2.0, heygen-com/hyperframes). Flow per job:

1. Validate the job spec (:mod:`media_render.jobs`).
2. Check dependencies (Node.js, npx, FFmpeg, hyperframes) with a clear,
   non-crashing error when something is missing.
3. Generate the HTML composition (:mod:`media_render.compositions`) into the
   configured workdir.
4. Optionally run ``hyperframes lint`` on the composition.
5. Run ``hyperframes render`` with a timeout, capture logs, and verify the
   output file.

Exact hyperframes subcommand flags can drift between releases; confirm with
``npx hyperframes render --help`` on the installed version and adapt via
``MediaRendererConfig.extra_render_args``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import compositions
from .jobs import ExplainerJob, LyricVideoJob, RenderResult

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class HyperframesError(Exception):
    """Base error for media_render pipeline failures."""


class DependencyError(HyperframesError):
    """Raised when a required external tool is missing."""


class RenderFailedError(HyperframesError):
    """Raised when lint or render exits non-zero (carries the tool logs)."""

    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class RenderTimeoutError(HyperframesError):
    """Raised when lint or render exceeds its configured timeout."""


# ---------------------------------------------------------------------------
# Config & dependency checks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DependencyStatus:
    """Availability of the external tools the pipeline shells out to."""

    node: bool = False
    npx: bool = False
    ffmpeg: bool = False
    hyperframes: bool = False
    hyperframes_version: str = ""

    @property
    def missing(self) -> list[str]:
        return [name for name in ("node", "npx", "ffmpeg", "hyperframes")
                if not getattr(self, name)]

    @property
    def all_available(self) -> bool:
        return not self.missing


@dataclass
class MediaRendererConfig:
    """Pipeline configuration. Paths are configurable; nothing is hardcoded.

    Attributes:
        hyperframes_command: Command used to invoke hyperframes, e.g.
            ``("npx", "hyperframes")`` or an absolute path to a local install.
        workdir: Directory for generated compositions and logs. Defaults to
            ``<system-temp>/media_render``.
        run_lint: Run ``hyperframes lint`` before rendering.
        render_timeout_seconds / lint_timeout_seconds / check_timeout_seconds:
            Subprocess timeouts.
        extra_render_args: Extra CLI flags appended to the render command
            (escape hatch for version-specific flags).
    """

    hyperframes_command: Sequence[str] = ("npx", "hyperframes")
    workdir: str | Path | None = None
    run_lint: bool = True
    render_timeout_seconds: int = 1800
    lint_timeout_seconds: int = 120
    check_timeout_seconds: int = 60
    extra_render_args: Sequence[str] = ()


def check_dependencies(
    command: Sequence[str] = ("npx", "hyperframes"),
    timeout_seconds: int = 60,
) -> DependencyStatus:
    """Probe for node, npx, ffmpeg, and hyperframes. Never raises."""
    status = DependencyStatus(
        node=shutil.which("node") is not None,
        npx=shutil.which("npx") is not None,
        ffmpeg=shutil.which("ffmpeg") is not None,
    )
    version = ""
    hyperframes_ok = False
    try:
        proc = subprocess.run(
            [*command, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if proc.returncode == 0:
            hyperframes_ok = True
            version = (proc.stdout or proc.stderr).strip().splitlines()[0][:120]
    except (OSError, subprocess.SubprocessError):
        hyperframes_ok = False
    return DependencyStatus(
        node=status.node,
        npx=status.npx,
        ffmpeg=status.ffmpeg,
        hyperframes=hyperframes_ok,
        hyperframes_version=version,
    )


_MISSING_GUIDANCE = (
    "node/npx: install Node.js 22+ from https://nodejs.org and ensure it is on PATH. "
    "ffmpeg: install via your OS package manager (e.g. `apt install ffmpeg`, "
    "`brew install ffmpeg`, or `choco install ffmpeg`). "
    "hyperframes: run `npm install -g hyperframes` or use `npx hyperframes` once "
    "with network access so npx can fetch it."
)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class MediaRenderer:
    """Orchestrates hyperframes CLI renders for lyric/explainer jobs."""

    def __init__(self, config: MediaRendererConfig | None = None) -> None:
        self.config = config or MediaRendererConfig()
        base = (Path(self.config.workdir).expanduser()
                if self.config.workdir
                else Path(tempfile.gettempdir()) / "media_render")
        base.mkdir(parents=True, exist_ok=True)
        self.workdir = base

    # -- public API ------------------------------------------------------

    def dependencies(self) -> DependencyStatus:
        """Return the current availability of node/npx/ffmpeg/hyperframes."""
        return check_dependencies(
            self.config.hyperframes_command,
            timeout_seconds=self.config.check_timeout_seconds,
        )

    def render(self, job: LyricVideoJob | ExplainerJob) -> RenderResult:
        """Validate, compose, lint, and render a job to video.

        Raises:
            JobValidationError: job spec is invalid.
            DependencyError: a required external tool is missing.
            RenderFailedError: lint or render exited non-zero.
            RenderTimeoutError: lint or render exceeded its timeout.
        """
        job.validate()

        status = self.dependencies()
        if not status.all_available:
            raise DependencyError(
                "Cannot render: missing required tools: "
                + ", ".join(status.missing)
                + ". " + _MISSING_GUIDANCE
            )

        job_dir = self.workdir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        composition_path = job_dir / "composition.html"
        composition_path.write_text(
            compositions.build_composition_html(job), encoding="utf-8"
        )
        log_path = job_dir / "render.log"

        output_path = Path(str(job.output_path)).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config.run_lint:
            self._run_lint(composition_path, log_path)

        render_cmd = [
            *self.config.hyperframes_command,
            "render",
            str(composition_path),
            "--output",
            str(output_path),
            *self.config.extra_render_args,
        ]
        started = time.monotonic()
        try:
            proc = subprocess.run(
                render_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.render_timeout_seconds,
                cwd=str(job_dir),
            )
        except subprocess.TimeoutExpired as exc:
            raise RenderTimeoutError(
                f"hyperframes render exceeded "
                f"{self.config.render_timeout_seconds}s for job {job.job_id}."
            ) from exc
        except OSError as exc:
            raise HyperframesError(
                f"Failed to launch hyperframes render: {exc}"
            ) from exc
        elapsed = time.monotonic() - started

        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\n$ {' '.join(render_cmd)}\n")
            log.write(proc.stdout or "")
            log.write(proc.stderr or "")

        if proc.returncode != 0:
            raise RenderFailedError(
                f"hyperframes render failed (exit {proc.returncode}) "
                f"for job {job.job_id}. See {log_path} for full logs.",
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RenderFailedError(
                f"hyperframes render reported success but no output video was "
                f"produced at {output_path} (job {job.job_id})."
            )

        return RenderResult(
            job_id=job.job_id,
            success=True,
            output_path=output_path,
            elapsed_seconds=elapsed,
            command=render_cmd,
            stdout_tail=(proc.stdout or "")[-4000:],
            stderr_tail=(proc.stderr or "")[-4000:],
            message=f"Rendered {output_path} in {elapsed:.1f}s.",
        )

    # -- internals -------------------------------------------------------

    def _run_lint(self, composition_path: Path, log_path: Path) -> None:
        lint_cmd = [*self.config.hyperframes_command, "lint", str(composition_path)]
        try:
            proc = subprocess.run(
                lint_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.lint_timeout_seconds,
                cwd=str(composition_path.parent),
            )
        except subprocess.TimeoutExpired as exc:
            raise RenderTimeoutError(
                f"hyperframes lint exceeded {self.config.lint_timeout_seconds}s."
            ) from exc
        except OSError as exc:
            raise HyperframesError(f"Failed to launch hyperframes lint: {exc}") from exc

        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"$ {' '.join(lint_cmd)}\n")
            log.write(proc.stdout or "")
            log.write(proc.stderr or "")

        if proc.returncode != 0:
            raise RenderFailedError(
                f"hyperframes lint failed (exit {proc.returncode}) for "
                f"{composition_path}. Fix the composition and retry.",
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
            )


__all__ = [
    "DependencyError",
    "DependencyStatus",
    "HyperframesError",
    "MediaRenderer",
    "MediaRendererConfig",
    "RenderFailedError",
    "RenderTimeoutError",
    "check_dependencies",
]
