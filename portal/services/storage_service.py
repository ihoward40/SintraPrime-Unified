"""
MinIO (S3-compatible) storage service.
Handles file upload, download, deletion, presigned URLs.
"""

from __future__ import annotations

import io
from typing import Optional
from urllib.parse import urljoin

from ..config import get_settings

settings = get_settings()


class StorageService:
    """Async wrapper around MinIO client."""

    def __init__(self) -> None:
        try:
            from minio import Minio  # type: ignore
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        except ImportError:
            self._client = None  # Will raise on use in production

    async def ensure_bucket_exists(self, bucket: str) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        found = await loop.run_in_executor(None, self._client.bucket_exists, bucket)
        if not found:
            await loop.run_in_executor(None, self._client.make_bucket, bucket)

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> None:
        import asyncio
        await self.ensure_bucket_exists(bucket)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=metadata or {},
            ),
        )

    async def get_object(self, bucket: str, key: str) -> bytes:
        import asyncio
        loop = asyncio.get_event_loop()

        def _get():
            response = self._client.get_object(bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await loop.run_in_executor(None, _get)

    async def delete_object(self, bucket: str, key: str) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.remove_object, bucket, key)

    async def presigned_get_url(
        self, bucket: str, key: str, expires_seconds: int = 3600
    ) -> str:
        import asyncio
        from datetime import timedelta
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=expires_seconds),
            ),
        )
        return url

    async def object_exists(self, bucket: str, key: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._client.stat_object, bucket, key)
            return True
        except Exception:
            return False

    async def copy_object(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> None:
        import asyncio
        from minio.commonconfig import CopySource  # type: ignore
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.copy_object(
                bucket_name=dest_bucket,
                object_name=dest_key,
                source=CopySource(src_bucket, src_key),
            ),
        )
