"""S3-compatible object storage service (MinIO)."""

from __future__ import annotations

import hashlib
from typing import BinaryIO
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.settings.s3_endpoint,
                    aws_access_key_id=self.settings.s3_access_key,
                    aws_secret_access_key=self.settings.s3_secret_key,
                    region_name=self.settings.s3_region,
                    config=Config(signature_version="s3v4"),
                    use_ssl=self.settings.s3_use_ssl,
                )
            except Exception as exc:  # noqa: BLE001
                raise ConfigurationError(
                    "Object storage is not configured correctly",
                    details={"error": str(exc)},
                ) from exc
        return self._client

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.settings.s3_bucket)
            except (ClientError, BotoCoreError) as exc:
                logger.error("bucket_create_failed", error=str(exc))
                raise AppError(
                    "Unable to access or create object storage bucket",
                    code="storage_error",
                    status_code=503,
                ) from exc

    def upload_bytes(
        self,
        *,
        data: bytes,
        organization_id: str,
        folder: str,
        filename: str,
        content_type: str,
    ) -> tuple[str, str, str]:
        """Upload bytes; returns (bucket, key, sha256)."""
        self.ensure_bucket()
        checksum = hashlib.sha256(data).hexdigest()
        key = f"{organization_id}/{folder}/{uuid4()}/{filename}"
        try:
            self.client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata={"sha256": checksum},
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("upload_failed", error=str(exc))
            raise AppError(
                "Failed to store uploaded file",
                code="storage_error",
                status_code=503,
            ) from exc
        return self.settings.s3_bucket, key, checksum

    def delete_object(self, *, bucket: str, key: str) -> None:
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            logger.warning("storage_delete_failed", error=str(exc), key=key)
            raise AppError(
                "Failed to delete file from storage",
                code="storage_error",
                status_code=503,
            ) from exc

    def download_bytes(self, *, bucket: str, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except (ClientError, BotoCoreError) as exc:
            raise AppError(
                "Failed to retrieve file from storage",
                code="storage_error",
                status_code=503,
            ) from exc

    def upload_fileobj(
        self,
        *,
        fileobj: BinaryIO,
        organization_id: str,
        folder: str,
        filename: str,
        content_type: str,
    ) -> tuple[str, str, str, int]:
        data = fileobj.read()
        bucket, key, checksum = self.upload_bytes(
            data=data,
            organization_id=organization_id,
            folder=folder,
            filename=filename,
            content_type=content_type,
        )
        return bucket, key, checksum, len(data)
