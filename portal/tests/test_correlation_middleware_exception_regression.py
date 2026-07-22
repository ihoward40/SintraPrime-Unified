from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from portal.middleware.correlation_middleware import CorrelationMiddleware


@pytest.mark.asyncio
async def test_post_exception_preserves_original_runtime_error() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.post('/boom')
    async def boom() -> dict[str, bool]:
        raise RuntimeError('boom')

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        with pytest.raises(RuntimeError, match='boom'):
            await client.post('/boom')


@pytest.mark.asyncio
async def test_post_success_still_returns_request_id_header() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.post('/ok')
    async def ok() -> JSONResponse:
        return JSONResponse({'ok': True})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        response = await client.post('/ok')

    assert response.status_code == 200
    assert response.headers['x-request-id'].startswith('req-')
