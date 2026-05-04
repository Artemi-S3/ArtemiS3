"""meili_models.py

Pydantic models for Meilisearch documents and tag update requests."""

from pydantic import BaseModel
from typing import List, Optional

# NOTE: if you change the model, you must delete all of the indexes and reindex everything for the changes to be present


class MeiliDocumentModel(BaseModel):
    """Canonical Meilisearch document shape for indexed S3 objects."""
    ID: str
    Key: str
    FileName: str
    ParentPath: str
    Ancestors: List[str]
    Depth: int
    Size: int
    LastModified: str
    ContentType: str
    StorageClass: str
    Keywords: List[str]
    Tags: List[str]
    # Prefix: Optional[str] = None


class TagRequest(BaseModel):
    """Payload for object tag updates routed through backend API."""
    bucket: str
    key: str
    tags: List[str]
