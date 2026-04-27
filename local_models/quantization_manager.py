"""
Quantization Manager — SintraPrime-Unified local_models
GGUF format support, memory requirement calculation, quantization
recommendations, download management, and basic benchmarking.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Memory overhead factor for OS + framework
MEM_OVERHEAD_FACTOR = 1.15

# Bytes per parameter for each quantization level (approximate)
QUANT_BYTES_PER_PARAM: Dict[str, float] = {
    "F16":    2.0,
    "Q8_0":   1.0,
    "Q6_K":   0.75,
    "Q5_K_M": 0.625,
    "Q5_K_S": 0.5625,
    "Q4_K_M": 0.5,
    "Q4_K_S": 0.4375,
    "Q3_K_M": 0.375,
    "Q2_K":   0.25,
}

# Known model sizes in billions of parameters
KNOWN_MODEL_PARAMS: Dict[str, float] = {
    "llama3":          8.0,
    "llama3:8b":       8.0,
    "llama3:70b":     70.0,
    "mistral":         7.0,
    "mistral:7b":      7.0,
    "deepseek-r1":     7.0,
    "deepseek-r1:7b":  7.0,
    "deepseek-r1:8b":  8.0,
    "deepseek-r1:14b":14.0,
    "deepseek-r1:32b":32.0,
    "deepseek-r1:70b":70.0,
    "hermes3":         8.0,
    "hermes3:8b":      8.0,
    "phi3":            3.8,
    "gemma2":          9.0,
    "qwen2":           7.0,
    "codellama":       7.0,
}

# Recommended quantizations
RECOMMENDED_QUANTS = ["Q4_K_M", "Q5_K_M", "Q8_0"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class QuantRecommendation:
    quant: str
    size_gb: float
    quality: str          # "good", "better", "best"
    speed: str            # "fastest", "fast", "moderate"
    suitable: bool        # fits in available RAM
    notes: str


@dataclass
class DownloadJob:
    url: str
    dest_path: Path
    model_name: str
    quant: str
    size_bytes: int = 0
    downloaded_bytes: int = 0
    status: str = "pending"   # pending / downloading / done / error
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    model: str
    quant: str
    tokens_per_second: float
    memory_used_gb: float
    latency_first_token_ms: float
    prompt_tokens: int
    completion_tokens: int
    duration_s: float


# ---------------------------------------------------------------------------
# QuantizationManager
# ---------------------------------------------------------------------------


class QuantizationManager:
    """
    Manages GGUF model quantization info, memory calculations,
    download helpers, and basic benchmarking.

    Parameters
    ----------
    models_dir:
        Local directory where GGUF models are stored.
    available_ram_gb:
        Total RAM available for models. Auto-detected if not provided.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        available_ram_gb: Optional[float] = None,
    ) -> None:
        self.models_dir = models_dir or Path.home() / ".sintra" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._ram_gb = available_ram_gb or self._detect_ram()

    # ------------------------------------------------------------------
    # RAM detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_ram() -> float:
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            # Fallback: read /proc/meminfo
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            return kb / (1024 ** 2)
            except Exception:
                pass
        return 16.0  # Assume 16 GB if detection fails

    @property
    def available_ram_gb(self) -> float:
        return self._ram_gb

    # ------------------------------------------------------------------
    # Memory requirement calculation
    # ------------------------------------------------------------------

    def memory_required_gb(self, model: str, quant: str = "Q4_K_M") -> float:
        """
        Estimate the RAM required to run a model with the given quantization.

        Parameters
        ----------
        model:
            Model name (e.g. "llama3:8b").
        quant:
            Quantization level (e.g. "Q4_K_M").

        Returns
        -------
        Required RAM in GB.
        """
        params_b = KNOWN_MODEL_PARAMS.get(model.lower(), 7.0)  # default 7B
        bpp = QUANT_BYTES_PER_PARAM.get(quant.upper(), 0.5)
        raw_gb = params_b * 1e9 * bpp / (1024 ** 3)
        return round(raw_gb * MEM_OVERHEAD_FACTOR, 2)

    def what_can_i_run(self, ram_gb: Optional[float] = None) -> Dict[str, List[str]]:
        """
        Return a report of which model/quant combinations fit in available RAM.

        Returns a dict: model → list of fitting quantizations.
        """
        ram = ram_gb or self._ram_gb
        result: Dict[str, List[str]] = {}
        for model_name, params_b in KNOWN_MODEL_PARAMS.items():
            fitting = []
            for quant, bpp in QUANT_BYTES_PER_PARAM.items():
                req = params_b * 1e9 * bpp / (1024 ** 3) * MEM_OVERHEAD_FACTOR
                if req <= ram:
                    fitting.append(quant)
            if fitting:
                result[model_name] = fitting
        return result

    # ------------------------------------------------------------------
    # Quantization recommendations
    # ------------------------------------------------------------------

    def recommend_quantization(
        self,
        model: str,
        priority: str = "balanced",
    ) -> List[QuantRecommendation]:
        """
        Recommend quantization levels for a model.

        Parameters
        ----------
        model:
            Model name.
        priority:
            ``"speed"`` — fastest inference.
            ``"quality"`` — highest quality output.
            ``"balanced"`` — good balance (default).

        Returns a list of QuantRecommendation sorted by suitability.
        """
        recs: List[QuantRecommendation] = []
        ram = self._ram_gb

        quant_profiles = {
            "Q4_K_M": ("good",   "fastest", "Best balance for most users. Minimal quality loss vs Q5/Q8."),
            "Q5_K_M": ("better", "fast",     "~5% more RAM than Q4, noticeably better quality."),
            "Q8_0":   ("best",   "moderate", "Near-FP16 quality, ~2× size of Q4. Use if RAM allows."),
            "Q6_K":   ("better", "fast",     "Between Q5 and Q8. Good for quality-focused workloads."),
            "Q3_K_M": ("fair",   "fastest",  "Very small but noticeable quality drop. Last resort."),
        }

        for quant, (quality, speed, notes) in quant_profiles.items():
            req = self.memory_required_gb(model, quant)
            recs.append(QuantRecommendation(
                quant=quant,
                size_gb=req,
                quality=quality,
                speed=speed,
                suitable=req <= ram,
                notes=notes,
            ))

        # Sort by priority
        if priority == "speed":
            recs.sort(key=lambda r: (not r.suitable, {"fastest": 0, "fast": 1, "moderate": 2}.get(r.speed, 9)))
        elif priority == "quality":
            recs.sort(key=lambda r: (not r.suitable, {"best": 0, "better": 1, "good": 2, "fair": 3}.get(r.quality, 9)))
        else:  # balanced
            recs.sort(key=lambda r: (not r.suitable, {"Q4_K_M": 0, "Q5_K_M": 1, "Q6_K": 2, "Q8_0": 3, "Q3_K_M": 4}.get(r.quant, 9)))

        return recs

    def best_quant_for_ram(self, model: str, ram_gb: Optional[float] = None) -> str:
        """Return the best quantization that fits in available RAM."""
        ram = ram_gb or self._ram_gb
        for quant in ["Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]:
            if self.memory_required_gb(model, quant) <= ram:
                return quant
        return "Q2_K"  # smallest

    # ------------------------------------------------------------------
    # GGUF info
    # ------------------------------------------------------------------

    @staticmethod
    def gguf_info() -> Dict[str, Any]:
        """Return general information about the GGUF format."""
        return {
            "format": "GGUF",
            "description": (
                "GGUF (GPT-Generated Unified Format) is the standard format for "
                "quantized GGML models. Used by llama.cpp and Ollama."
            ),
            "file_extension": ".gguf",
            "quantization_levels": list(QUANT_BYTES_PER_PARAM.keys()),
            "recommended_for_legal": ["Q4_K_M", "Q5_K_M"],
            "sources": [
                "https://huggingface.co/TheBloke",
                "https://huggingface.co/bartowski",
                "https://ollama.com/library",
            ],
        }

    def list_local_models(self) -> List[Dict[str, Any]]:
        """List GGUF models stored in the local models directory."""
        models = []
        for p in self.models_dir.glob("**/*.gguf"):
            stat = p.stat()
            models.append({
                "name": p.stem,
                "path": str(p),
                "size_gb": round(stat.st_size / (1024 ** 3), 2),
                "modified": stat.st_mtime,
            })
        return models

    # ------------------------------------------------------------------
    # Download manager
    # ------------------------------------------------------------------

    def download_model(
        self,
        url: str,
        model_name: str,
        quant: str = "Q4_K_M",
        progress_callback: Optional[Callable[[int, int], None]] = None,
        verify_sha256: Optional[str] = None,
    ) -> DownloadJob:
        """
        Download a GGUF model file.

        Parameters
        ----------
        url:
            Direct URL to the .gguf file.
        model_name:
            Human-readable name (used for filename).
        quant:
            Quantization level (used for filename).
        progress_callback:
            Called with (downloaded_bytes, total_bytes) during download.
        verify_sha256:
            If provided, verify the downloaded file's SHA-256 hash.

        Returns
        -------
        A completed or errored DownloadJob.
        """
        import requests

        filename = f"{model_name}-{quant}.gguf".replace("/", "_").replace(":", "_")
        dest = self.models_dir / filename

        job = DownloadJob(
            url=url,
            dest_path=dest,
            model_name=model_name,
            quant=quant,
        )

        if dest.exists():
            logger.info("Model already downloaded: %s", dest)
            job.status = "done"
            job.downloaded_bytes = dest.stat().st_size
            job.size_bytes = job.downloaded_bytes
            return job

        job.status = "downloading"
        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            job.size_bytes = total

            sha = hashlib.sha256()
            downloaded = 0

            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        sha.update(chunk)
                        downloaded += len(chunk)
                        job.downloaded_bytes = downloaded
                        if progress_callback:
                            progress_callback(downloaded, total)

            if verify_sha256 and sha.hexdigest() != verify_sha256:
                dest.unlink(missing_ok=True)
                job.status = "error"
                job.error = f"SHA-256 mismatch: expected {verify_sha256}, got {sha.hexdigest()}"
                return job

            job.status = "done"
            logger.info("Downloaded model to %s", dest)

        except Exception as exc:
            job.status = "error"
            job.error = str(exc)
            logger.error("Download failed: %s", exc)

        return job

    # ------------------------------------------------------------------
    # Benchmarking
    # ------------------------------------------------------------------

    def benchmark_model(
        self,
        model: str,
        quant: str = "Q4_K_M",
        prompt: str = "Explain the concept of habeas corpus in simple terms.",
        num_tokens: int = 50,
        ollama_url: str = "http://localhost:11434",
    ) -> BenchmarkResult:
        """
        Benchmark a locally running Ollama model.

        Measures tokens/sec and latency to first token.
        """
        import requests

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": num_tokens},
        }

        first_token_ms = 0.0
        start = time.time()
        first = True
        total_tokens = 0

        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json=payload,
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            import json
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if first:
                    first_token_ms = (time.time() - start) * 1000
                    first = False
                total_tokens += 1
                if chunk.get("done"):
                    break
        except Exception as exc:
            logger.error("Benchmark failed: %s", exc)
            return BenchmarkResult(
                model=model, quant=quant, tokens_per_second=0.0,
                memory_used_gb=0.0, latency_first_token_ms=0.0,
                prompt_tokens=0, completion_tokens=0, duration_s=0.0,
            )

        duration = time.time() - start
        tps = total_tokens / duration if duration > 0 else 0.0
        mem = self.memory_required_gb(model, quant)

        return BenchmarkResult(
            model=model,
            quant=quant,
            tokens_per_second=round(tps, 2),
            memory_used_gb=mem,
            latency_first_token_ms=round(first_token_ms, 1),
            prompt_tokens=len(prompt.split()),
            completion_tokens=total_tokens,
            duration_s=round(duration, 2),
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"QuantizationManager(ram_gb={self._ram_gb:.1f}, "
            f"models_dir={self.models_dir!r})"
        )
