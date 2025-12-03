<script lang="ts">
  import { type S3ObjectModel } from "../schemas/s3";
  import { Download } from "@lucide/svelte";

  export let s3Uri: string = "";
  export let items: S3ObjectModel[] = [];
  export let searchedYet: boolean = false;
  export let onDownload: (key: string, bucket: string) => void;
</script>

{#if !searchedYet}
  <!-- Before search has been ran -->
  <p class="mt-3 text-gray-600 text-sm">
    No results yet. Enter a valid S3 URI and run a search.
  </p>
{:else if searchedYet && items.length === 0}
  <!-- Search has been ran but there are no results -->
  <p class="mt-3 text-gray-600 text-sm">
    No results found. Try a different query.
  </p>
{:else}
  <table class="mt-4 w-full border-collapse text-sm">
    <thead>
      <tr class="border-b bg-white">
        <th class="text-left p-2">Key</th>
        <th class="text-left p-2">Size bytes</th>
        <th class="text-left p-2">Last modified</th>
        <th class="text-left p-2">Storage class</th>
        <th class="text-left p-2">Download</th>
      </tr>
    </thead>
    <tbody>
      {#each items as obj}
        <tr class="border-b odd:bg-gray-100">
          <td class="p-2 font-mono text-xs break-all">{obj.key}</td>
          <td class="p-2">{obj.size}</td>
          <td class="p-2">{obj.last_modified ?? "unknown"}</td>
          <td class="p-2">{obj.storage_class ?? "STANDARD"}</td>
          <td class="p-2">
            <button
              on:click={() => onDownload(obj.key)}
              title="Download"
              class="text-blue-600 hover:text-blue-800 cursor-pointer"
            >
              <Download size={18} />
            </button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}
