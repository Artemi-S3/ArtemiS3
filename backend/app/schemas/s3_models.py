"""s3_models.py

Pydantic response models for S3 file and folder API payloads."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class S3ObjectModel(BaseModel):
    """Serialized representation of one S3 object in search responses."""
    key: str
    size: int
    last_modified: Optional[datetime] = None
    storage_class: Optional[str] = None
    tags: Optional[List[str]] = None


class S3FolderModel(BaseModel):
    """Serialized folder candidate returned by folder search endpoints."""
    path: str
    name: str
    depth: int
    matched_count: int


class S3BreadcrumbModel(BaseModel):
    """One breadcrumb segment used for folder navigation responses."""
    path: str
    name: str


class S3FolderChildrenResponse(BaseModel):
    """Folder navigation payload including breadcrumbs, children, and files."""
    path: str
    breadcrumbs: List[S3BreadcrumbModel]
    children: List[S3FolderModel]
    files: List[S3ObjectModel]
