<script lang="ts">
  import { Search as SearchIcon } from "@lucide/svelte";
  import { searchS3 } from "../api/s3";
  import { type S3ObjectModel, type S3SearchRequest } from "../schemas/s3";
  import FilterPanel from "../components/FilterPanel.svelte";
  import S3ResultsTable from "../s3/S3ResultsTable.svelte";

  export let className = "";

  let s3Uri = "";
  let s3Contains = "";
  let s3Limit = 10;

  let s3Loading = false;
  let s3Error: string | null = null;
  let s3Results: S3ObjectModel[] = [];

  type FilterState = {
    suffixes?: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    modifiedAfter?: string;
    modifiedBefore?: string;
  };
  let s3Filters: FilterState = {};

  type FilterPanelPayload = {
    selectedTypes: string[]; // file types
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    date?: string; // YYYY-MM-DD
    condition?: "after" | "before" | "";
  };

  let hasSearched = false;
  async function runS3Search() {
    s3Loading = true;
    s3Error = null;

    try {
      const request: S3SearchRequest = {
        s3Uri: s3Uri,
        contains: s3Contains || undefined,
        limit: s3Limit,
        suffixes: s3Filters.suffixes,
        minSize: s3Filters.minSize,
        maxSize: s3Filters.maxSize,
        storageClasses: s3Filters.storageClasses,
        modifiedAfter: s3Filters.modifiedAfter,
        modifiedBefore: s3Filters.modifiedBefore,
      };

      hasSearched = true;
      s3Results = await searchS3(request);
    } catch (err) {
      s3Error = err instanceof Error ? err.message : "Unknown S3 error";
      s3Results = [];
      console.error("S3 search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  // calls on apply from FilterPanel
  async function handleFilterApply(payload: FilterPanelPayload) {
    const next: FilterState = {};

    if (payload.selectedTypes && payload.selectedTypes.length > 0) {
      next.suffixes = payload.selectedTypes;
    }

    if (typeof payload.minSize === "number") {
      next.minSize = payload.minSize;
    }

    if (typeof payload.maxSize === "number") {
      next.maxSize = payload.maxSize;
    }

    if (payload.storageClasses && payload.storageClasses.length > 0) {
      next.storageClasses = payload.storageClasses;
    }

    if (payload.date && payload.condition == "after") {
      next.modifiedAfter = payload.date;
    } else if (payload.date && payload.condition == "before") {
      next.modifiedBefore = payload.date;
    }

    s3Filters = next;

    // rerun search when filters are applied
    if (s3Uri) {
      await runS3Search();
    }
  }

  function getBucketFromUri(uri: string): string {
    if (!uri.startsWith("s3://")) return "";
    return uri.slice("s3://".length).split("/")[0];
  }

  async function handleDownload(key: string) {
    const bucket = getBucketFromUri(s3Uri);
    const fileUri = `s3://${bucket}/${key}`;
    const url = `/api/s3/download?s3_uri=${encodeURIComponent(fileUri)}`;

    // trigger browser download
    window.location.href = url;
  }
</script>

<section class={`border rounded p-4 bg-gray-50 ${className}`}>
  <h2 class="text-xl font-semibold mb-3">Enter your search:</h2>

  <form
    class="flex flex-wrap gap-3 items-end"
    on:submit|preventDefault={runS3Search}
  >
    <FilterPanel onApply={handleFilterApply} />
    <div class="flex flex-col">
      <label for="s3Uri" class="text-sm font-medium mb-1">S3 URI</label>
      <input
        id="s3Uri"
        type="text"
        bind:value={s3Uri}
        placeholder="s3://bucket/prefix"
        class="border rounded p-2 w-72"
        required
      />
    </div>

    <div class="flex flex-col">
      <label for="s3Contains" class="text-sm font-medium mb-1">
        Contains
      </label>
      <input
        id="s3Contains"
        type="text"
        bind:value={s3Contains}
        placeholder="optional substring filter"
        class="border rounded p-2 w-48"
      />
    </div>

    <div class="flex flex-col">
      <label for="s3Limit" class="text-sm font-medium mb-1">Limit</label>
      <input
        id="s3Limit"
        type="number"
        min="1"
        max="1000"
        bind:value={s3Limit}
        class="border rounded p-2 w-24"
      />
    </div>

    <button
      type="submit"
      class="flex items-center gap-2 bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-60"
      disabled={s3Loading}
    >
      <SearchIcon class="w-4 h-4" />
      {#if s3Loading}
        Searching
      {:else}
        Run S3 search
      {/if}
    </button>
  </form>

  {#if s3Error}
    <p class="mt-3 text-red-600">{s3Error}</p>
  {/if}

  <S3ResultsTable s3Uri={s3Uri} items={s3Results} searchedYet={hasSearched} onDownload={handleDownload} />
</section>
