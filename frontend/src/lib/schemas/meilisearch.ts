/** Progress status reported by backend index-refresh tracking endpoint. */
export type MeilisearchRefreshStatus = {
  status: "idle" | "listing" | "running" | "done" | "error";
  processed: number;
  total: number;
  percent: number;
  listed?: number;
  started_at?: string;
  finished_at?: string;
  message?: string;
};
