"""Superfície de armazenamento de arquivo do `core`. É daqui que um módulo guarda e lê bytes,
sem conhecer o provedor."""

from src.core.storage.objects import (
    LocalDirectoryStorage,
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageDep,
    S3ObjectStorage,
    get_object_storage,
)

__all__ = [
    "LocalDirectoryStorage",
    "ObjectNotFoundError",
    "ObjectStorage",
    "ObjectStorageDep",
    "S3ObjectStorage",
    "get_object_storage",
]
