<script lang="ts">
  /** Main search workflow component for file and folder exploration modes. */
  import { Search as SearchIcon } from "@lucide/svelte";
  import {
    searchS3,
    searchS3Folders,
    searchS3FolderChildren,
    editObjectTags,
  } from "../api/s3";
  import type {
    S3FolderChildrenResponse,
    S3FolderModel,
    S3ObjectModel,
    S3SearchRequest,
  } from "../schemas/s3";
  import { onDestroy, onMount } from "svelte";
  import FilterPanel from "../components/FilterPanel.svelte";
  import S3FolderExplorer from "../components/S3FolderExplorer.svelte";
  import S3IndexRefreshProgress from "./S3IndexRefreshProgress.svelte";
  import S3ResultsTable from "../components/S3ResultsTable.svelte";

  export let className = "";

  const s3UriOptions = [
    "s3://asc-pds-services",
    "s3://asc-pds-services/pigpen",
    "s3://asc-astropedia",
    "s3://asc-astropedia/Mars",
    "custom",
  ];

  let selectedS3Bucket = s3UriOptions[0];
  let customS3Uri = "";
  let s3Uri = selectedS3Bucket;

  let s3Contains = "";
  let s3Limit = 500;

  let s3Loading = false;
  let s3Error: string | null = null;
  let s3Results: S3ObjectModel[] = [];
  let viewMode: "file" | "folder" = "file";

  let folderSuggestions: S3FolderModel[] = [];
  let folderChildren: S3FolderModel[] = [];
  let folderBreadcrumbs: S3FolderChildrenResponse["breadcrumbs"] = [];
  let activeFolderPath = "";
  let folderFiles: S3ObjectModel[] = [];

  let sortBy: "Key" | "Size" | "LastModified" | undefined = undefined;
  let sortDirection: "asc" | "desc" = "asc";
  let hasSearched = false;

  const QUERY_KEY = "artemis_recent_queries";
  const FILTER_KEY = "artemis_saved_filter_presets";
  const MAX_QUERIES = 10;

  let recentQueries: string[] = [];
  let showQueryDropdown = false;
  let dropdownContainer: HTMLDivElement;
  let filterPanelRef: any;

  type FilterState = {
    suffixes?: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    modifiedAfter?: string;
    modifiedBefore?: string;
  };

  type FilterPreset = {
    name: string;
    filters: FilterState;
  };

  type FilterPanelPayload = {
    selectedTypes: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    date?: string;
    condition?: "after" | "before" | "";
  };

  let s3Filters: FilterState = {};
  let savedFilterPresets: FilterPreset[] = [];

  /** Applies an S3 dropdown selection and resets folder navigation state. */
  function handleS3OptionChange(value: string) {
    if (value === "custom") {
      s3Uri = customS3Uri;
    } else {
      s3Uri = value;
    }
    resetFolderState();
  }

  /** Updates custom S3 URI text input and resets folder navigation state. */
  function handleCustomS3UriInput(value: string) {
    customS3Uri = value;
    if (selectedS3Bucket === "custom") {
      s3Uri = customS3Uri;
    }
    resetFolderState();
  }

  /** Clears folder-mode navigation and listing state. */
  function resetFolderState() {
    folderSuggestions = [];
    folderChildren = [];
    folderBreadcrumbs = [];
    activeFolderPath = "";
    folderFiles = [];
  }

  /** Switches between file and folder mode with state reset. */
  function setViewMode(mode: string) {
    if (mode !== "file" && mode !== "folder") return;
    if (viewMode === mode) return;

    viewMode = mode;
    hasSearched = false;
    s3Error = null;
    resetFolderState();
  }

  /** Runs file-mode search using current query, filters, and sort state. */
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
        sortBy,
        sortDirection,
      };
      hasSearched = true;
      s3Results = await searchS3(request);
      saveQuery(s3Contains);
    } catch (err) {
      s3Error = err instanceof Error ? err.message : "Unknown S3 error";
      s3Results = [];
      console.error("S3 search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  /** Loads children and files for a folder-mode path. */
  async function loadFolderChildren(path?: string) {
    const data = await searchS3FolderChildren({
      s3Uri,
      path: path || undefined,
      contains: s3Contains || undefined,
      limit: s3Limit,
      sortBy,
      sortDirection,
    });
    activeFolderPath = data.path;
    folderBreadcrumbs = data.breadcrumbs;
    folderChildren = data.children;
    folderFiles = data.files ?? [];
  }

  /** Runs folder suggestion search and loads initial folder selection. */
  async function runFolderSearch() {
    s3Loading = true;
    s3Error = null;

    try {
      hasSearched = true;
      saveQuery(s3Contains);
      folderSuggestions = await searchS3Folders({
        s3Uri,
        contains: s3Contains || undefined,
        limit: s3Limit,
      });

      if (folderSuggestions.length > 0) {
        await loadFolderChildren(folderSuggestions[0].path);
      } else {
        folderChildren = [];
        folderBreadcrumbs = [];
        activeFolderPath = "";
        folderFiles = [];
      }
    } catch (err) {
      s3Error =
        err instanceof Error ? err.message : "Unknown folder search error";
      resetFolderState();
      console.error("S3 folder search failed:", err);
    } finally {
      s3Loading = false;
    }
  }

  /** Dispatches to file or folder search based on current view mode. */
  async function runSearchByMode() {
    if (viewMode === "folder") {
      await runFolderSearch();
      return;
    }
    await runS3Search();
  }

  /** Toggles sort state and re-runs active mode query. */
  async function handleSort(column: "Key" | "Size" | "LastModified") {
    if (!column) return;

    if (sortBy === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortBy = column;
      sortDirection = "desc";
    }

    if (viewMode === "folder") {
      await loadFolderChildren(activeFolderPath || undefined);
      return;
    }
    await runS3Search();
  }

  /** Converts filter panel payload into API filter state and refreshes results. */
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

    if (payload.date && payload.condition === "after") {
      next.modifiedAfter = payload.date;
    } else if (payload.date && payload.condition === "before") {
      next.modifiedBefore = payload.date;
    }

    s3Filters = next;

    if (s3Uri && viewMode === "file") {
      await runS3Search();
    }
  }

  /** Extracts bucket name from an `s3://` URI string. */
  function getBucketFromUri(uri: string): string {
    if (!uri.startsWith("s3://")) return "";
    return uri.slice("s3://".length).split("/")[0];
  }

  /** Triggers backend download endpoint for an object key. */
  async function handleDownload(key: string) {
    const bucket = getBucketFromUri(s3Uri);
    const fileUri = `s3://${bucket}/${key}`;
    const url = `/api/s3/download?s3_uri=${encodeURIComponent(fileUri)}`;
    window.location.href = url;
  }

  /** Opens a folder path in folder-mode view. */
  async function openFolder(path: string) {
    await loadFolderChildren(path);
  }

  /** Opens a breadcrumb path in folder-mode view. */
  async function openBreadcrumb(path: string) {
    await loadFolderChildren(path || undefined);
  }

  /** Navigates up one folder level from the active path. */
  async function navigateUp() {
    if (!activeFolderPath) return;
    const segments = activeFolderPath.split("/").filter(Boolean);
    segments.pop();
    const parentPath = segments.join("/");
    await loadFolderChildren(parentPath || undefined);
  }

  /** Persists tag edits for a key in the currently selected bucket. */
  async function editTags(key: string, tags: string[]) {
    const bucket = getBucketFromUri(s3Uri);
    await editObjectTags(bucket, key, tags);
  }

  /** Safely parses JSON from localStorage values. */
  function parseStoredJson(raw: string | null): unknown {
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (err) {
      console.warn("Skipping invalid localStorage value:", err);
      return null;
    }
  }

  /** Coerces unknown storage data into a valid recent-query list. */
  function coerceQueryList(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value.filter((entry): entry is string => typeof entry === "string");
  }

  /** Coerces unknown storage data into valid named filter presets. */
  function coerceFilterPresets(value: unknown): FilterPreset[] {
    if (!Array.isArray(value)) return [];

    return value.flatMap((entry) => {
      if (!entry || typeof entry !== "object") return [];

      const candidate = entry as Record<string, unknown>;
      if (typeof candidate.name !== "string") return [];

      const filters =
        candidate.filters && typeof candidate.filters === "object"
          ? (candidate.filters as FilterState)
          : {};

      return [{ name: candidate.name, filters }];
    });
  }

  /** Restores persisted query/preset state and enables outside-click behavior. */
  onMount(() => {
    if (typeof window === "undefined") return;

    recentQueries = coerceQueryList(parseStoredJson(localStorage.getItem(QUERY_KEY)));
    savedFilterPresets = coerceFilterPresets(
      parseStoredJson(localStorage.getItem(FILTER_KEY)),
    );

    document.addEventListener("click", handleClickOutside);
  });

  /** Stores the newest query at the top of bounded recent-query history. */
  function saveQuery(query: string) {
    if (!query) return;

    const filtered = recentQueries.filter((q) => q !== query);
    recentQueries = [query, ...filtered].slice(0, MAX_QUERIES);

    localStorage.setItem(QUERY_KEY, JSON.stringify(recentQueries));
  }

  /** Removes a query from recent-query history. */
  function deleteQuery(queryToDelete: string) {
    recentQueries = recentQueries.filter((q) => q !== queryToDelete);
    localStorage.setItem(QUERY_KEY, JSON.stringify(recentQueries));
  }

  /** Saves the current filter state under a user-provided preset name. */
  function saveCurrentFiltersAsPreset() {
    const current = filterPanelRef.getCurrentFilters();

    const name = prompt("Preset name?");
    if (!name) return;

    const existingIndex = savedFilterPresets.findIndex((f) => f.name === name);

    if (existingIndex !== -1) {
      const overwrite = confirm(
        `A filter named "${name}" already exists. Do you want to overwrite it?`,
      );
      if (!overwrite) return;
      savedFilterPresets[existingIndex] = { name, filters: current };
    } else {
      savedFilterPresets = [...savedFilterPresets, { name, filters: current }];
    }

    localStorage.setItem(FILTER_KEY, JSON.stringify(savedFilterPresets));
  }

  /** Hides query suggestions when clicking outside the dropdown container. */
  function handleClickOutside(event: MouseEvent) {
    if (!dropdownContainer) return;
    if (!dropdownContainer.contains(event.target as Node)) {
      showQueryDropdown = false;
    }
  }

  /** Removes one saved filter preset and persists updated state. */
  function deleteFilterPreset(name: string) {
    savedFilterPresets = savedFilterPresets.filter((f) => f.name !== name);
    localStorage.setItem(FILTER_KEY, JSON.stringify(savedFilterPresets));
  }

  /** Removes outside-click listener on component teardown. */
  onDestroy(() => {
    document.removeEventListener("click", handleClickOutside);
  });
</script>

<section
  class={`art-fade-up relative overflow-visible border border-slate-300/55 bg-slate-950/55 shadow-[0_40px_90px_rgba(2,10,18,0.55)] ${className}`}
>
  <div class="relative z-20 mx-auto w-full max-w-[1000px] px-4 py-8 md:px-8 md:py-10">
    <h2 class="mb-8 text-3xl font-bold tracking-tight md:text-4xl">
      Search <span class="text-amber-400">S3</span> Bucket
    </h2>

    <form class="space-y-7" on:submit|preventDefault={runSearchByMode}>
      <div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
        <div class="flex flex-col gap-2">
          <label for="s3Uri" class="text-sm font-semibold tracking-wide text-slate-300">
            S3 URI
          </label>
          <div
            class="art-bracket rounded-md border border-slate-400/45 bg-slate-900/65 px-3 py-2 shadow-[0_0_0_1px_rgba(15,23,42,0.4)]"
          >
            <select
              id="s3Uri"
              bind:value={selectedS3Bucket}
              class="w-full appearance-none bg-transparent text-lg font-semibold text-slate-100 outline-none"
              on:change={(e) =>
                handleS3OptionChange((e.currentTarget as HTMLSelectElement).value)}
              required
            >
              {#each s3UriOptions as option}
                <option class="bg-slate-900 text-slate-100" value={option}>
                  {option === "custom" ? "Custom..." : option}
                </option>
              {/each}
            </select>
          </div>

          {#if selectedS3Bucket === "custom"}
            <div
              class="art-bracket rounded-md border border-slate-400/45 bg-slate-900/65 px-3 py-2 shadow-[0_0_0_1px_rgba(15,23,42,0.4)]"
            >
              <input
                type="text"
                placeholder="s3://bucket/prefix"
                class="w-full border-none bg-transparent text-base text-slate-100 outline-none"
                value={customS3Uri}
                on:input={(e) =>
                  handleCustomS3UriInput((e.currentTarget as HTMLInputElement).value)}
                required
              />
            </div>
          {/if}
        </div>
        <S3IndexRefreshProgress {s3Uri} />
      </div>

      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex flex-wrap items-center gap-3 text-base">
          <span class="text-base font-semibold text-slate-200">Mode:</span>
          <button
            type="button"
            class={`art-bracket rounded-md border px-2 py-1 text-base transition ${
              viewMode === "file"
                ? "border-amber-300/65 bg-amber-400/20 text-amber-200"
                : "border-slate-400/50 bg-slate-900/60 text-slate-200 hover:bg-slate-800/70"
            }`}
            on:click={() => setViewMode("file")}
          >
            File
          </button>
          <button
            type="button"
            class={`art-bracket rounded-md border px-2 py-1 text-base transition ${
              viewMode === "folder"
                ? "border-amber-300/65 bg-amber-400/20 text-amber-200"
                : "border-slate-400/50 bg-slate-900/60 text-slate-200 hover:bg-slate-800/70"
            }`}
            on:click={() => setViewMode("folder")}
          >
            Folder
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          {#if viewMode === "file"}
            <FilterPanel
              bind:this={filterPanelRef}
              initialFilters={s3Filters}
              onApply={handleFilterApply}
              savedFilters={savedFilterPresets}
              onSave={saveCurrentFiltersAsPreset}
              onDelete={deleteFilterPreset}
            />
          {/if}
          <label for="s3Limit" class="text-base font-semibold text-slate-200">Limit:</label>
          <div class="art-bracket rounded-md border border-slate-400/50 bg-slate-900/65 px-2 py-1">
            <input
              id="s3Limit"
              type="number"
              min="1"
              max="1000"
              bind:value={s3Limit}
              class="w-20 border-none bg-transparent text-right text-lg text-slate-100 outline-none"
            />
          </div>
        </div>
      </div>

      <div class="flex flex-col items-center gap-3 md:flex-row md:justify-center">
        <div class="relative w-full max-w-md" bind:this={dropdownContainer}>
          <div
            class="art-bracket w-full rounded-md border border-slate-400/50 bg-slate-900/65 px-3 py-2"
          >
            <input
              id="s3Contains"
              type="text"
              bind:value={s3Contains}
              placeholder="Search ArtemiS3..."
              class="w-full border-none bg-transparent text-xl text-slate-100 outline-none md:text-2xl"
              autocomplete="off"
              on:focus={() => (showQueryDropdown = true)}
            />
          </div>

          {#if showQueryDropdown && recentQueries.length > 0}
            <div
              class="absolute left-0 right-0 top-full z-20 mt-1 max-h-52 overflow-y-auto rounded-md border border-slate-500/50 bg-slate-900/95 p-1 shadow-2xl"
            >
              {#each recentQueries.filter((q) => q.toLowerCase().includes(s3Contains.toLowerCase())) as query}
                <div class="flex items-center justify-between rounded px-2 hover:bg-slate-800/80">
                  <button
                    type="button"
                    class="w-full py-1.5 text-left text-sm text-slate-200"
                    on:click={async () => {
                      s3Contains = query;
                      await runSearchByMode();
                      showQueryDropdown = false;
                    }}
                  >
                    {query}
                  </button>
                  <button
                    type="button"
                    class="px-2 text-xs font-semibold text-slate-400 transition hover:text-rose-300"
                    on:click={() => deleteQuery(query)}
                  >
                    x
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <button
          type="submit"
          class="art-bracket inline-flex items-center gap-2 rounded-md border border-slate-300/70 bg-slate-900/70 px-3 py-2 text-lg font-bold text-slate-100 transition hover:border-amber-300/65 hover:text-amber-200 disabled:cursor-not-allowed disabled:opacity-65 md:text-xl"
          disabled={s3Loading}
        >
          <SearchIcon class="h-4 w-4 md:h-5 md:w-5" />
          {s3Loading ? "Searching" : "Run Search"}
        </button>
      </div>
    </form>

    {#if s3Error}
      <p class="mt-4 text-sm text-rose-300">{s3Error}</p>
    {/if}
  </div>

  <div class="relative z-0 art-fade-up-delayed border-t border-slate-300/65 px-4 py-4 md:px-8 md:py-6">
    {#if viewMode === "file"}
      <S3ResultsTable
        {s3Uri}
        items={s3Results}
        searchedYet={hasSearched}
        onDownload={handleDownload}
        onSort={handleSort}
        {sortBy}
        {sortDirection}
        {editTags}
      />
    {:else}
      <S3FolderExplorer
        searchedYet={hasSearched}
        loading={s3Loading}
        suggestions={folderSuggestions}
        children={folderChildren}
        files={folderFiles}
        breadcrumbs={folderBreadcrumbs}
        activePath={activeFolderPath}
        {s3Uri}
        {sortBy}
        {sortDirection}
        onOpenFolder={openFolder}
        onOpenBreadcrumb={openBreadcrumb}
        onNavigateUp={navigateUp}
        onSort={handleSort}
        onDownload={handleDownload}
      />
    {/if}
  </div>
</section>
