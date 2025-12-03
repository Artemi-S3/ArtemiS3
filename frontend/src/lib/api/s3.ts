import { type S3ObjectModel, type S3SearchRequest } from "../schemas/s3";

export async function searchS3(params: S3SearchRequest): Promise<S3ObjectModel[]> {
  const queries = new URLSearchParams();
  queries.set("s3_uri", params.s3Uri);

  // helper to add parameters to the query string
  function _addParam(key: string, value: unknown) {
    if (value === undefined || value === null) return;

    if (Array.isArray(value)) {
      value.forEach(val => queries.append(key, String(val)));
    } else {
      queries.set(key, String(value));
    }
  }

  _addParam("contains", params.contains);
  _addParam("limit", params.limit);
  _addParam("suffixes", params.suffixes);
  _addParam("min_size", params.minSize);
  _addParam("max_size", params.maxSize);
  _addParam("storage_classes", params.storageClasses);
  _addParam("modified_after", params.modifiedAfter);
  _addParam("modified_before", params.modifiedBefore);

  const res = await fetch(`/api/s3/search?${queries.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`S3 search failed: ${res.status} ${errorText}`);
  }

  return await res.json();
}
