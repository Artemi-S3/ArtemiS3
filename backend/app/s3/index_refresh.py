"""index_refresh.py

Meilisearch index refresh pipeline for S3 buckets and prefixes."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
import os
from typing import List, Optional
import fitz
import meilisearch

import psycopg
from app.s3.refresh_status import (
    start_refresh,
    set_status,
    increment_listed,
    increment_processed,
    finish_refresh,
    fail_refresh
)
from app.s3.utils import (
    get_public_client,
    normalize_s3_path,
    key_parent_path,
    key_filename,
    parent_ancestors,
    path_depth,
)
from app.schemas.meili_models import MeiliDocumentModel
from app.meilisearch.util import get_all_documents, get_all_indexes, get_doc_id, guess_mime_type


# List of supported text file types for full-text indexing
TEXT_CONTENT_TYPES = ["text/plain", "text/css", "text/csv", "text/xml", "application/xml"
                      "text/html", "text/markdown", "application/json", "text/lbl", "text/lab"]
# Keyword parsing separation characters
SEPARATION_CHARACTERS = ["/", ",", "_", "-", " ", ".", "\n",
                         ":", "\\", "(", ")", "[", "]", "=", ";", "—", "*", "\""]
INDEX_SETTINGS = {
    "rankingRules": ["sort", "words", "typo", "proximity", "attribute", "exactness"],
    "searchableAttributes": ["Tags", "FileName", "Key", "Keywords"],
    "filterableAttributes": [
        "ContentType", "Size", "StorageClass", "LastModified",
        "ParentPath", "Ancestors", "Depth"
    ],
    "sortableAttributes": ["Key", "Size", "LastModified"]
}


def config_index_settings(index_obj: meilisearch.Client) -> None:
    """Apply standard ArtemiS3 index settings to a Meilisearch index."""
    index_obj.update_settings(INDEX_SETTINGS)


def get_current_s3_objects(bucket_name: str, prefix: Optional[str] = None, s3_uri: Optional[str] = None):
    """List current S3 objects under a bucket/prefix and track listing progress."""
    s3 = get_public_client()
    pager = s3.get_paginator("list_objects_v2")
    objects = []
    try:
        for page in pager.paginate(Bucket=bucket_name, Prefix=prefix or ""):
            contents = page.get("Contents", [])
            objects.extend(contents)
            if s3_uri is not None:
                increment_listed(s3_uri, len(contents))
    except Exception as e:
        print("Error fetching s3 objects:", e)

    return objects


def refresh_meili_index(bucket_name: str, prefix: Optional[str] = None, s3_uri: Optional[str] = None) -> None:
    """Synchronize Meilisearch documents with current S3 state for a target URI."""
    # start tracking at object listing
    if s3_uri is not None:
        start_refresh(s3_uri, total=0, status="listing")

    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    current_files = get_current_s3_objects(bucket_name, prefix, s3_uri=s3_uri)

    index_objs = get_all_indexes()
    indexes = {f["uid"] for f in index_objs}

    if bucket_name in indexes:
        prev_documents = get_all_documents(bucket_name, prefix)

        prev_keys = [getattr(f, "Key") for f in prev_documents]
        curr_keys = [f["Key"] for f in current_files]

        # Detect new and removed files
        new_files = [f for f in current_files if f["Key"] not in prev_keys]
        removed_files = [f for f in prev_keys if f not in curr_keys]

        # compute total work up front
        total = len(new_files) + len(removed_files)

    else:
        new_files = current_files
        removed_files = []
        total = len(new_files)

    # track actual refresh
    if s3_uri is not None:
        set_status(s3_uri, status="running", total=total, reset_processed=True)

    try:
        if bucket_name in indexes:
            idx = meili_client.index(bucket_name)
            config_index_settings(idx)

            if new_files:
                add_files_to_index(bucket_name, new_files, s3_uri=s3_uri)
            if removed_files:
                remove_files_from_index(
                    bucket_name, removed_files, s3_uri=s3_uri)

        else:
            # index doesn't exist, create a new index
            # object key includes invalid characters for primary key, create a hash of the key to use as the primary key instead
            # NOTE: this means that in order to access a specific document by key you must hash it first using get_doc_id
            meili_client.create_index(bucket_name, {"primaryKey": "ID"})
            idx = meili_client.index(bucket_name)
            config_index_settings(idx)
            add_files_to_index(bucket_name, current_files, s3_uri=s3_uri)

        if s3_uri is not None:
            finish_refresh(s3_uri)

    except Exception as e:
        if s3_uri is not None:
            fail_refresh(s3_uri, str(e))
        raise


def create_document(index: str, file, meili_client: meilisearch.Client, dbTags: dict[str, tuple], s3_uri: Optional[str] = None) -> None:
    """Create and insert one Meilisearch document from a single S3 object."""
    s3 = get_public_client()

    # prefixing logic to handle folders
    raw_key = file["Key"]
    if raw_key.endswith("/"):
        if s3_uri is not None:
            increment_processed(s3_uri, 1)
        return

    norm_key = normalize_s3_path(raw_key)
    hashed_key = get_doc_id(raw_key)
    head = s3.head_object(Bucket=index, Key=raw_key)
    size = file["Size"]
    storage_class = file.get("StorageClass", "STANDARD")
    ctype = head.get("ContentType", "unknown")
    last_modified = int(file["LastModified"].timestamp())
    file_name = key_filename(norm_key)
    parent_path = key_parent_path(norm_key)
    ancestors = parent_ancestors(parent_path)
    depth = path_depth(parent_path)
    tags = dbTags[hashed_key][2] if hashed_key in dbTags else []
    keywords = []

    if ctype == "binary/octet-stream":
        ctype = guess_mime_type(norm_key.split(".")[-1])

    if ctype in TEXT_CONTENT_TYPES:
        keywords = get_keywords_from_text(index, raw_key)
    elif ctype == "application/pdf":
        keywords = get_keywords_from_pdf(index, raw_key)

    if len(keywords) == 0:
        keywords = get_keywords_from_key(raw_key)

    new_document: MeiliDocumentModel = {
        "ID": hashed_key,
        "Key": raw_key,
        "FileName": file_name,
        "ParentPath": parent_path,
        "Ancestors": ancestors,
        "Depth": depth,
        "LastModified": last_modified,
        "Size": size,
        "StorageClass": storage_class,
        "ContentType": ctype,
        "Keywords": keywords,
        "Tags": tags
    }
    meili_client.index(index).add_documents([new_document])
    if s3_uri is not None:
        increment_processed(s3_uri, 1)


def add_files_to_index(index: str, new_files: List, s3_uri: Optional[str] = None) -> None:
    """Insert a batch of new S3 objects into the Meilisearch index."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    postgres_url = os.getenv("DATABASE_URL")

    with psycopg.connect(postgres_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM file_tags WHERE bucket=%s""", (index,))
            dbTags = {record[0]: record for record in cur.fetchall()}

    create_with_args = partial(
        create_document, index, meili_client=meili_client, dbTags=dbTags, s3_uri=s3_uri)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(create_with_args, new_files)


def remove_files_from_index(index: str, removed_keys: List[str], s3_uri: Optional[str] = None) -> None:
    """Delete removed objects from Meilisearch and remove their stored tags."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)
    postgres_url = os.getenv("DATABASE_URL")

    with psycopg.connect(postgres_url) as conn:
        with conn.cursor() as cur:
            for key in removed_keys:
                hashed_key = get_doc_id(key)
                meili_client.index(index).delete_document(hashed_key)
                cur.execute(
                    """DELETE FROM file_tags WHERE hashed_key=%s""", (hashed_key,))
                if s3_uri is not None:
                    increment_processed(s3_uri, 1)


def get_keywords_from_key(key: str):
    """Extract coarse keyword tokens from a key or text blob."""
    replacements = str.maketrans({char: "," for char in SEPARATION_CHARACTERS})
    key = key.translate(replacements)
    keywords = list(set(key.split(",")))
    if keywords.count("") > 0:
        keywords.remove("")
    return keywords


def get_keywords_from_text(index: str, key: str):
    """Read text content from S3 and derive capped keyword tokens for indexing."""
    s3 = get_public_client()
    keywords = []
    try:
        response = s3.get_object(Bucket=index, Key=key)
        text_content = response["Body"].read().decode("utf-8")
        keywords = get_keywords_from_key(text_content)
    except Exception as e:
        print(f"Error extracting text content from {key}", e)
        keywords = get_keywords_from_key(key)
    # only read up to 500 words to prevent index bloating on large text files
    return keywords[:500]


def get_keywords_from_pdf(index: str, key: str):
    """Extract keyword tokens from PDF text content stored in S3."""
    s3 = get_public_client()
    keywords = []
    try:
        response = s3.get_object(Bucket=index, Key=key)
        pdf_stream = response["Body"].read()
        pdf_document = fitz.open("application/pdf", pdf_stream)
        for page in pdf_document:
            text = page.get_text("text")
            if text:
                keywords.extend(get_keywords_from_key(text))
            if len(keywords) > 500:
                break

    except Exception as e:
        print(f"Error extracting text content from {key}: {e}")
        keywords = get_keywords_from_key(key)
    return keywords[:500]
