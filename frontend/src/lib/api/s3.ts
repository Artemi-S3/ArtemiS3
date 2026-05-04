/**
 * API client helpers for S3 search, folder browsing, refresh tracking, and tagging.
 * Adapts backend snake_case fields into frontend camelCase models.
 */
import type {
  S3ObjectModel,
  S3SearchRequest,
  S3FolderModel,
  S3FolderSearchRequest,
  S3FolderChildrenRequest,
  S3FolderChildrenResponse
} from "../schemas/s3";
import type { MeilisearchRefreshStatus } from "../schemas/meilisearch";
import axios from "axios";

/** Backend object shape for file search responses. */
type RawS3ObjectModel = {
  key: string;
  size: number;
  last_modified?: string;
  storage_class?: string;
  lastModified?: string;
  storageClass?: string;
  tags: string[];
};

/** Backend object shape for folder children file entries. */
type RawS3FolderFileModel = {
  key: string;
  size: number;
  last_modified?: string;
  storage_class?: string;
  lastModified?: string;
  storageClass?: string;
};

/** Backend response shape for folder children endpoint. */
type RawS3FolderChildrenResponse = {
  path: string;
  breadcrumbs: S3FolderChildrenResponse["breadcrumbs"];
  children: S3FolderChildrenResponse["children"];
  files?: RawS3FolderFileModel[];
};

/** Appends a query parameter, expanding arrays into repeated key/value pairs. */
function addQueryParam(queries: URLSearchParams, key: string, value: unknown) {
  if (value === undefined || value === null) return;

  if (Array.isArray(value)) {
    value.forEach((val) => queries.append(key, String(val)));
  } else {
    queries.set(key, String(value));
  }
}

/** Normalizes sort direction and provides a safe fallback for unexpected values. */
function normalizeSortDirection(
  direction: unknown,
): "asc" | "desc" | undefined {
  if (direction === undefined || direction === null || direction === "") {
    return undefined;
  }
  return direction === "asc" || direction === "desc" ? direction : "asc";
}

/** Fetches Meilisearch index-refresh status for the selected S3 URI. */
export async function getRefreshStatus(s3Uri: string): Promise<MeilisearchRefreshStatus> {
  const queries = new URLSearchParams();
  queries.set("s3_uri", s3Uri);
  const res = await fetch(`/api/s3/refresh/status?${queries.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Refresh status failed: ${res.status} ${errorText}`);
  }
  return await res.json();
}

/** Runs file-mode S3 search with optional text, filter, and sort parameters. */
export async function searchS3(params: S3SearchRequest): Promise<S3ObjectModel[]> {
  const queries = new URLSearchParams();
  queries.set("s3_uri", params.s3Uri);
  const normalizedSortDirection = normalizeSortDirection(params.sortDirection);

  addQueryParam(queries, "contains", params.contains);
  addQueryParam(queries, "limit", params.limit);
  addQueryParam(queries, "suffixes", params.suffixes);
  addQueryParam(queries, "min_size", params.minSize);
  addQueryParam(queries, "max_size", params.maxSize);
  addQueryParam(queries, "storage_classes", params.storageClasses);
  addQueryParam(queries, "modified_after", params.modifiedAfter);
  addQueryParam(queries, "modified_before", params.modifiedBefore);
  addQueryParam(queries, "sort_by", params.sortBy);
  addQueryParam(queries, "sort_direction", normalizedSortDirection);

  const res = await fetch(`/api/s3/search?${queries.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`S3 search failed: ${res.status} ${errorText}`);
  }

  const raw = (await res.json()) as RawS3ObjectModel[];
  return raw.map((item) => ({
    key: item.key,
    size: item.size,
    lastModified: item.lastModified ?? item.last_modified,
    storageClass: item.storageClass ?? item.storage_class,
    tags: item.tags
  }));
}

/** Returns folder suggestions that match a query within an S3 URI. */
export async function searchS3Folders(params: S3FolderSearchRequest): Promise<S3FolderModel[]> {
  const queries = new URLSearchParams();
  queries.set("s3_uri", params.s3Uri);

  addQueryParam(queries, "contains", params.contains);
  addQueryParam(queries, "limit", params.limit);

  const res = await fetch(`/api/s3/folders/search?${queries.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`S3 folder search failed: ${res.status} ${errorText}`);
  }

  return await res.json();
}

/** Loads child folders/files for a folder path in folder-mode navigation. */
export async function searchS3FolderChildren(params: S3FolderChildrenRequest): Promise<S3FolderChildrenResponse> {
  const queries = new URLSearchParams();
  queries.set("s3_uri", params.s3Uri);
  const normalizedSortDirection = normalizeSortDirection(params.sortDirection);

  addQueryParam(queries, "path", params.path);
  addQueryParam(queries, "contains", params.contains);
  addQueryParam(queries, "limit", params.limit);
  addQueryParam(queries, "sort_by", params.sortBy);
  addQueryParam(queries, "sort_direction", normalizedSortDirection);

  const res = await fetch(`/api/s3/folders/children?${queries.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`S3 folder children failed: ${res.status} ${errorText}`);
  }

  const data = (await res.json()) as RawS3FolderChildrenResponse;
  return {
    path: data.path,
    breadcrumbs: data.breadcrumbs,
    children: data.children,
    files: data.files?.map((item) => ({
      key: item.key,
      size: item.size,
      lastModified: item.lastModified ?? item.last_modified,
      storageClass: item.storageClass ?? item.storage_class
    }))
  };
}

/** Persists user-edited tags for an object through the backend API. */
export async function editObjectTags(bucket: string, key: string, tags: string[]) {
  try {
    await axios.post("/api/s3/tag", { bucket, key, tags });
  } catch (err) {
    console.error("Failed to edit tags", err);
  }
}
