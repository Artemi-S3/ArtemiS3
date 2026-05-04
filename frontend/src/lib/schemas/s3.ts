/** Shared S3 search and folder navigation models used across the frontend. */
export type S3ObjectModel = {
  key: string;
  size: number;
  lastModified?: string;
  storageClass?: string;
  tags?: string[];
};

/** Request payload for file-mode S3 search. */
export type S3SearchRequest = {
  s3Uri: string;
  contains?: string;
  limit?: number;
  suffixes?: string[];
  minSize?: number;
  maxSize?: number;
  storageClasses?: string[];
  modifiedAfter?: string;
  modifiedBefore?: string;
  sortBy?: "Key" | "Size" | "LastModified";
  sortDirection?: "asc" | "desc";
};

/** Folder entry returned from folder-mode APIs. */
export type S3FolderModel = {
  path: string;
  name: string;
  depth: number;
  matched_count: number;
};

/** Breadcrumb segment for current folder path. */
export type S3BreadcrumbModel = {
  path: string;
  name: string;
};

/** Folder children response including nested folders and direct files. */
export type S3FolderChildrenResponse = {
  path: string;
  breadcrumbs: S3BreadcrumbModel[];
  children: S3FolderModel[];
  files?: S3ObjectModel[];
};

/** Request payload for folder suggestion search. */
export type S3FolderSearchRequest = {
  s3Uri: string;
  contains?: string;
  limit?: number;
};

/** Request payload for loading children under a folder path. */
export type S3FolderChildrenRequest = {
  s3Uri: string;
  path?: string;
  contains?: string;
  limit?: number;
  sortBy?: "Key" | "Size" | "LastModified";
  sortDirection?: "asc" | "desc";
};
