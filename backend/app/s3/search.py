import os
from typing import Iterator, Optional, Dict, Any
from datetime import datetime
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
import meilisearch
from app.s3.utils import get_public_client

# temp fix to "contains" problem
SUFFIX_TO_CONTENT_TYPES = {"pdf": "application/pdf", 
                           "png": "image/png", 
                           "jpg": "image/jpg", 
                           "zip": "application/zip"}

def iter_s3_objects(bucket: str, 
                    prefix: str, 
                    contains: Optional[str] = None, 
                    limit: int = 10, 
                    s3: Optional[BaseClient] = None, 
                    min_size: Optional[int] = None, 
                    max_size: Optional[int] = None, 
                    storage_classes: Optional[list[str]] = None, 
                    modified_after: Optional[datetime] = None, 
                    modified_before: Optional[datetime] = None, 
                    suffixes: Optional[list[str]] = None) -> Iterator[Dict[str, Any]]:
    if s3 is None:
        s3 = get_public_client()

    pager = s3.get_paginator("list_objects_v2")
    yielded = 0

    try:
        for page in pager.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                size = obj["Size"]
                last_modified = obj.get("LastModified")
                storage_class = obj.get("StorageClass")

                if not filter_s3_objects(key=key, 
                                         size=size, 
                                         last_modified=last_modified, 
                                         storage_class=storage_class, 
                                         contains=contains, 
                                         min_size=min_size, 
                                         max_size=max_size, 
                                         storage_classes=storage_classes, 
                                         modified_after=modified_after, 
                                         modified_before=modified_before, 
                                         suffixes=suffixes):
                    continue

                last_modified_out = (
                    last_modified.isoformat()
                    if isinstance(last_modified, datetime)
                    else last_modified
                )

                yield {"key": key, 
                       "size": size, 
                       "last_modified": last_modified_out, 
                       "storage_class": storage_class}
                yielded += 1
                if yielded >= limit:
                    return
                
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 listing failed: {e}") from e
    
def filter_s3_objects(key: str, 
                      size: int, 
                      last_modified: Optional[datetime] = None, 
                      storage_class: Optional[str] = None, 
                      contains: Optional[str] = None, 
                      min_size: Optional[int] = None, 
                      max_size: Optional[int] = None, 
                      storage_classes: Optional[list[str]] = None, 
                      modified_after: Optional[datetime] = None, 
                      modified_before: Optional[datetime] = None, 
                      suffixes: Optional[list[str]] = None) -> bool:
    if contains and contains not in key:
        return False
    
    if suffixes and not any(key.endswith(suffix) for suffix in suffixes):
        return False
    
    if min_size is not None and size < min_size:
        return False
    if max_size is not None and size > max_size:
        return False
    
    if storage_classes and (storage_class not in storage_classes):
        return False
    
    if isinstance(last_modified, datetime):
        if modified_after and last_modified < modified_after:
            return False
        if modified_before and last_modified > modified_before:
            return False
        
    return True
    
def search_from_meili(bucket: str, 
                      prefix: str, 
                      contains: Optional[str] = None, 
                      limit: int = 10, 
                      min_size: Optional[int] = None, 
                      max_size: Optional[int] = None, 
                      storage_classes: Optional[list[str]] = None, 
                      modified_after: Optional[datetime] = None, 
                      modified_before: Optional[datetime] = None, 
                      suffixes: Optional[list[str]] = None) -> list[Dict[str, Any]]:
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    filter_arr = []
    if prefix is not None and prefix != "":
        prefix = prefix.split("/")[0]
        filter_arr.append(f"Prefix={prefix}")

    if min_size is not None:
        filter_arr.append(f"Size>={min_size}")

    if max_size is not None:
        filter_arr.append(f"Size<={max_size}")

    if storage_classes is not None and len(storage_classes) > 0:
        storage_classes = [f"StorageClass={storage_class}" for storage_class in storage_classes]
        filter_arr.append(" OR ".join(storage_classes))

    if modified_after is not None:
        timestamp = modified_after.timestamp()
        filter_arr.append(f"LastModified>={timestamp}")
    
    if modified_before is not None:
        timestamp = modified_before.timestamp()
        filter_arr.append(f"LastModified<={timestamp}")

    if suffixes is not None:
        content_types = {SUFFIX_TO_CONTENT_TYPES.get(suffix.lower()) for suffix in suffixes if suffix is not None}
        
        if len(content_types) == 1:
            only_type = next(iter(content_types))
            filter_arr.append(f"ContentType='{only_type}'")
        else:
            types_list = ", ".join(f"'{ctype}'" for ctype in sorted(content_types))
            filter_arr.append(f"ContentType IN [{types_list}]")

    documents = meili_client.index(bucket).search(
        contains if contains is not None else "",
        {'filter': filter_arr,
         'limit': limit})

    objects = []
    for document in documents["hits"]:
        last_modified_out = datetime.fromtimestamp(int(document["LastModified"]))

        objects.append({
            "key": document["Key"], 
            "size": document["Size"], 
            "last_modified": last_modified_out, 
            "storage_class": document["StorageClass"]
        })

    return objects