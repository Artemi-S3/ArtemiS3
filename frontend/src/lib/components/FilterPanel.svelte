<script lang="ts">
  /** Search filter panel for file-mode queries, including preset management. */
  import { ListFilter as ListIcon } from "@lucide/svelte";

  export let onSave: (() => void) | null = null;
  export let onDelete: ((name: string) => void) | null = null;
  export let onApply: (payload: {
    selectedTypes: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    date?: string;
    condition?: "after" | "before" | "";
  }) => void = () => {};
  export let initialFilters: {
    suffixes?: string[];
    minSize?: number;
    maxSize?: number;
    storageClasses?: string[];
    modifiedAfter?: string;
    modifiedBefore?: string;
  } | null = null;
  export let savedFilters: { name: string; filters: typeof initialFilters }[] = [];

  let dropdownOpen = false;
  let selectedTypes: string[] = [];
  let minSizeInput = "";
  let maxSizeInput = "";
  const allStorageClasses = ["STANDARD", "GLACIER", "INTELLIGENT_TIERING"];
  let selectedStorageClasses: string[] = [];
  let dateValue = "";
  let dateCondition: "before" | "after" | "" = "before";
  let minUnit = 1;
  let maxUnit = 1;
  const unitConversion = [
    { label: "B", value: 1 },
    { label: "KB", value: 1024 },
    { label: "MB", value: 1024 ** 2 },
    { label: "GB", value: 1024 ** 3 },
  ];
  const defaultFileTypes = [
    "zip",
    "pdf",
    "png",
    "jpg",
    "txt",
    "geojson",
    "kml",
    "kmz",
  ];
  let customType = "";

  let showSavedFilters = false;
  let savedFilterSearch = "";
  let filteredSavedFilters: { name: string; filters: typeof initialFilters }[] = [];
  let lastInitialFilters: any = null;

  /** Returns currently selected filters in backend-compatible shape. */
  export function getCurrentFilters() {
    const minSize = minSizeInput
      ? Math.round(Number(minSizeInput) * minUnit)
      : undefined;
    const maxSize = maxSizeInput
      ? Math.round(Number(maxSizeInput) * maxUnit)
      : undefined;

    const result: {
      suffixes?: string[];
      minSize?: number;
      maxSize?: number;
      storageClasses?: string[];
      modifiedAfter?: string;
      modifiedBefore?: string;
    } = {};

    if (selectedTypes.length > 0) result.suffixes = selectedTypes;
    if (typeof minSize === "number") result.minSize = minSize;
    if (typeof maxSize === "number") result.maxSize = maxSize;
    if (selectedStorageClasses.length > 0) {
      result.storageClasses = selectedStorageClasses;
    }

    if (dateValue) {
      if (dateCondition === "after") {
        result.modifiedAfter = dateValue;
      } else {
        result.modifiedBefore = dateValue;
      }
    }

    return result;
  }

  /** Toggles the filter dropdown visibility. */
  function toggleDropdown() {
    dropdownOpen = !dropdownOpen;
  }

  /** Formats decimal values without excessive precision noise. */
  function formatDisplayNumber(value: number): string {
    const rounded = Math.round(value * 1000) / 1000;
    return Number.isInteger(rounded) ? String(rounded) : String(rounded);
  }

  /** Converts byte counts into value/unit pairs for the size UI inputs. */
  function bytesToInputAndUnit(
    bytes?: number,
    preferredUnit?: number,
  ): { input: string; unit: number } {
    if (typeof bytes !== "number" || Number.isNaN(bytes)) {
      return { input: "", unit: 1 };
    }

    if (preferredUnit && preferredUnit > 0) {
      return {
        input: formatDisplayNumber(bytes / preferredUnit),
        unit: preferredUnit,
      };
    }

    for (let i = unitConversion.length - 1; i >= 0; i--) {
      const unit = unitConversion[i].value;
      const scaled = bytes / unit;

      // Prefer larger units when the displayed value stays readable.
      if (scaled >= 1) {
        return { input: formatDisplayNumber(scaled), unit };
      }
    }

    return { input: String(bytes), unit: 1 };
  }

  $: {
    selectedTypes;
    minSizeInput;
    maxSizeInput;
    selectedStorageClasses;
    dateValue;
    dateCondition;
    minUnit;
    maxUnit;

    if (dropdownOpen && !showSavedFilters) {
      sendFilter();
    }
  }

  $: if (initialFilters && initialFilters !== lastInitialFilters) {
    lastInitialFilters = initialFilters;

    selectedTypes = initialFilters.suffixes ?? [];
    const minDisplay = bytesToInputAndUnit(
      initialFilters.minSize,
      dropdownOpen ? minUnit : undefined,
    );
    minSizeInput = minDisplay.input;
    minUnit = minDisplay.unit;
    const maxDisplay = bytesToInputAndUnit(
      initialFilters.maxSize,
      dropdownOpen ? maxUnit : undefined,
    );
    maxSizeInput = maxDisplay.input;
    maxUnit = maxDisplay.unit;
    selectedStorageClasses = initialFilters.storageClasses ?? [];

    if (initialFilters.modifiedAfter) {
      dateValue = initialFilters.modifiedAfter;
      dateCondition = "after";
    } else if (initialFilters.modifiedBefore) {
      dateValue = initialFilters.modifiedBefore;
      dateCondition = "before";
    } else {
      dateValue = "";
    }
  }

  $: filteredSavedFilters =
    savedFilterSearch.trim() === ""
      ? savedFilters
      : savedFilters.filter((f) =>
          f.name.toLowerCase().includes(savedFilterSearch.toLowerCase()),
        );

  /** Emits the currently selected filters to the parent component. */
  function sendFilter() {
    const minSize = minSizeInput
      ? Math.round(Number(minSizeInput) * minUnit)
      : undefined;
    const maxSize = maxSizeInput
      ? Math.round(Number(maxSizeInput) * maxUnit)
      : undefined;

    onApply({
      selectedTypes,
      minSize: Number.isNaN(minSize as number) ? undefined : minSize,
      maxSize: Number.isNaN(maxSize as number) ? undefined : maxSize,
      storageClasses:
        selectedStorageClasses.length > 0 ? selectedStorageClasses : undefined,
      date: dateValue.trim() || undefined,
      condition: dateValue.trim() ? dateCondition : "",
    });
  }

  /** Clears all filter controls and emits an empty filter payload. */
  function resetFilters() {
    selectedTypes = [];
    minSizeInput = "";
    maxSizeInput = "";
    selectedStorageClasses = [];
    dateValue = "";
    dateCondition = "before";
    minUnit = 1;
    maxUnit = 1;
    sendFilter();
  }

  /** Adds a custom file suffix to selected types. */
  function addCustomType() {
    const type = customType.trim().toLowerCase().replace(".", "");
    if (type && !selectedTypes.includes(type)) {
      selectedTypes = [...selectedTypes, type];
      customType = "";
    }
  }

  /** Svelte action that closes the dropdown when clicking outside. */
  function clickOutside(node: HTMLElement) {
    const handleClick = (event: MouseEvent) => {
      if (
        dropdownOpen &&
        node &&
        !node.contains(event.target as Node) &&
        !event.defaultPrevented
      ) {
        dropdownOpen = false;
      }
    };

    document.addEventListener("click", handleClick, true);
    return {
      destroy() {
        document.removeEventListener("click", handleClick, true);
      },
    };
  }

  /** Applies a saved preset to local controls and emits the updated filter payload. */
  function applySavedFilter(filter: any) {
    selectedTypes = filter.suffixes ?? [];
    const minDisplay = bytesToInputAndUnit(filter.minSize);
    minSizeInput = minDisplay.input;
    minUnit = minDisplay.unit;
    const maxDisplay = bytesToInputAndUnit(filter.maxSize);
    maxSizeInput = maxDisplay.input;
    maxUnit = maxDisplay.unit;
    selectedStorageClasses = filter.storageClasses ?? [];
    if (filter.modifiedAfter) {
      dateValue = filter.modifiedAfter;
      dateCondition = "after";
    } else if (filter.modifiedBefore) {
      dateValue = filter.modifiedBefore;
      dateCondition = "before";
    } else {
      dateValue = "";
    }
    sendFilter();
    dropdownOpen = false;
  }
</script>

<div class="relative">
  <button
    type="button"
    on:click|stopPropagation={toggleDropdown}
    class="art-bracket inline-flex items-center gap-1 rounded-md border border-slate-400/50 bg-slate-900/65 px-2 py-1 text-base font-semibold text-slate-100 transition hover:bg-slate-800/75"
  >
    <ListIcon class="h-4 w-4" />
    <span>Filter</span>
    <span class="text-sm text-slate-300">v</span>
  </button>

  {#if dropdownOpen}
    <div
      use:clickOutside
      class="absolute right-0 z-40 mt-2 w-[22rem] max-w-[calc(100vw-2rem)] max-h-[70vh] overflow-y-auto overscroll-contain rounded-md border border-slate-400/55 bg-slate-950/95 p-4 shadow-[0_18px_45px_rgba(2,8,16,0.75)]"
    >
      <div class="mb-3 flex gap-2">
        <button
          type="button"
          class={`rounded border px-2 py-1 text-xs font-semibold tracking-wide ${
            !showSavedFilters
              ? "border-amber-300/60 bg-amber-400/20 text-amber-200"
              : "border-slate-500/45 bg-slate-900/70 text-slate-200"
          }`}
          on:click={() => (showSavedFilters = false)}
        >
          New Filter
        </button>
        <button
          type="button"
          class={`rounded border px-2 py-1 text-xs font-semibold tracking-wide ${
            showSavedFilters
              ? "border-amber-300/60 bg-amber-400/20 text-amber-200"
              : "border-slate-500/45 bg-slate-900/70 text-slate-200"
          }`}
          on:click={() => (showSavedFilters = true)}
        >
          Saved Filters
        </button>
      </div>

      {#if !showSavedFilters}
        <div class="space-y-4">
          <div>
            <h4 class="mb-2 text-sm font-semibold text-slate-100">File types</h4>
            <div class="grid grid-cols-2 gap-1 text-xs">
              {#each defaultFileTypes as type}
                <label class="inline-flex items-center gap-2 text-slate-200">
                  <input
                    class="h-3.5 w-3.5 accent-amber-400"
                    type="checkbox"
                    value={type}
                    bind:group={selectedTypes}
                  />
                  <span class="uppercase">{type}</span>
                </label>
              {/each}
              {#each selectedTypes.filter((t) => !defaultFileTypes.includes(t)) as type}
                <label class="inline-flex items-center gap-2 text-amber-200">
                  <input
                    class="h-3.5 w-3.5 accent-amber-400"
                    type="checkbox"
                    value={type}
                    bind:group={selectedTypes}
                  />
                  <span class="uppercase">{type}</span>
                </label>
              {/each}
            </div>
            <input
              type="text"
              placeholder="+ add type (csv, tif, lbl)"
              bind:value={customType}
              on:keydown={(e) => e.key === "Enter" && addCustomType()}
              class="mt-2 w-full rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none focus:border-amber-300/75"
            />
          </div>

          <div>
            <h4 class="mb-1 text-sm font-semibold text-slate-100">Size</h4>
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <span class="text-[10px] uppercase tracking-wider text-slate-400">Min</span>
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    placeholder="0"
                    bind:value={minSizeInput}
                    class="w-full rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none focus:border-amber-300/75"
                  />
                  <select
                    bind:value={minUnit}
                    class="rounded border border-slate-500/45 bg-slate-900/75 px-1 py-1 text-xs text-slate-100 outline-none"
                  >
                    {#each unitConversion as unit}
                      <option class="bg-slate-900" value={unit.value}>
                        {unit.label}
                      </option>
                    {/each}
                  </select>
                </div>
              </div>

              <div class="space-y-1">
                <span class="text-[10px] uppercase tracking-wider text-slate-400">Max</span>
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    placeholder="Any"
                    bind:value={maxSizeInput}
                    class="w-full rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none focus:border-amber-300/75"
                  />
                  <select
                    bind:value={maxUnit}
                    class="rounded border border-slate-500/45 bg-slate-900/75 px-1 py-1 text-xs text-slate-100 outline-none"
                  >
                    {#each unitConversion as unit}
                      <option class="bg-slate-900" value={unit.value}>
                        {unit.label}
                      </option>
                    {/each}
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-sm font-semibold text-slate-100">Storage class</h4>
            <div class="space-y-1 text-xs">
              {#each allStorageClasses as storageClass}
                <label class="inline-flex items-center gap-2 text-slate-200">
                  <input
                    class="h-3.5 w-3.5 accent-amber-400"
                    type="checkbox"
                    value={storageClass}
                    checked={selectedStorageClasses.includes(storageClass)}
                    bind:group={selectedStorageClasses}
                  />
                  <span>{storageClass}</span>
                </label>
              {/each}
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-sm font-semibold text-slate-100">Last modified</h4>
            <div class="flex items-center gap-2">
              <input
                type="date"
                bind:value={dateValue}
                class="rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none"
              />
              <select
                bind:value={dateCondition}
                class="rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none"
              >
                <option class="bg-slate-900" value="before">Before</option>
                <option class="bg-slate-900" value="after">After</option>
              </select>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <button
              type="button"
              on:click={resetFilters}
              class="text-xs font-medium text-slate-300 transition hover:text-amber-300"
            >
              Clear all filters
            </button>
            <button
              type="button"
              class="rounded border border-amber-300/60 bg-amber-300/90 px-2 py-1 text-xs font-semibold text-slate-950 transition hover:bg-amber-200"
              on:click={() => onSave && onSave()}
            >
              Save Filter
            </button>
          </div>
        </div>
      {:else}
        <input
          type="text"
          placeholder="Search saved filters..."
          bind:value={savedFilterSearch}
          class="mb-2 w-full rounded border border-slate-500/45 bg-slate-900/75 px-2 py-1 text-xs text-slate-100 outline-none focus:border-amber-300/75"
        />

        {#if filteredSavedFilters.length === 0}
          <p class="text-xs italic text-slate-400">
            {savedFilterSearch ? "No matching filters found" : "No saved filters yet"}
          </p>
        {:else}
          <div class="flex max-h-64 flex-col gap-1 overflow-y-auto pr-1">
            {#each filteredSavedFilters as filter}
              <div class="rounded border border-slate-600/45 bg-slate-900/75 p-2">
                <div class="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    class="flex-1 text-left text-sm font-semibold text-slate-100 hover:text-amber-200"
                    on:click={() => applySavedFilter(filter.filters)}
                  >
                    {filter.name}
                  </button>
                  <button
                    type="button"
                    class="px-1 text-xs font-semibold text-slate-400 transition hover:text-rose-300"
                    on:click={() => onDelete && onDelete(filter.name)}
                  >
                    x
                  </button>
                </div>
                <div class="mt-1 text-[11px] text-slate-400">
                  {#if filter.filters?.suffixes}
                    {filter.filters.suffixes.join(", ")}
                  {/if}
                  {#if filter.filters?.minSize}
                    | min {filter.filters.minSize}
                  {/if}
                  {#if filter.filters?.maxSize}
                    | max {filter.filters.maxSize}
                  {/if}
                  {#if filter.filters?.storageClasses}
                    | {filter.filters.storageClasses.join(", ")}
                  {/if}
                  {#if filter.filters?.modifiedAfter}
                    | after {filter.filters.modifiedAfter}
                  {/if}
                  {#if filter.filters?.modifiedBefore}
                    | before {filter.filters.modifiedBefore}
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>
