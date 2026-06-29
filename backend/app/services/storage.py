import os
from abc import ABC, abstractmethod
from app.core.config import settings

class StorageProvider(ABC):
    @abstractmethod
    def save_file(self, file_name: str, file_content: bytes) -> str:
        """Save a file and return its storage path/URI"""
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """Read a file from storage and return its bytes"""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, upload_dir: str = None):
        self.upload_dir = upload_dir or settings.LOCAL_STORAGE_DIR
        if os.environ.get("VERCEL") == "1":
            self.upload_dir = "/tmp"
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(self, file_name: str, file_content: bytes) -> str:
        file_path = os.path.join(self.upload_dir, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    def read_file(self, file_path: str) -> bytes:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found in local storage: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()


class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION

    def save_file(self, file_name: str, file_content: bytes) -> str:
        # Mock S3 uploading path. In production, this would call boto3 client
        # client.put_object(Bucket=self.bucket, Key=file_name, Body=file_content)
        mock_uri = f"s3://{self.bucket or 'caintelligence-bucket'}/{file_name}"
        # For mock compatibility, write locally as a fallback
        local_fallback = LocalStorageProvider()
        local_fallback.save_file(file_name, file_content)
        return mock_uri

    def read_file(self, file_path: str) -> bytes:
        # Mock S3 downloading. If mock, fall back to local disk read
        local_fallback = LocalStorageProvider()
        file_name = os.path.basename(file_path)
        return local_fallback.read_file(os.path.join(local_fallback.upload_dir, file_name))


class SupabaseStorageProvider(StorageProvider):
    def save_file(self, file_name: str, file_content: bytes) -> str:
        mock_uri = f"supabase://storage/buckets/documents/{file_name}"
        local_fallback = LocalStorageProvider()
        local_fallback.save_file(file_name, file_content)
        return mock_uri

    def read_file(self, file_path: str) -> bytes:
        local_fallback = LocalStorageProvider()
        file_name = os.path.basename(file_path)
        return local_fallback.read_file(os.path.join(local_fallback.upload_dir, file_name))


class AzureStorageProvider(StorageProvider):
    def save_file(self, file_name: str, file_content: bytes) -> str:
        mock_uri = f"azure://blob/container/documents/{file_name}"
        local_fallback = LocalStorageProvider()
        local_fallback.save_file(file_name, file_content)
        return mock_uri

    def read_file(self, file_path: str) -> bytes:
        local_fallback = LocalStorageProvider()
        file_name = os.path.basename(file_path)
        return local_fallback.read_file(os.path.join(local_fallback.upload_dir, file_name))


class GCSStorageProvider(StorageProvider):
    def save_file(self, file_name: str, file_content: bytes) -> str:
        mock_uri = f"gs://caintelligence-bucket/documents/{file_name}"
        local_fallback = LocalStorageProvider()
        local_fallback.save_file(file_name, file_content)
        return mock_uri

    def read_file(self, file_path: str) -> bytes:
        local_fallback = LocalStorageProvider()
        file_name = os.path.basename(file_path)
        return local_fallback.read_file(os.path.join(local_fallback.upload_dir, file_name))


def get_storage_provider() -> StorageProvider:
    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "s3":
        return S3StorageProvider()
    elif provider == "supabase":
        return SupabaseStorageProvider()
    elif provider == "azure":
        return AzureStorageProvider()
    elif provider == "gcs":
        return GCSStorageProvider()
    else:
        return LocalStorageProvider()
