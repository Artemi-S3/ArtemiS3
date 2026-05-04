<script lang="ts">
  /** Folder-mode explorer with breadcrumb navigation, table view, and preview. */
  import {
    Download as DownloadIcon,
    Eye as EyeIcon,
    File as FileIcon,
    Folder as FolderIcon,
    FolderOpen as FolderOpenIcon,
  } from "@lucide/svelte";
  import type {
    S3BreadcrumbModel,
    S3FolderModel,
    S3ObjectModel,
  } from "../schemas/s3";
  import S3MapPreview from "./S3MapPreview.svelte";
  import { isGeospatialPreviewableKey } from "../utils/geospatialPreview";

  const STANDARD_PREVIEWABLE_EXTENSIONS = [
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mp3",
  ];

  export let searchedYet = false;
  export let loading = false;
  export let s3Uri = "";
  export let suggestions: S3FolderModel[] = [];
  export let children: S3FolderModel[] = [];
  export let files: S3ObjectModel[] = [];
  export let breadcrumbs: S3BreadcrumbModel[] = [];
  export let activePath = "";
  export let sortBy: "Key" | "Size" | "LastModified" | undefined = undefined;
  export let sortDirection: "asc" | "desc" = "asc";

  export let onOpenFolder: (path: string) => void = () => {};
  export let onOpenBreadcrumb: (path: string) => void = () => {};
  export let onNavigateUp: () => void = () => {};
  export let onSort: (
    column: "Key" | "Size" | "LastModified",
  ) => void = () => {};
  export let onDownload: (key: string) => void = () => {};

  let previewKey: string | null = null;
  let previewUrl: string | null = null;
  let previewError: string | null = null;
  let previewLoading = false;
  let selectedRow: string | null = null;
  let selectedFolderPath: string | null = null;

  $: if (selectedFolderPath === null && activePath) {
    selectedFolderPath = activePath;
  }
  $: sortedChildren = [...children].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  $: if (previewKey && !files.some((item) => item.key === previewKey)) {
    clearPreview();
  }

  /** Clears currently loaded preview state. */
  function clearPreview() {
    previewKey = null;
    previewUrl = null;
    previewError = null;
    previewLoading = false;
  }

  /** Extracts bucket name from an `s3://` URI. */
  function getBucketFromUri(uri: string): string {
    if (!uri.startsWith("s3://")) return "";
    return uri.slice("s3://".length).split("/")[0];
  }

  /** Returns true when a file extension is previewable in folder mode. */
  function canPreview(key: string): boolean {
    const lowerKey = key.toLowerCase();
    if (isGeospatialPreviewableKey(lowerKey)) return true;
    return STANDARD_PREVIEWABLE_EXTENSIONS.some((ext) =>
      lowerKey.endsWith(ext),
    );
  }

  /** Returns the final path segment for display in file rows. */
  function displayName(key: string): string {
    const segments = key.split("/").filter(Boolean);
    return segments[segments.length - 1] || key;
  }

  /** Formats byte size values for display in table rows. */
  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  /** Builds text labels for sortable table headers. */
  function sortLabel(column: "Key" | "Size" | "LastModified", label: string) {
    if (sortBy !== column) return `${label} -`;
    return `${label} ${sortDirection === "asc" ? "^" : "v"}`;
  }

  /** Selects a folder row without triggering navigation. */
  function selectFolder(path: string) {
    selectedFolderPath = path;
    selectedRow = `folder:${path}`;
  }

  /** Opens a folder and refreshes child listing. */
  async function openFolder(path: string) {
    clearPreview();
    selectFolder(path);
    await onOpenFolder(path);
  }

  /** Navigates to a breadcrumb path and refreshes child listing. */
  async function openBreadcrumb(path: string) {
    clearPreview();
    selectedRow = null;
    selectedFolderPath = path || null;
    await onOpenBreadcrumb(path);
  }

  /** Toggles preview for a file row and fetches preview URL from backend. */
  async function handlePreview(key: string) {
    if (!canPreview(key)) return;

    if (previewKey === key && previewUrl) {
      clearPreview();
      return;
    }

    previewLoading = true;
    previewError = null;
    previewKey = key;
    previewUrl = null;

    const bucketName = getBucketFromUri(s3Uri);
    if (!bucketName) {
      previewLoading = false;
      previewError = "Invalid S3 URI for preview.";
      return;
    }

    try {
      const response = await fetch(
        `/api/s3/preview?bucket=${encodeURIComponent(bucketName)}&key=${encodeURIComponent(key)}`,
      );
      if (!response.ok) {
        previewError = `Preview failed: ${response.status}`;
        return;
      }
      const data = await response.json();
      previewUrl = data.preview_url ?? null;
      if (!previewUrl) {
        previewError = "Preview URL was not returned by the server.";
      }
    } catch (err) {
      previewError = err instanceof Error ? err.message : "Preview failed.";
    } finally {
      previewLoading = false;
    }
  }
</script>

{#if !searchedYet}
  <p class="text-base text-slate-300/90 md:text-lg">
    No results yet.<br />Enter an S3 URI and run a folder search.
  </p>
{:else if suggestions.length === 0}
  <p class="text-base text-slate-300/90 md:text-lg">
    No folders found. Try a different query.
  </p>
{:else}
  <div
    class="overflow-hidden rounded-md border border-slate-400/50 bg-slate-950/45"
  >
    <div
      class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-500/50 bg-slate-900/75 px-4 py-3"
    >
      <div class="flex min-w-0 flex-wrap items-center gap-2 text-sm">
        <span class="font-semibold text-slate-200">Path</span>
        <button
          type="button"
          class="rounded px-1 text-amber-300 underline decoration-amber-400/65 underline-offset-3 transition hover:text-amber-200"
          on:click={() => openBreadcrumb("")}
        >
          root
        </button>
        {#each breadcrumbs as crumb}
          <span class="text-slate-500">/</span>
          <button
            type="button"
            class="rounded px-1 text-amber-300 underline decoration-amber-400/65 underline-offset-3 transition hover:text-amber-200"
            on:click={() => openBreadcrumb(crumb.path)}
          >
            {crumb.name}
          </button>
        {/each}
      </div>
      <div class="flex items-center gap-2">
        {#if loading}
          <span class="text-xs text-slate-300">Loading...</span>
        {/if}
        <button
          type="button"
          class="rounded border border-slate-500/45 bg-slate-900/85 px-2 py-1 text-xs font-semibold text-slate-200 transition hover:bg-slate-800/75 disabled:cursor-not-allowed disabled:opacity-55"
          on:click={onNavigateUp}
          disabled={!activePath || loading}
        >
          Up
        </button>
      </div>
    </div>

    <div
      class="grid min-h-[420px] grid-cols-1 lg:grid-cols-[18rem_minmax(0,1fr)]"
    >
      <aside
        class="border-b border-slate-700/60 bg-slate-900/55 p-3 lg:border-b-0 lg:border-r"
      >
        <h3 class="mb-2 text-sm font-semibold tracking-wide text-slate-200">
          Relevant folders
        </h3>
        {#if suggestions.length === 0}
          <p class="text-sm text-slate-400">No relevant folders.</p>
        {:else}
          <ul class="space-y-1">
            {#each suggestions as folder}
              <li>
                <button
                  type="button"
                  class={`flex w-full items-center justify-between gap-2 rounded border px-2 py-1 text-left text-sm transition ${
                    selectedFolderPath === folder.path
                      ? "border-amber-300/50 bg-amber-400/15 text-amber-200"
                      : "border-slate-600/40 bg-slate-900/40 text-slate-200 hover:bg-slate-800/55"
                  }`}
                  on:click={() => openFolder(folder.path)}
                >
                  <span class="mono truncate">{folder.path}</span>
                  <span class="text-xs text-slate-400"
                    >{folder.matched_count}</span
                  >
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </aside>

      <div class="p-3">
        <div
          class="overflow-x-auto rounded-md border border-slate-500/45 bg-slate-950/45"
        >
          <table class="w-full min-w-[900px] text-sm">
            <thead
              class="border-b border-slate-600/60 bg-slate-900/70 text-left text-sm font-semibold"
            >
              <tr>
                <th
                  title="Sort Alphabetically"
                  class="cursor-pointer px-3 py-2"
                  on:click={() => onSort("Key")}
                >
                  {sortLabel("Key", "Name")}
                </th>
                <th
                  title="Sort by Biggest/Smallest"
                  class="cursor-pointer px-3 py-2"
                  on:click={() => onSort("Size")}
                >
                  {sortLabel("Size", "Size")}
                </th>
                <th
                  title="Sort by Most Recent/Least Recent"
                  class="cursor-pointer px-3 py-2"
                  on:click={() => onSort("LastModified")}
                >
                  {sortLabel("LastModified", "Last Modified")}
                </th>
                <th class="px-3 py-2">Storage Class</th>
                <th class="px-3 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#if sortedChildren.length === 0 && files.length === 0}
                <tr>
                  <td
                    colspan="5"
                    class="px-3 py-8 text-center text-sm text-slate-400"
                  >
                    This folder is empty.
                  </td>
                </tr>
              {:else}
                {#each sortedChildren as child, idx}
                  <tr
                    class={`group border-b border-slate-800/80 ${idx % 2 === 0 ? "bg-slate-900/45" : "bg-slate-800/60"}`}
                  >
                    <td class="px-3 py-2">
                      <button
                        type="button"
                        class={`flex w-full items-center gap-2 rounded border px-2 py-1 text-left transition ${
                          selectedFolderPath === child.path
                            ? "border-amber-300/55 bg-amber-400/15 text-amber-200"
                            : "border-transparent text-slate-100 hover:border-slate-500/55 hover:bg-slate-700/35"
                        }`}
                        on:click={() => selectFolder(child.path)}
                        on:dblclick={() => openFolder(child.path)}
                        title={child.path}
                      >
                        {#if selectedFolderPath === child.path}
                          <FolderOpenIcon
                            class="h-4 w-4 shrink-0 text-amber-300"
                          />
                        {:else}
                          <FolderIcon class="h-4 w-4 shrink-0 text-amber-400" />
                        {/if}
                        <span class="truncate">{child.name}</span>
                      </button>
                    </td>
                    <td class="px-3 py-2 text-slate-400">-</td>
                    <td class="px-3 py-2 text-slate-400">-</td>
                    <td class="px-3 py-2 text-slate-300">Folder</td>
                    <td class="px-3 py-2 text-center">
                      <button
                        type="button"
                        class="rounded px-2 py-1 text-xs font-semibold text-amber-200 transition hover:bg-slate-700/45"
                        on:click={() => openFolder(child.path)}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                {/each}

                {#each files as file, idx}
                  <tr
                    class={`group border-b border-slate-800/80 ${
                      selectedRow === `file:${file.key}`
                        ? "bg-amber-500/12"
                        : idx % 2 === 0
                          ? "bg-slate-900/45"
                          : "bg-slate-800/60"
                    }`}
                  >
                    <td class="px-3 py-2">
                      <button
                        type="button"
                        class="flex w-full items-center gap-2 text-left text-slate-100"
                        on:click={() => (selectedRow = `file:${file.key}`)}
                        title={file.key}
                      >
                        <FileIcon class="h-4 w-4 shrink-0 text-slate-400" />
                        <span class="truncate">{displayName(file.key)}</span>
                      </button>
                    </td>
                    <td class="px-3 py-2 text-slate-200"
                      >{formatSize(file.size)}</td
                    >
                    <td class="px-3 py-2 text-slate-200"
                      >{file.lastModified ?? "Unknown"}</td
                    >
                    <td class="px-3 py-2 text-slate-200"
                      >{file.storageClass ?? "STANDARD"}</td
                    >
                    <td class="px-3 py-2">
                      <div
                        class="flex items-center justify-center gap-1 opacity-65 transition group-hover:opacity-100"
                      >
                        <button
                          type="button"
                          class="icon-button"
                          title="Download"
                          on:click={() => onDownload(file.key)}
                        >
                          <DownloadIcon class="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          class="icon-button"
                          title={canPreview(file.key)
                            ? "Preview"
                            : "Preview unavailable for this file type"}
                          on:click={() => handlePreview(file.key)}
                          disabled={!canPreview(file.key)}
                        >
                          <EyeIcon class="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {#if previewKey === file.key}
                    <tr class="border-b border-slate-700/70 bg-slate-950/70">
                      <td colspan="5" class="p-3">
                        <div
                          class="rounded border border-slate-500/45 bg-slate-900/75 p-3"
                        >
                          <div
                            class="mb-2 flex items-center justify-between gap-2"
                          >
                            <p
                              class="truncate text-sm font-medium text-slate-200"
                            >
                              Preview: {previewKey}
                            </p>
                            <button
                              type="button"
                              class="rounded px-2 py-1 text-xs text-slate-300 transition hover:bg-slate-800/70 hover:text-rose-300"
                              on:click={clearPreview}
                            >
                              Close
                            </button>
                          </div>
                          {#if previewLoading}
                            <p class="text-sm text-slate-300">
                              Loading preview...
                            </p>
                          {:else if previewError}
                            <p class="text-sm text-rose-300">{previewError}</p>
                          {:else if previewUrl}
                            {#if previewKey && isGeospatialPreviewableKey(previewKey)}
                              <S3MapPreview
                                fileKey={file.key}
                                fileSize={file.size}
                                {previewUrl}
                              />
                            {:else if previewKey
                              ?.toLowerCase()
                              .endsWith(".pdf")}
                              <iframe
                                src={previewUrl}
                                title="PDF preview"
                                class="h-[560px] w-full rounded border border-slate-600/55 bg-white"
                              ></iframe>
                            {:else if file.size > 52428800}
                              <div
                                class="rounded border border-amber-300/45 bg-amber-500/15 p-4 text-sm text-amber-100"
                              >
                                This file is {formatSize(file.size)}. Open it in
                                a new tab for a safer preview.
                                <a
                                  class="ml-2 underline hover:text-amber-300"
                                  href={previewUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Open preview
                                </a>
                              </div>
                            {:else}
                              <div
                                class="rounded border border-slate-600/55 bg-slate-900/80 p-2"
                              >
                                <img
                                  src={previewUrl}
                                  alt="S3 file preview"
                                  class="mx-auto max-h-[560px] max-w-full object-contain"
                                />
                              </div>
                            {/if}
                          {/if}
                        </div>
                      </td>
                    </tr>
                  {/if}
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
{/if}
