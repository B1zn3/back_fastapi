import mimetypes
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import quote, unquote, urlparse
from uuid import uuid4

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from src.core.config import settings
from src.core.constants import (
    CHAT_ALLOWED_CONTENT_TYPES,
    PROFILE_IMAGE_ALLOWED_CONTENT_TYPES,
    FileErrorMessage,
    StorageFolder,
)


@dataclass(frozen=True)
class StoredFile:
    file_url: str
    object_key: str
    file_name: str
    file_type: Optional[str]
    file_size: int


class FileStorageError(Exception):
    pass


class FileValidationError(ValueError):
    pass


class FileStorageService:
    def __init__(self) -> None:
        self.endpoint_url = settings.s3_endpoint_url_normalized
        self.bucket = settings.S3_BUCKET
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.region = settings.S3_REGION
        self.public_base_url = settings.s3_public_base_url_normalized
        self.default_acl = settings.s3_acl_normalized

        self.chat_max_file_size = settings.chat_max_file_size_bytes
        self.profile_image_max_size = settings.profile_image_max_size_bytes
        self.max_chat_files_per_message = settings.MAX_CHAT_FILES_PER_MESSAGE

        self._validate_settings()

        self._client: Optional[BaseClient] = None

    def _validate_settings(self) -> None:
        required_values = {
            "S3_ENDPOINT_URL": self.endpoint_url,
            "S3_BUCKET": self.bucket,
            "S3_ACCESS_KEY": self.access_key,
            "S3_SECRET_KEY": self.secret_key,
        }

        missing = [
            key
            for key, value in required_values.items()
            if not str(value or "").strip()
        ]

        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing S3 settings: {joined}")

    @property
    def client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )

        return self._client

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        raw_name = filename.strip() or "file"
        raw_name = raw_name.replace("\\", "/").split("/")[-1]

        stem, ext = raw_name.rsplit(".", 1) if "." in raw_name else (raw_name, "")

        stem = re.sub(
            r"[^A-Za-zА-Яа-я0-9._-]+",
            "_",
            stem,
            flags=re.UNICODE,
        ).strip("._-")

        ext = re.sub(
            r"[^A-Za-z0-9]+",
            "",
            ext,
        ).lower()

        if not stem:
            stem = "file"

        if len(stem) > 80:
            stem = stem[:80].rstrip("._-")

        if len(ext) > 12:
            ext = ext[:12]

        return f"{stem}.{ext}" if ext else stem

    @staticmethod
    def _normalize_folder(folder: str) -> str:
        normalized = str(PurePosixPath(folder.strip().strip("/")))

        if normalized in ("", "."):
            raise FileValidationError(FileErrorMessage.INVALID_FOLDER)

        return normalized

    def _build_object_key(
        self,
        *,
        folder: str,
        filename: str,
    ) -> str:
        safe_folder = self._normalize_folder(folder)
        safe_filename = self._sanitize_filename(filename)

        return f"{safe_folder}/{uuid4().hex}_{safe_filename}"

    def _build_file_url(self, object_key: str) -> str:
        encoded_key = quote(object_key, safe="/")

        if self.public_base_url:
            return f"{self.public_base_url}/{encoded_key}"

        return f"{self.endpoint_url}/{self.bucket}/{encoded_key}"

    @staticmethod
    def _guess_content_type(
        file: UploadFile,
        filename: str,
    ) -> str:
        if file.content_type:
            return file.content_type

        guessed, _ = mimetypes.guess_type(filename)

        return guessed or "application/octet-stream"

    @staticmethod
    async def _read_file_with_limit(
        *,
        file: UploadFile,
        max_size: int,
    ) -> bytes:
        content = await file.read(max_size + 1)

        if len(content) > max_size:
            max_size_mb = max_size // 1024 // 1024

            raise FileValidationError(
                f"Файл слишком большой. Максимальный размер: {max_size_mb} МБ"
            )

        if not content:
            raise FileValidationError(FileErrorMessage.EMPTY_FILE)

        return content

    @staticmethod
    def _validate_content_type(
        *,
        content_type: str,
        allowed_content_types: set[str],
    ) -> None:
        if content_type not in allowed_content_types:
            raise FileValidationError(
                f"{FileErrorMessage.INVALID_FILE_TYPE}: {content_type}"
            )

    def _put_object_sync(
        self,
        *,
        object_key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> None:
        extra_args = {
            "Bucket": self.bucket,
            "Key": object_key,
            "Body": content,
            "ContentType": content_type,
            "Metadata": {
                "original-filename": quote(original_filename)[:1024],
            },
        }

        if self.default_acl:
            extra_args["ACL"] = self.default_acl

        self.client.put_object(**extra_args)

    def _delete_object_sync(
        self,
        object_key: str,
    ) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=object_key,
        )

    async def upload_file(
        self,
        *,
        file: UploadFile,
        folder: str,
        allowed_content_types: set[str],
        max_size: int,
    ) -> StoredFile:
        original_filename = file.filename or "file"
        safe_filename = self._sanitize_filename(original_filename)
        content_type = self._guess_content_type(
            file=file,
            filename=safe_filename,
        )

        self._validate_content_type(
            content_type=content_type,
            allowed_content_types=allowed_content_types,
        )

        content = await self._read_file_with_limit(
            file=file,
            max_size=max_size,
        )

        object_key = self._build_object_key(
            folder=folder,
            filename=safe_filename,
        )

        try:
            await run_in_threadpool(
                self._put_object_sync,
                object_key=object_key,
                content=content,
                content_type=content_type,
                original_filename=original_filename,
            )

        except (BotoCoreError, ClientError) as e:
            raise FileStorageError(FileErrorMessage.STORAGE_SAVE_FAILED) from e

        return StoredFile(
            file_url=self._build_file_url(object_key),
            object_key=object_key,
            file_name=original_filename,
            file_type=content_type,
            file_size=len(content),
        )

    async def upload_chat_file(
        self,
        *,
        chat_id: int,
        file: UploadFile,
    ) -> StoredFile:
        return await self.upload_file(
            file=file,
            folder=f"{StorageFolder.CHATS.value}/{chat_id}",
            allowed_content_types=CHAT_ALLOWED_CONTENT_TYPES,
            max_size=self.chat_max_file_size,
        )

    async def upload_company_logo(
        self,
        *,
        company_id: int,
        file: UploadFile,
    ) -> StoredFile:
        return await self.upload_file(
            file=file,
            folder=f"{StorageFolder.COMPANIES.value}/{company_id}/logo",
            allowed_content_types=PROFILE_IMAGE_ALLOWED_CONTENT_TYPES,
            max_size=self.profile_image_max_size,
        )

    async def upload_applicant_photo(
        self,
        *,
        applicant_id: int,
        file: UploadFile,
    ) -> StoredFile:
        return await self.upload_file(
            file=file,
            folder=f"{StorageFolder.APPLICANTS.value}/{applicant_id}/photo",
            allowed_content_types=PROFILE_IMAGE_ALLOWED_CONTENT_TYPES,
            max_size=self.profile_image_max_size,
        )

    def get_object_key_from_url_or_key(
        self,
        value: Optional[str],
    ) -> Optional[str]:
        if not value:
            return None

        raw_value = value.strip()

        if not raw_value:
            return None

        if "://" not in raw_value:
            return raw_value.lstrip("/")

        parsed = urlparse(raw_value)
        path = unquote(parsed.path).lstrip("/")

        if not path:
            return None

        if path.startswith(f"{self.bucket}/"):
            return path[len(self.bucket) + 1 :]

        if self.public_base_url and raw_value.startswith(self.public_base_url):
            public_base_path = urlparse(self.public_base_url).path.strip("/")

            if public_base_path and path.startswith(f"{public_base_path}/"):
                return path[len(public_base_path) + 1 :]

            return path

        return path

    async def delete_file(
        self,
        file_url_or_key: Optional[str],
    ) -> None:
        object_key = self.get_object_key_from_url_or_key(file_url_or_key)

        if not object_key:
            return

        try:
            await run_in_threadpool(
                self._delete_object_sync,
                object_key,
            )

        except (BotoCoreError, ClientError):
            return


file_storage_service = FileStorageService()