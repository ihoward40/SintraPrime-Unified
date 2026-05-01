import datetime
from starlette.middleware.base import BaseHTTPMiddleware

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.session_created = datetime.datetime.now(tz=datetime.timezone.utc).date()
        response = await call_next(request)
        return response
