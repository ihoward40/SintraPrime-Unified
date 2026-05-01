"""
CORS middleware for portal.
 """
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

from portal.config import get_settings


class CORSMiddleware(FastAPICORSMiddleware):
    """Custom CORS middleware that reads from settings.CORS_ORIGINS."""
    pass
