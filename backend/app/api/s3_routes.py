from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from app.s3.search import iter_s3_objects
from app.schemas.s3_models import S3ObjectModel
from app.s3.utils import parse_s3_uri

s3_router = APIRouter(prefix="/api/s3", tags=["s3"])

@s3_router.get("/search", response_model=List[S3ObjectModel])
def search_s3(s3_uri: str = Query(..., description="s3://bucket/prefix"), 
              contains: Optional[str] = Query(None, description="Optional substring filter, case sensitive"), 
              limit: int = Query(10, description="Maximum number of results to return")):
    try:
        bucket, prefix = parse_s3_uri(s3_uri)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try: 
        objects = list(iter_s3_objects(bucket=bucket, prefix=prefix, contains=contains, limit=limit))
    
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return objects
