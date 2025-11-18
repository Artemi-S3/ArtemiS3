export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost/api';

export type Query = Record<string, string | number | boolean | undefined | null>;

export function buildQuery(params: Query): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value == null) continue;
    search.append(key, String(value));
  }
  const queryString = search.toString();
  return queryString ? `?${queryString}` : "";
}
