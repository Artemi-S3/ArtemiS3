export interface S3ObjectModel {
  key: string;
  size: number;
  last_modified?: string;
  storage_class?: string;
};

export interface S3SearchRequest {
  s3Uri: string;
  contains?: string;
  limit?: number;
  suffixes?: string[];
  minSize?: number;
  maxSize?: number;
  storageClasses?: string[];
  modifiedAfter?: string;
  modifiedBefore?: string;
};
