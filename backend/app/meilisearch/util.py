"""util.py

Meilisearch and MIME-type helper functions used by backend services."""

import hashlib
import mimetypes
import os
from typing import Optional

import meilisearch
import psycopg

from app.s3.utils import build_subtree_filter, normalize_s3_path


def get_doc_id(key: str):
    """Return stable SHA-256 hex identifier for an S3 object key."""
    hash_object = hashlib.sha256(key.encode())
    hex_dig = hash_object.hexdigest()
    return (f"{hex_dig}")


def get_all_indexes():
    """Fetch all Meilisearch index metadata using paginated requests."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    limit = 20
    offset = 0
    total: int | None = None
    indexObjs = []
    while total is None or offset < total:
        temp = meili_client.get_raw_indexes({"limit": limit, "offset": offset})
        if total is None:
            total = temp["total"]
        offset += limit
        indexObjs.extend(temp["results"])

    return indexObjs


def get_all_documents(index: str, prefix: Optional[str] = None):
    """Fetch all document keys for an index, optionally filtered by prefix subtree."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    limit = 100
    offset = 0
    total: int | None = None
    documentObjs = []

    while total is None or offset < total:
        get_query = {
            "fields": ["Key"],
            "limit": limit,
            "offset": offset
        }
        if prefix is not None and prefix != "":
            norm_prefix = normalize_s3_path(prefix)
            get_query["filter"] = build_subtree_filter(norm_prefix)

        temp = meili_client.index(index).get_documents(get_query)
        if total is None:
            total = temp.total
        offset += limit
        documentObjs.extend(temp.results)

    return documentObjs


def guess_mime_type(extension: str):
    """Resolve MIME type from custom DB overrides, then Python mimetype fallback."""
    postgres_url = os.getenv("DATABASE_URL")
    with psycopg.connect(postgres_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT * FROM custom_mime_types""")
            custom_types = [type for type in cur.fetchall()]

    if extension in [m[0] for m in custom_types]:
        mime_type = custom_types[[m[0]
                                  for m in custom_types].index(extension)][1]
    else:
        mime_type = mimetypes.guess_type(f"f.{extension}", False)[0]
    if mime_type == "None" or mime_type == None:
        return "binary/octet-stream"
    else:
        return mime_type
