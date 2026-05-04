"""search.py

S3 object and folder search helpers backed by Meilisearch or live S3 APIs."""

import os
from typing import Iterator, Optional, Dict, Any, List
from datetime import datetime
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
import meilisearch
from app.s3.utils import (
    get_public_client,
    normalize_s3_path,
    escape_meili_filter_val,
    path_depth,
    build_subtree_filter
)
from app.meilisearch.util import guess_mime_type


def _normalize_suffixes(suffixes: Optional[list[str]]) -> list[str]:
    """Normalize suffix list to lowercase extension tokens without leading dots."""
    if not suffixes:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in suffixes:
        if raw is None:
            continue
        token = str(raw).strip().lower()
        if token.startswith("."):
            token = token[1:]
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _key_matches_suffixes(key: str, suffixes: Optional[list[str]]) -> bool:
    """Match key against exact filename extension(s), case-insensitive."""
    normalized = _normalize_suffixes(suffixes)
    if not normalized:
        return True

    lower_key = key.lower()
    return any(lower_key.endswith(f".{suffix}") for suffix in normalized)


def _facet_map(result: Dict[str, Any], facet_name: str) -> Dict[str, int]:
    """Return a normalized facet distribution map for a single facet name."""
    dist = result.get("facetDistribution") or result.get(
        "facetsDistribution") or {}
    raw = dist.get(facet_name, {})
    return {str(k): int(v) for k, v in raw.items()}


def _folder_name(path: str) -> str:
    """Return the display name for a folder path."""
    return path.rsplit("/", 1)[-1] if path else ""


def _is_same_or_descendant(path: str, root: str) -> bool:
    """Check whether path is root itself or within root subtree."""
    return (not root) or path == root or path.startswith(f"{root}/")


def _is_direct_child(parent: str, candidate: str) -> bool:
    """Check if candidate is exactly one level below parent."""
    if not candidate:
        return False
    if not parent:
        return "/" not in candidate
    if not candidate.startswith(f"{parent}/"):
        return False
    remainder = candidate[len(parent) + 1:]
    return remainder != "" and "/" not in remainder


def _breadcrumbs(path: str) -> List[Dict[str, str]]:
    """Build breadcrumb segments from a normalized folder path."""
    p = normalize_s3_path(path)
    if not p:
        return []
    parts = p.split("/")
    return [{"path": "/".join(parts[:i]),
             "name": parts[i - 1]}
            for i in range(1, len(parts) + 1)]


def _to_last_modified(raw: Any) -> datetime | None:
    """Convert indexed LastModified values to datetime if possible."""
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(int(raw))
    except (TypeError, ValueError, OSError):
        try:
            return datetime.fromisoformat(str(raw))
        except ValueError:
            return None


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
    """Iterate matching S3 objects from live bucket listing with filtering."""
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
                      suffixes: Optional[list[str]] = None
                      ) -> bool:
    """Return whether an object record satisfies all provided filter predicates."""
    if contains and contains not in key:
        return False

    if not _key_matches_suffixes(key, suffixes):
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
                      suffixes: Optional[list[str]] = None,
                      sort_by: Optional[str] = None,
                      sort_direction: str = "asc") -> list[Dict[str, Any]]:
    """Search indexed file documents in Meilisearch with optional filters/sort."""
    meilisearch_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meilisearch_url)

    filter_arr = []
    if prefix is not None and prefix != "":
        prefix = normalize_s3_path(prefix)
        filter_arr.append(build_subtree_filter(prefix))

    if min_size is not None:
        filter_arr.append(f"Size>={min_size}")

    if max_size is not None:
        filter_arr.append(f"Size<={max_size}")

    if storage_classes is not None and len(storage_classes) > 0:
        storage_classes = [
            f"StorageClass='{escape_meili_filter_val(storage_class)}'"
            for storage_class in storage_classes]
        filter_arr.append(f"({' OR '.join(storage_classes)})")

    if modified_after is not None:
        timestamp = modified_after.timestamp()
        filter_arr.append(f"LastModified>={timestamp}")

    if modified_before is not None:
        timestamp = modified_before.timestamp()
        filter_arr.append(f"LastModified<={timestamp}")

    if suffixes is not None:
        content_types = {ctype
                         for suffix in suffixes
                         if suffix is not None
                         for ctype in [guess_mime_type(suffix)]
                         if ctype}
        print(content_types)
        if len(content_types) == 1:
            only_type = next(iter(content_types))
            filter_arr.append(f"ContentType='{only_type}'")
        else:
            types_list = ", ".join(
                f"'{ctype}'" for ctype in sorted(content_types))
            filter_arr.append(f"ContentType IN [{types_list}]")

    search_opts = {
        "filter": filter_arr,
        "limit": limit,
    }

    if sort_by:
        if sort_by in {"Key", "Size", "LastModified"}:
            search_opts["sort"] = [
                f"{sort_by}:{sort_direction}"
            ]

    documents = meili_client.index(bucket).search(
        contains if contains is not None else "",
        search_opts)

    objects = []

    for document in documents["hits"]:
        last_modified_out = datetime.fromtimestamp(
            int(document["LastModified"]))

        objects.append({
            "key": document["Key"],
            "size": document["Size"],
            "last_modified": last_modified_out,
            "storage_class": document["StorageClass"],
            "tags": document["Tags"]
        })

    return objects


def search_folders_from_meili(
    bucket: str,
    prefix: str = "",
    contains: Optional[str] = None,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """Return relevant folder candidates from facet counts on Ancestors."""
    meili_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meili_url)

    root = normalize_s3_path(prefix)
    search_opts: Dict[str, Any] = {
        "limit": 1,
        "facets": ["Ancestors"]
    }
    if root:
        search_opts["filter"] = [build_subtree_filter(root)]

    result = meili_client.index(bucket).search(contains or "", search_opts)
    counts = _facet_map(result, "Ancestors")

    folders: List[Dict[str, Any]] = []
    for raw_path, count in counts.items():
        path = normalize_s3_path(raw_path)
        if not path:
            continue
        if root and (not _is_same_or_descendant(path, root) or path == root):
            continue
        folders.append({
            "path": path,
            "name": _folder_name(path),
            "depth": path_depth(path),
            "matched_count": count
        })

    folders.sort(key=lambda x: (-x["matched_count"], x["path"]))
    return folders[:limit]


def list_folder_children_from_meili(
    bucket: str,
    prefix: str = "",
    path: Optional[str] = None,
    contains: Optional[str] = None,
    limit: int = 100,
    sort_by: Optional[str] = None,
    sort_direction: str = "asc"
) -> Dict[str, Any]:
    """Return direct child folders/files and breadcrumbs for a folder path."""
    meili_url = os.getenv("MEILISEARCH_URL")
    meili_client = meilisearch.Client(meili_url)

    base = normalize_s3_path(prefix)
    active = normalize_s3_path(path) if path is not None else base

    if base and active and not _is_same_or_descendant(active, base):
        raise ValueError("Requested path must stay within s3_uri prefix")

    subtree = active or base
    search_opts: Dict[str, Any] = {
        "limit": 1,
        "facets": ["Ancestors"]
    }
    if subtree:
        search_opts["filter"] = [build_subtree_filter(subtree)]

    result = meili_client.index(bucket).search(contains or "", search_opts)
    counts = _facet_map(result, "Ancestors")

    # get children of current selected folder
    children: List[Dict[str, Any]] = []
    for raw_path, count in counts.items():
        folder_path = normalize_s3_path(raw_path)
        if _is_direct_child(active, folder_path):
            children.append({
                "path": folder_path,
                "name": _folder_name(folder_path),
                "depth": path_depth(folder_path),
                "matched_count": count
            })

    children.sort(key=lambda x: (-x["matched_count"], x["name"]))

    # build options to grab files
    parent_filter = (
        f"ParentPath = '{escape_meili_filter_val(active)}'"
        if active
        else "ParentPath = ''"
    )
    sort_field = sort_by if sort_by in (
        "Key", "Size", "LastModified") else "Key"
    sort_order = "desc" if sort_direction == "desc" else "asc"
    file_opts: Dict[str, Any] = {
        "filter": [parent_filter],
        "limit": limit,
        "sort": [f"{sort_field}:{sort_order}"],
        "attributesToRetrieve": ["Key", "Size", "LastModified", "StorageClass"]
    }
    file_result = meili_client.index(bucket).search(contains or "", file_opts)

    # find all files within current folder
    files: List[Dict[str, Any]] = []
    for document in file_result.get("hits", []):
        key = document.get("Key")
        if not key or str(key).endswith("/"):
            continue
        files.append({
            "key": key,
            "size": int(document.get("Size", 0)),
            "last_modified": _to_last_modified(document.get("LastModified")),
            "storage_class": document.get("StorageClass")
        })

    return {
        "path": active,
        "breadcrumbs": _breadcrumbs(active),
        "children": children[:limit],
        "files": files
    }
