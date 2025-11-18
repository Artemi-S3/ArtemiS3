<script lang="ts">
  import { type S3ObjectModel } from "../schemas/s3";

  export let items: S3ObjectModel[] = [];
</script>

{#if items.length === 0}
  <p class="mt-3 text-gray-600 text-sm">
    No results yet. Enter a valid S3 URI and run a search.
  </p>
{:else}
  <table class="mt-4 w-full border-collapse text-sm">
    <thead>
      <tr class="border-b bg-white">
        <th class="text-left p-2">Key</th>
        <th class="text-left p-2">Size bytes</th>
        <th class="text-left p-2">Last modified</th>
        <th class="text-left p-2">Storage class</th>
      </tr>
    </thead>
    <tbody>
      {#each items as obj}
        <tr class="border-b odd:bg-gray-100">
          <td class="p-2 font-mono text-xs break-all">{obj.key}</td>
          <td class="p-2">{obj.size}</td>
          <td class="p-2">{obj.last_modified ?? "unknown"}</td>
          <td class="p-2">{obj.storage_class ?? "STANDARD"}</td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}
