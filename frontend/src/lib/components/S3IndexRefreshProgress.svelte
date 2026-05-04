<script lang="ts">
  /** Displays and polls backend index-refresh status for the active S3 URI. */
  import { onDestroy } from "svelte";
  import { getRefreshStatus } from "../api/s3";
  import type { MeilisearchRefreshStatus } from "../schemas/meilisearch";

  export let s3Uri = "";

  let status: MeilisearchRefreshStatus = {
    status: "idle",
    processed: 0,
    total: 0,
    percent: 0,
  };
  let pollId: number | null = null;
  let error: string | null = null;

  /** Performs one refresh-status fetch cycle. */
  async function pollOnce() {
    if (!s3Uri) return;
    try {
      status = await getRefreshStatus(s3Uri);
      error = null;
    } catch (err) {
      error = err instanceof Error ? err.message : "Unknown error occurred";
    }
  }

  /** Starts interval polling and performs an immediate status fetch. */
  function startPolling() {
    stopPolling();
    pollOnce();
    pollId = window.setInterval(pollOnce, 15000);
  }

  /** Stops interval polling if active. */
  function stopPolling() {
    if (pollId !== null) {
      clearInterval(pollId);
      pollId = null;
    }
  }

  $: if (s3Uri && s3Uri.startsWith("s3://")) {
    startPolling();
  } else {
    stopPolling();
    status = {
      status: "idle",
      processed: 0,
      total: 0,
      percent: 0,
    };
  }

  // might be worth changing later...
  $: if (status.status === "done" || status.status === "error") {
    stopPolling();
  }

  onDestroy(stopPolling);
</script>

{#if s3Uri}
  {#if status.status === "listing"}
    <div class="w-full max-w-xs">
      <div class="mb-1 text-xs font-medium tracking-wide text-slate-300/90">
        Index status: scanning objects
        {#if status.listed !== null}
          ({status.listed} found)
        {/if}
      </div>
      <div class="h-2 overflow-hidden rounded bg-slate-800/80">
        <div class="h-2 w-full animate-pulse bg-amber-400/80"></div>
      </div>
    </div>
  {:else if status.status === "running"}
    <div class="w-full max-w-xs">
      <div class="mb-1 text-xs font-medium tracking-wide text-slate-300/90">
        Refreshing index: {status.processed}/{status.total} ({status.percent}%)
      </div>
      <div class="h-2 rounded bg-slate-800/80">
        <div
          class="h-2 rounded bg-amber-400"
          style={`width: ${status.percent}%`}
        ></div>
      </div>
    </div>
  {:else if status.status === "error"}
    <div class="text-xs text-rose-300">
      Refresh error: {error || "Unknown error occurred"}
    </div>
  {/if}
{/if}
