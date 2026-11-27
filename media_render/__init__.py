"""media_render -- hyperframes-backed video rendering for IKE Solutions media.

Produces lyric videos and visual explainer videos for the Lawful Roots
Recordings media arm by generating hyperframes-compatible HTML compositions
and rendering them to MP4 through the external ``npx hyperframes`` CLI
(heygen-com/hyperframes, Apache-2.0).

Imports are lazy so that importing this package never pulls in heavy or
optional dependencies.
"""

__all__ = [
    "PRESET_THEMES",
    "DependencyError",
    "DependencyStatus",
    "ExplainerJob",
    "HyperframesError",
    "JobValidationError",
    "LyricLine",
    "LyricVideoJob",
    "MediaRenderer",
    "MediaRendererConfig",
    "NarrationOptions",
    "RenderFailedError",
    "RenderResult",
    "RenderTimeoutError",
    "Theme",
    "build_composition_html",
    "build_explainer_html",
    "build_lyric_video_html",
    "check_dependencies",
    "split_explainer_scenes",
]

_EXPORTS = {
    "LyricVideoJob": ("media_render.jobs", "LyricVideoJob"),
    "LyricLine": ("media_render.jobs", "LyricLine"),
    "ExplainerJob": ("media_render.jobs", "ExplainerJob"),
    "NarrationOptions": ("media_render.jobs", "NarrationOptions"),
    "Theme": ("media_render.jobs", "Theme"),
    "PRESET_THEMES": ("media_render.jobs", "PRESET_THEMES"),
    "RenderResult": ("media_render.jobs", "RenderResult"),
    "JobValidationError": ("media_render.jobs", "JobValidationError"),
    "build_composition_html": ("media_render.compositions", "build_composition_html"),
    "build_lyric_video_html": ("media_render.compositions", "build_lyric_video_html"),
    "build_explainer_html": ("media_render.compositions", "build_explainer_html"),
    "split_explainer_scenes": ("media_render.compositions", "split_explainer_scenes"),
    "MediaRenderer": ("media_render.pipeline", "MediaRenderer"),
    "MediaRendererConfig": ("media_render.pipeline", "MediaRendererConfig"),
    "DependencyStatus": ("media_render.pipeline", "DependencyStatus"),
    "check_dependencies": ("media_render.pipeline", "check_dependencies"),
    "HyperframesError": ("media_render.pipeline", "HyperframesError"),
    "DependencyError": ("media_render.pipeline", "DependencyError"),
    "RenderFailedError": ("media_render.pipeline", "RenderFailedError"),
    "RenderTimeoutError": ("media_render.pipeline", "RenderTimeoutError"),
}


def __getattr__(name: str):
    if name in _EXPORTS:
        module_name, attr = _EXPORTS[name]
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, attr)
    raise AttributeError(f"module 'media_render' has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
