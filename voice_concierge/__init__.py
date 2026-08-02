"""
SintraPrime Voice Concierge (SP-VOICE-001)
===========================================

Top-level package for the governed voice-command orchestration foundation.

This package is intentionally kept free of eager imports so that importing
any submodule (e.g. ``voice_concierge.governed``) never pulls in unrelated,
heavy, or optional dependencies. See ``voice_concierge/governed/AGENTS.md``
for scope and governance contracts.
"""
