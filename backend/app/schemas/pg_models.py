"""pg_models.py

Pydantic models for Postgres-backed tag and MIME configuration records."""

from pydantic import BaseModel


class TagRecord(BaseModel):
    """Persisted file-tag record keyed by hashed object identifier."""
    hashed_key: str
    bucket: str
    tags: list[str]


class MimeRecord(BaseModel):
    """Custom MIME type mapping payload for one file extension."""
    extension: str
    mime_type: str
