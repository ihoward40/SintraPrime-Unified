"""
SintraPrime App Builder & Digital Twin
======================================
Autonomous web/app builder for legal and financial use cases,
plus a Digital Twin AI that learns the user's world model.

Inspired by:
- Manus AI Web App Builder (full websites, database, Stripe, SEO)
- Digital Twin AI (learns user world model, life governance)
- GPT-5.5 Workspace Agents (custom bots for specific roles)
- Space Agent (personal life management AI)
"""

from .app_builder import AppBuilder
from .digital_twin import DigitalTwin
from .site_generator import SiteGenerator
from .app_types import AppSpec, AppTemplate, AppType, BuildResult
from .database_builder import DatabaseBuilder
from .stripe_integrator import StripeIntegrator
from .template_library import TemplateLibrary

__all__ = [
    "AppBuilder",
    "DigitalTwin",
    "SiteGenerator",
    "AppSpec",
    "AppTemplate",
    "AppType",
    "BuildResult",
    "DatabaseBuilder",
    "StripeIntegrator",
    "TemplateLibrary",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"
