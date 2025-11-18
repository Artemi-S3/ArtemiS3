import { type S3ObjectModel } from "../schemas/s3";
import { getJSON } from "./client";
import { type Query } from "./utils";

export interface S3SearchParams extends Query {
  s3_uri: string;
  contains?: string;
  limit?: number;
}

export async function searchS3(params: S3SearchParams): Promise<S3ObjectModel[]> {
  return getJSON<S3ObjectModel[]>("/s3/search", params);
}
