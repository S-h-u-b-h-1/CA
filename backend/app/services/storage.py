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
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(self, file_name: str, file_content: bytes) -> str:
        # Resolve clean path
        file_path = os.path.join(self.upload_dir, file_name)
        # Ensure containing directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    def read_file(self, file_path: str) -> bytes:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found in local storage: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    else:
        # Default fallback
        return LocalStorageProvider()
