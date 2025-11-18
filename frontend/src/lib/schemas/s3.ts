export interface S3ObjectModel {
  key: string;
  size: number;
  last_modified?: string;
  storage_class?: string;
}
