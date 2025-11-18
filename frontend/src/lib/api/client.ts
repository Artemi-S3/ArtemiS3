import { API_BASE_URL, buildQuery, type Query } from './utils';

export async function getJSON<T>(path: string, params: Query = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}${buildQuery(params)}`;
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed: ${response.status}: ${text}`);
  }

  return response.json() as Promise<T>;
}
