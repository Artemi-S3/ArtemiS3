import os
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import meilisearch
from botocore.exceptions import ClientError
from app.s3.search import iter_s3_objects, search_from_meili
from app.schemas.s3_models import S3ObjectModel
from app.s3.utils import parse_s3_uri, get_public_client
from app.s3.index_refresh import refresh_meili_index

s3_router = APIRouter(prefix="/api/s3", tags=["s3"])

@s3_router.get("/search", response_model=List[S3ObjectModel])
def search_s3(s3_uri: str = Query(..., description="s3://bucket/prefix"), 
              contains: Optional[str] = None,
              suffixes: Optional[List[str]] = Query(None, description="Allowed file suffixes like .txt, .pdf"),
              min_size: Optional[int] = Query(None, description="Minimum file size in bytes"),
              max_size: Optional[int] = Query(None, description="Maximum file size in bytes"),
              storage_classes: Optional[List[str]] = Query(None, description="Allowed storage classes"),
              modified_after: Optional[datetime] = Query(None),
              modified_before: Optional[datetime] = Query(None),
              limit: int = Query(10, description="Maximum number of results to return")):
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    
    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
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
                                        limit=limit)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

    except:
        print("Index Doesn't Exist, running manual search")
        try: 
            objects = list(iter_s3_objects(bucket=bucket, 
                                        prefix=prefix, 
                                        contains=contains, 
                                        suffixes=suffixes, 
                                        min_size=min_size, 
                                        max_size=max_size, 
                                        storage_classes=storage_classes, 
                                        modified_after=modified_after, 
                                        modified_before=modified_before,
                                        limit=limit))
        
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

    return objects

@s3_router.get("/refresh")
def refresh_index(s3_uri: str):
    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    refresh_meili_index(bucket_name=bucket, prefix=prefix)

@s3_router.get("/download")
def download_file(s3_uri: str = Query(..., description="s3://bucket/key")):
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
