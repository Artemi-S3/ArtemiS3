from typing import Optional, List, Sequence
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from app.s3.search import iter_s3_objects
from app.schemas.s3_models import S3ObjectModel
from app.s3.utils import parse_s3_uri

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
    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try: 
        objects = list(iter_s3_objects(bucket=bucket, 
                                       prefix=prefix, 
                                       contains=contains, 
                                       siffixes=suffixes, 
                                       min_size=min_size, 
                                       max_size=max_size, 
                                       storage_classes=storage_classes, 
                                       modified_after=modified_after, 
                                       modified_before=modified_before,
                                       limit=limit))
    
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return objects
