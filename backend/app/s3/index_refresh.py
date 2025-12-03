import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import sys
import meilisearch
import hashlib
from app.s3.utils import get_public_client, parse_s3_uri
from app.schemas.meili_models import MeiliDocumentModel


def get_current_files_from_mock(bucket_name: str) -> List[Dict]:

    path = Path(bucket_name)
    if not path.exists():
        raise FileNotFoundError(f"Bucket '{bucket_name}' not found.")

    with open(path, "r") as f:
        data = json.load(f)

    return data



def refresh_search_index(bucket_name: str, cache_file: str = "index_cache.json"):
    """
    FR6 Prototype Demonstration

    Usage
    -----
    >>> # Refresh bucket search index
    >>> python index_refresh.py <NASA_Bucket_Name>
    """
    
    current_files = get_current_files_from_mock(bucket_name)

    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path, "r") as f:
            previous_files = json.load(f)
    else:
        previous_files = []

    prev_keys = {f["Key"] for f in previous_files}
    curr_keys = {f["Key"] for f in current_files}

    # Detect new and removed files
    new_files = [f for f in current_files if f["Key"] not in prev_keys]
    removed_files = [f for f in previous_files if f["Key"] not in curr_keys]

    # Simulate updating the search index
    if new_files:
        print(f"Found {len(new_files)} new files:")
        for f in new_files:
            print(f"  + {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No new files found.")

    print()

    if removed_files:
        print(f"{len(removed_files)} files removed:")
        for f in removed_files:
            print(f"  - {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No files removed.")

    # Save the new state to disk
    with open(cache_path, "w") as f:
        json.dump(current_files, f, indent=2)


def get_current_s3_objects(bucket_name: str, prefix: Optional[str] = None):
    s3 = get_public_client()
    pager = s3.get_paginator("list_objects_v2")
    objects = []
    try:
        for page in pager.paginate(Bucket=bucket_name, Prefix=prefix if prefix is not None else ""):
            for obj in page.get("Contents", []):
                objects.append(obj)
    except Exception as e:
        print("Error fetching s3 objects:", e)

    return objects


def refresh_meili_index(bucket_name: str, prefix: Optional[str] = None):
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    current_files = get_current_s3_objects(bucket_name, prefix)

    indexObjs = get_all_indexes()
    indexes = {f["uid"] for f in indexObjs}

    if bucket_name in indexes:
        prev_documents = get_all_documents(bucket_name, prefix)
        
        prev_keys = [getattr(f, "Key") for f in prev_documents]
        curr_keys = [f["Key"] for f in current_files]

        # Detect new and removed files
        new_files = [f for f in current_files if f["Key"] not in prev_keys]
        removed_files = [f for f in prev_keys if f not in curr_keys]

        if new_files:
            print(f"Adding {len(new_files)} new files to the index \"{bucket_name}\"")
            add_files_to_index(bucket_name, new_files)
        else:
            print("No new files found.")

        if removed_files:
            print(f"Removing {len(removed_files)} from the index \"{bucket_name}\"")
            remove_files_from_index(bucket_name, removed_files)
        else:
            print("No files removed.")
    else:
        # index doesn't exist, create a new index
        # object key includes invalid characters for primary key, create a hash of the key to use as the primary key instead
        # NOTE: this means that in order to access a specific document by key you must hash it first using get_doc_id
        meili_client.create_index(bucket_name, {"primaryKey": "ID"})
        meili_client.index(bucket_name).update_settings({
            "searchableAttributes": ["Tags", "Key", "Keywords"], # sorted in order of importance
            "filterableAttributes": ["ContentType", "Size", "StorageClass", "LastModified", "Prefix"],
            "sortableAttributes": ["Size", "LastModified"],
        })
        add_files_to_index(bucket_name, current_files)


def add_files_to_index(index: str, new_files: List):
    s3 = get_public_client()
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    # TODO: look into parallelizing this loop to speed up indexing 
    #  (most of the time cost is in meilisearch so doing this probably won't result in much speedup)

    for file in new_files:
        key = file["Key"]
        hashed_key = get_doc_id(key)
        head = s3.head_object(Bucket=index, Key=key)
        size = file["Size"]
        storage_class = file["StorageClass"]
        ctype = head.get("ContentType", "unknown")
        last_modified = int(file["LastModified"].timestamp())
        keywords = get_keywords_from_key(key)
        tags = [] # empty user tag array
        prefixList = key.split("/")
        if len(prefixList) > 1: prefix = prefixList[0]
        else: prefix = None

        # TODO: if file has text content, extract text and add to keywords array
        
        new_document: MeiliDocumentModel = {
                        "ID": hashed_key,
                        "Key": key,
                        "LastModified": last_modified,
                        "Size": size,
                        "StorageClass": storage_class,
                        "ContentType": ctype,
                        "Keywords": keywords,
                        "Tags": tags,
                        "Prefix": prefix
                        }
        meili_client.index(index).add_documents([new_document])


def remove_files_from_index(index: str, removed_keys: List[str]):
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    for key in removed_keys:
        hashed_key = get_doc_id(key)
        meili_client.index(index).delete_document(hashed_key)


# TODO: move meilisearch utility functions to their own file
def get_doc_id(key: str):
    hash_object = hashlib.sha256(key.encode())
    hex_dig = hash_object.hexdigest()
    return(f"{hex_dig}")


def get_keywords_from_key(key: str):
    replacements = str.maketrans({"/": ",", "_": ",", "-": ",", " ":",", ".": ","})
    key = key.translate(replacements)
    keywords = list(set(key.split(",")))
    if keywords.count("") > 0: keywords.remove("")
    return keywords


def get_all_indexes():
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    limit = 20
    offset = 0
    total: int | None = None
    indexObjs = []
    while total is None or offset < total:
        temp = meili_client.get_raw_indexes({"limit": limit, "offset": offset})
        if total is None: total = temp["total"]
        offset += limit
        indexObjs.extend(temp["results"])

    return indexObjs

def get_all_documents(index: str, prefix: Optional[str] = None):
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
        if prefix is not None and prefix != "": get_query["filter"] = f"Prefix={prefix}"

        temp = meili_client.index(index).get_documents(get_query)
        if total is None: total = temp.total
        offset += limit
        documentObjs.extend(temp.results)

    return documentObjs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python index_refresh.py <bucket_name>")
        sys.exit(1)

    bucket_name = sys.argv[1]
    refresh_search_index(bucket_name)
