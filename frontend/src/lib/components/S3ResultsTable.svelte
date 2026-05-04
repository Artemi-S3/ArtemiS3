<script lang="ts">
  /** File-mode results table with sorting, pagination, preview, and tag editing. */
  import {
    ChevronDown,
    ChevronFirst,
    ChevronLast,
    ChevronLeft,
    ChevronRight,
    ChevronsUpDown,
    ChevronUp,
    Download,
    Eye,
    Pencil,
  } from "@lucide/svelte";
  import type { S3ObjectModel } from "../schemas/s3";
  import EditTagsModal from "./EditTagsModal.svelte";
  import S3MapPreview from "./S3MapPreview.svelte";
  import { isGeospatialPreviewableKey } from "../utils/geospatialPreview";

  export let s3Uri = "";
  export let items: S3ObjectModel[] = [];
  export let searchedYet = false;
  export let onDownload: (key: string, bucket?: string) => void;
  export let onSort: (column: "Key" | "Size" | "LastModified") => void;
  export let editTags: (key: string, tags: string[]) => Promise<void>;
  export let sortBy: "Key" | "Size" | "LastModified" | undefined;
  export let sortDirection: "asc" | "desc";

  const STANDARD_PREVIEWABLE_EXTENSIONS = [
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mp3",
    ".xml",
    ".lbl",
    ".lab",
    ".txt",
    ".asc",
  ];
  const PAGE_SIZE = 10;

  let previewKey: string | null = null;
  let previewUrl: string | null = null;
  let previewLoading = false;
  let previewError: string | null = null;

  let editing: string | null = null;
  let page = 0;

  $: maxPage = Math.max(Math.ceil(items.length / PAGE_SIZE) - 1, 0);
  $: pageStart = page * PAGE_SIZE;
  $: pageEnd = Math.min(page * PAGE_SIZE + PAGE_SIZE, items.length);
  $: pagedItems = items.slice(pageStart, pageEnd);
  $: checkMaxPage(maxPage);

  /** Keeps active page index inside valid bounds after result-size changes. */
  function checkMaxPage(maxPage: number) {
    if (page > maxPage) {
      page = maxPage;
      pagedItems = items.slice(
        page * PAGE_SIZE,
        Math.min(page * PAGE_SIZE + PAGE_SIZE, items.length),
      );
    }
  }

  /** Sets the object key currently being edited in the tag modal. */
  function setEditing(key: string | null) {
    editing = key;
  }

  /** Clears currently loaded preview state. */
  function clearPreview() {
    previewKey = null;
    previewUrl = null;
    previewLoading = false;
    previewError = null;
  }

  /** Toggles preview for a result row and fetches a signed preview URL. */
  async function handlePreview(key: string) {
    if (previewKey === key && previewUrl) {
      clearPreview();
      return;
    }

    const bucketName = s3Uri.replace(/^s3:\/\//, "").split("/")[0];

    try {
      previewLoading = true;
      previewError = null;
      previewUrl = null;
      previewKey = key;

      const response = await fetch(
        `/api/s3/preview?bucket=${encodeURIComponent(bucketName)}&key=${encodeURIComponent(key)}`,
      );

      if (!response.ok) {
        previewError = `Preview failed (${response.status})`;
        previewLoading = false;
        return;
      }

      const data = await response.json();
      previewUrl = data.preview_url;
    } catch (err) {
      previewError = err instanceof Error ? err.message : "Preview failed";
    } finally {
      previewLoading = false;
    }
  }

  /** Returns true when a file extension is supported by preview renderers. */
  function canPreview(key: string): boolean {
    const lowerKey = key.toLowerCase();
    if (isGeospatialPreviewableKey(lowerKey)) return true;
    return STANDARD_PREVIEWABLE_EXTENSIONS.some((ext) => lowerKey.endsWith(ext));
  }

  /** Formats ISO date strings for display in local browser timezone. */
  function formatDate(date: string): string {
    return new Date(date).toLocaleString();
  }

  /** Formats byte size values for display in table rows. */
  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    if (bytes < 1024 * 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    return `${(bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2)} TB`;
  }

  /** Builds a compact sort indicator label for headers. */
  function sortLabel(column: "Key" | "Size" | "LastModified", label: string) {
    console.log(sortBy, column, label);
    if (sortBy !== column) return `${label} -`;
    return `${label} ${sortDirection === "asc" ? "^" : "v"}`;
  }
</script>

{#if !searchedYet}
  <p class="text-base text-slate-300/90 md:text-lg">
    No results yet.<br />Enter an S3 URI and run a search.
  </p>
{:else if items.length === 0}
  <p class="text-base text-slate-300/90 md:text-lg">
    No results found. Try a different query.
  </p>
{:else}
  <div class="space-y-4">
    <div
      class="overflow-x-auto rounded-md border border-slate-400/55 bg-slate-950/45"
    >
      <table class="w-full min-w-[980px] text-sm">
        <thead class="border-b border-slate-500/55 bg-slate-900/70 text-left">
          <tr class="text-base font-semibold text-slate-100">
            <th
              title="Sort Alphabetically"
              class="cursor-pointer px-4 py-3 text-nowrap"
              on:click={() => onSort("Key")}
            >
              File Name
              {#if sortBy !== "Key"}
                <ChevronsUpDown class="opacity-60 inline" />
              {:else if sortDirection === "asc"}
                <ChevronUp class="inline" />
              {:else}
                <ChevronDown class="inline" />
              {/if}
            </th>
            <th
              title="Sort by Biggest/Smallest"
              class="cursor-pointer px-3 py-3 text-nowrap"
              on:click={() => onSort("Size")}
            >
              Size
              {#if sortBy !== "Size"}
                <ChevronsUpDown class="opacity-60 inline" />
              {:else if sortDirection === "asc"}
                <ChevronUp class="inline" />
              {:else}
                <ChevronDown class="inline" />
              {/if}
            </th>
            <th
              title="Sort by Most Recent/Least Recent"
              class="cursor-pointer px-3 py-3 text-nowrap"
              on:click={() => onSort("LastModified")}
            >
              Last Modified
              {#if sortBy !== "LastModified"}
                <ChevronsUpDown class="opacity-60 inline" />
              {:else if sortDirection === "asc"}
                <ChevronUp class="inline" />
              {:else}
                <ChevronDown class="inline" />
              {/if}
            </th>
            <th class="px-3 py-3">Storage Class</th>
            <th class="px-3 py-3">Tags</th>
            <th class="px-2 py-3 text-center">Actions</th>
          </tr>
        </thead>

        <tbody>
          {#each pagedItems as obj, idx}
            <tr
              class={`group border-b border-slate-800/90 ${idx % 2 === 0 ? "bg-slate-900/45" : "bg-slate-800/65"}`}
            >
              <td
                class="max-w-[34rem] truncate px-4 py-3 text-sm text-slate-100 mono"
                title={obj.key}
              >
                {obj.key}
              </td>
              <td class="px-3 py-3 text-sm text-slate-200"
                >{formatSize(obj.size)}</td
              >
              <td class="px-3 py-3 text-sm text-slate-200">
                {obj.lastModified ? formatDate(obj.lastModified) : "unknown"}
              </td>
              <td class="px-3 py-3 text-sm text-slate-200"
                >{obj.storageClass ?? "STANDARD"}</td
              >
              <td
                class="max-w-[18rem] truncate px-3 py-3 text-sm text-slate-200"
              >
                {obj.tags && obj.tags.length > 0 ? obj.tags.join(", ") : "-"}
              </td>
              <td class="px-2 py-2">
                <div
                  class="flex items-center justify-center gap-1 opacity-65 transition group-hover:opacity-100"
                >
                  <button
                    class="icon-button"
                    on:click={() => onDownload(obj.key)}
                    title="Download"
                  >
                    <Download size={18} />
                  </button>

                  <button
                    class="icon-button"
                    disabled={!canPreview(obj.key)}
                    on:click={() => handlePreview(obj.key)}
                    title={canPreview(obj.key)
                      ? "Preview document"
                      : "Cannot preview this file type"}
                  >
                    <Eye size={18} />
                  </button>

                  <button
                    class="icon-button"
                    title="Edit tags"
                    on:click={() => setEditing(obj.key)}
                  >
                    <Pencil size={18} />
                  </button>
                </div>
              </td>
            </tr>

            {#if previewKey === obj.key}
              <tr class="border-b border-slate-700/70 bg-slate-950/70">
                <td colspan="6" class="p-4">
                  <div
                    class="rounded-md border border-slate-500/45 bg-slate-900/70 p-3"
                  >
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <p class="truncate text-sm font-semibold text-slate-200">
                        Preview: {previewKey}
                      </p>
                      <button
                        on:click={clearPreview}
                        class="rounded px-2 py-1 text-xs font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-rose-300"
                      >
                        Close
                      </button>
                    </div>

                    {#if previewLoading}
                      <p class="text-sm text-slate-300">Loading preview...</p>
                    {:else if previewError}
                      <p class="text-sm text-rose-300">
                        Failed to load preview: {previewError}
                      </p>
                    {:else if previewUrl}
                      {#if isGeospatialPreviewableKey(obj.key)}
                        <S3MapPreview
                          fileKey={obj.key}
                          fileSize={obj.size}
                          {previewUrl}
                        />
                      {:else if obj.key.toLowerCase().endsWith(".pdf")}
                        <iframe
                          src={previewUrl}
                          title="PDF Preview"
                          class="h-[620px] w-full rounded border border-slate-600/55 bg-white"
                        ></iframe>
                      {:else if obj.key.toLowerCase().endsWith(".mp4")}
                        <video
                          controls
                          class="max-h-[620px] w-full rounded border border-slate-600/55"
                        >
                          <source src={previewUrl} type="video/mp4" />
                          Your browser does not support the video tag.
                        </video>
                      {:else if obj.key.toLowerCase().endsWith(".mp3")}
                        <div
                          class="rounded border border-slate-600/55 bg-slate-950/60 p-4"
                        >
                          <p class="mb-2 text-xs text-slate-400">
                            Audio preview: {obj.key.split("/").pop()}
                          </p>
                          <audio controls src={previewUrl} class="w-full">
                            Your browser does not support the audio element.
                          </audio>
                        </div>
                      {:else if obj.size > 52428800}
                        <div
                          class="rounded border border-amber-300/45 bg-amber-500/15 p-4 text-sm text-amber-100"
                        >
                          This file is {formatSize(obj.size)}. Open in a new tab
                          for a safer preview.
                          <a
                            href={previewUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="ml-2 underline hover:text-amber-300"
                          >
                            Open preview
                          </a>
                        </div>
                      {:else if obj.key
                        .toLowerCase()
                        .match(/\.(xml|lbl|lab|asc|txt)$/)}
                        <div
                          class="overflow-hidden rounded border border-slate-600/55 bg-slate-950/70"
                        >
                          <div
                            class="border-b border-slate-700/80 bg-slate-900/80 px-3 py-2 text-xs text-slate-300"
                          >
                            {obj.key.split("/").pop()}
                          </div>
                          <div class="max-h-[560px] overflow-auto p-3">
                            {#await fetch(previewUrl).then((res) => res.text())}
                              <p class="text-sm text-slate-300">
                                Reading file content...
                              </p>
                            {:then content}
                              <pre
                                class="mono whitespace-pre-wrap break-all text-xs leading-relaxed text-slate-100">{content}</pre>
                            {:catch error}
                              <p class="text-xs text-rose-300">
                                Failed to load text: {error.message}
                              </p>
                            {/await}
                          </div>
                        </div>
                      {:else}
                        <div
                          class="rounded border border-slate-600/55 bg-slate-900/80 p-2"
                        >
                          <img
                            src={previewUrl}
                            alt="Preview"
                            class="mx-auto block max-h-[620px] max-w-full object-contain"
                          />
                        </div>
                      {/if}
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>

    <div
      class="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-300"
    >
      <span>
        Showing <b>{pageStart + 1}</b> to <b>{pageEnd}</b> of
        <b>{items.length}</b> results
      </span>
      <div class="flex items-center">
        <button
          class="page-button rounded-l-md"
          title="Go to the first page"
          disabled={page <= 0}
          on:click={() => (page = 0)}
        >
          <ChevronFirst class="h-4 w-4" />
        </button>
        <button
          class="page-button"
          title="Go to the previous page"
          disabled={page <= 0}
          on:click={() => page--}
        >
          <ChevronLeft class="h-4 w-4" />
        </button>
        <button
          class="page-button"
          title="Go to the next page"
          disabled={page >= maxPage}
          on:click={() => page++}
        >
          <ChevronRight class="h-4 w-4" />
        </button>
        <button
          class="page-button rounded-r-md"
          title="Go to the last page"
          disabled={page >= maxPage}
          on:click={() => (page = maxPage)}
        >
          <ChevronLast class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>

  <EditTagsModal
    {editing}
    {setEditing}
    localTags={[...(items.find((obj) => obj.key === editing)?.tags ?? [])]}
    submitTags={async (key, tags) => {
      await editTags(key, tags);
      items = items.map((obj) => {
        if (obj.key === key) obj.tags = tags;
        return obj;
      });
      setEditing(null);
    }}
  />
{/if}
