"""s3_routes.py

HTTP routes for S3 search, navigation, preview, download, and tagging."""

import os
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import meilisearch
from botocore.exceptions import ClientError
import psycopg
from app.s3.search import (
    iter_s3_objects,
    search_from_meili,
    search_folders_from_meili,
    list_folder_children_from_meili
)
from app.schemas.s3_models import (
    S3ObjectModel,
    S3FolderModel,
    S3FolderChildrenResponse
)
from app.s3.utils import (
    parse_s3_uri,
    get_public_client,
    generate_preview_url
)
from app.s3.refresh_status import get_status
from app.schemas.meili_models import TagRequest
from app.meilisearch.util import get_doc_id

s3_router = APIRouter(prefix="/api/s3", tags=["s3"])


@s3_router.get("/search", response_model=List[S3ObjectModel])
def search_s3(s3_uri: str = Query(..., description="s3://bucket/prefix"),
              contains: Optional[str] = None,
              suffixes: Optional[List[str]] = Query(
                  None, description="Allowed file suffixes like .txt, .pdf"),
              min_size: Optional[int] = Query(
                  None, description="Minimum file size in bytes"),
              max_size: Optional[int] = Query(
                  None, description="Maximum file size in bytes"),
              storage_classes: Optional[List[str]] = Query(
                  None, description="Allowed storage classes"),
              modified_after: Optional[datetime] = Query(None),
              modified_before: Optional[datetime] = Query(None),
              limit: int = Query(
                  10, ge=1, le=1000, description="Maximum number of results to return"),
              sort_by: Optional[str] = Query(
                  None, description="Key | Size | LastModified"),
              sort_direction: str = Query("asc", description="asc | desc")):
    """Search indexed or live S3 objects with optional filters and sorting."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    try:
        bucket, prefix = parse_s3_uri(s3_uri)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if sort_direction not in ("asc", "desc"):
        sort_direction = "asc"

    if sort_by not in ("Key", "Size", "LastModified"):
        sort_by = None

    # Meilisearch
    objects = []
    try:
        meili_client.get_index(bucket)
        print("Index Exists, retrieving from index")

        try:
            objects = search_from_meili(bucket=bucket,
                                        prefix=prefix,
                                        contains=contains,
                                        suffixes=suffixes,
                                        min_size=min_size,
                                        max_size=max_size,
                                        storage_classes=storage_classes,
                                        modified_after=modified_after,
                                        modified_before=modified_before,
                                        limit=limit,
                                        sort_by=sort_by,
                                        sort_direction=sort_direction
                                        )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        print("Index Doesn't Exist, running manual search", e)
        try:
            objects = list(iter_s3_objects(
                bucket=bucket,
                prefix=prefix,
                contains=contains,
                suffixes=suffixes,
                min_size=min_size,
                max_size=max_size,
                storage_classes=storage_classes,
                modified_after=modified_after,
                modified_before=modified_before,
                limit=limit
            ))

        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

    return objects


@s3_router.get("/folders/search", response_model=List[S3FolderModel])
def search_s3_folders(s3_uri: str = Query(..., description="s3://bucket/prefix"),
                      contains: Optional[str] = Query(
                          None, description="Optional folder relevance query"),
                      limit: int = Query(25, ge=1, le=500)):
    """Return relevant folder candidates for a bucket/prefix query."""
    meili_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meili_url)

    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        meili_client.get_index(bucket)
    except Exception:
        raise HTTPException(
            status_code=404, detail="Meilisearch index not found for this bucket. Run refresh first.")

    try:
        return search_folders_from_meili(
            bucket=bucket,
            prefix=prefix,
            contains=contains,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@s3_router.get("/folders/children", response_model=S3FolderChildrenResponse)
def list_s3_folder_children(s3_uri: str = Query(..., description="s3://bucket/prefix"),
                            path: Optional[str] = Query(
                                None, description="Folder path within bucket"),
                            contains: Optional[str] = Query(
                                None, description="Optional folder relevance query"),
                            limit: int = Query(100, ge=1, le=500),
                            sort_by: Optional[str] = Query(
                                None, description="Key | Size | LastModified"),
                            sort_direction: str = Query("asc", description="asc | desc")):
    """Return direct child folders/files and breadcrumbs for a folder path."""
    meili_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meili_url)

    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if sort_direction not in {"asc", "desc"}:
        sort_direction = "asc"

    if sort_by not in ("Key", "Size", "LastModified"):
        sort_by = None

    try:
        meili_client.get_index(bucket)
    except Exception:
        raise HTTPException(
            status_code=404, detail="Meilisearch index not found for this bucket. Run refresh first.")

    try:
        return list_folder_children_from_meili(
            bucket=bucket,
            prefix=prefix,
            path=path,
            contains=contains,
            limit=limit,
            sort_by=sort_by,
            sort_direction=sort_direction
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@s3_router.get("/refresh/status")
def refresh_status(s3_uri: str = Query(..., description="s3://bucket/prefix")):
    """Return current refresh progress status for a configured S3 URI."""
    try:
        # only for validation
        parse_s3_uri(s3_uri)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return get_status(s3_uri)


@s3_router.get("/download")
def download_file(s3_uri: str = Query(..., description="s3://bucket/key")):
    """Stream an S3 object as an attachment response."""
    try:
        bucket, key = parse_s3_uri(s3_uri)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        s3_client = get_public_client()
        obj = s3_client.get_object(Bucket=bucket, Key=key)

    except ClientError:
        raise HTTPException(status_code=404, detail="Object not found")

    body = obj["Body"]
    content_type = obj.get("ContentType", "application/octet-stream")
    filename = key.split("/")[-1] or "file"

    return StreamingResponse(body, media_type=content_type,
                             headers={
                                 "Content-Disposition": f"attachment; filename={filename}"
                             })


@s3_router.get("/preview")
def s3_preview(bucket: str, key: str):
    """Return a temporary preview URL for an S3 object."""
    url = generate_preview_url(bucket, key)
    if not url:
        raise HTTPException(status_code=400, detail="Failed to generate URL")
    return {"preview_url": url}


@s3_router.post("/tag")
def edit_tags(data: TagRequest):
    """Update tags in Meilisearch and persist them in Postgres."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    postgres_url = os.getenv("DATABASE_URL")
    doc_id = get_doc_id(data.key)

    # add tags to index
    try:
        index = meili_client.get_index(data.bucket)
        index.update_documents([{
            "ID": doc_id,
            "Tags": data.tags
        }])
        # NOTE skip_creation=True not available in current version,
        # we should update the meilisearch client when we get the change so that this function is not able to create new documents

    except Exception:
        raise HTTPException(
            status_code=500, detail="Error encountered while editing tags. Check that the meilisearch index and document exist.")

    # store tags in db
    try:
        with psycopg.connect(postgres_url) as conn:
            with conn.cursor() as cur:
                if len(data.tags) > 0:
                    cur.execute("""INSERT INTO file_tags (hashed_key, bucket, tags) VALUES (%s, %s, %s) 
                                ON CONFLICT (hashed_key) DO UPDATE SET tags = EXCLUDED.tags""",
                                (doc_id, data.bucket, data.tags))
                else:
                    cur.execute(
                        """DELETE FROM file_tags WHERE hashed_key=%s""", (doc_id,))

    except Exception:
        raise HTTPException(
            status_code=500, detail="Error encountered while storing tags to database."
        )
