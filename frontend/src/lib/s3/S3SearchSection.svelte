<script lang="ts">
  import { Search as SearchIcon } from "@lucide/svelte";
  import { searchS3 } from "../api/s3";
  import { type S3ObjectModel } from "../schemas/s3";
  import S3ResultsTable from "../s3/S3ResultsTable.svelte";

  export let className = "";

  let s3Uri = "";
  let s3Contains = "";
  let s3Limit = 10;

  let s3Loading = false;
  let s3Error: string | null = null;
  let s3Results: S3ObjectModel[] = [];

  async function runS3Search() {
    s3Loading = true;
    s3Error = null;
    try {
      s3Results = await searchS3({
        s3_uri: s3Uri,
        contains: s3Contains || undefined,
        limit: s3Limit
      });
      console.log("S3 search results:", s3Results);
    } catch (err) {
      s3Error = err instanceof Error ? err.message : "Unknown S3 error";
      s3Results = [];
      console.error("S3 search failed:", err);
    } finally {
      s3Loading = false;
    }
  }
</script>

<section class={`border rounded p-4 bg-gray-50 ${className}`}>
  <h2 class="text-xl font-semibold mb-3">
    S3 search endpoint test
  </h2>

  <form
    class="flex flex-wrap gap-3 items-end"
    on:submit|preventDefault={runS3Search}
  >
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

  <S3ResultsTable items={s3Results} />
</section>
