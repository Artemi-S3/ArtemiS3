from typing import Iterator, Optional, Dict, Any
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from app.s3.utils import get_public_client

def iter_s3_objects(bucket: str, 
                    prefix: str, 
                    contains: Optional[str] = None, 
                    limit: int = 10, 
                    s3: Optional[BaseClient] = None) -> Iterator[Dict[str, Any]]:
    if s3 is None:
        s3 = get_public_client()

    pager = s3.get_paginator("list_objects_v2")
    yielded = 0

    try:
        for page in pager.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if contains and contains not in key:
                    continue

                yield {"key": key, 
                       "size": obj["Size"], 
                       "last_modified": obj.get("LastModified"), 
                       "storgae_class": obj.get("StorageClass")}
                yielded += 1
                if yielded >= limit:
                    return
                
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 listing failed: {e}") from e
    