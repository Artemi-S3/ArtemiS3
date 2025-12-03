<script lang="ts">
  import { List as ListIcon } from "@lucide/svelte";

  export let onApply: (payload: {
    selectedTypes: string[];              // file types
    minSize?: number;
    maxSize?: number;
    storgageClasses?: string[];
    date?: string;                        // YYYY-MM-DD
    condition?: "after" | "before" | "";
  }) => void = () => {};

  let dropdownOpen = false;
  let selectedTypes: string[] = [];
  let minSizeInput = "";
  let maxSizeInput = "";
  const allStorageClasses = ["STANDARD", "GLACIER", "INTELLIGENT_TIERING"];
  let selectedStorageClasses: string[] = [];
  let dateValue = "";
  let dateCondition: "before" | "after" | "" = "before";

  function toggleDropdown() {
    dropdownOpen = !dropdownOpen;
  }

  function sendFilter() {
    const minSize = minSizeInput ? Number(minSizeInput) : undefined;
    const maxSize = maxSizeInput ? Number(maxSizeInput) : undefined;

    const payload = {
      selectedTypes, 
      minSize: Number.isNaN(minSize as Number) ? undefined : minSize, 
      maxSize: Number.isNaN(maxSize as Number) ? undefined : maxSize, 
      storageClasses: selectedStorageClasses.length > 0 ? selectedStorageClasses : undefined, 
      date: dateValue.trim() || undefined, 
      condition: dateValue.trim() ? dateCondition : ""
    };

    onApply(payload);
    dropdownOpen = false;
  }
</script>

<div class="relative">
  <button 
    type="button"
    on:click={toggleDropdown}
    class="border p-2 rounded bg-gray-100 hover:bg-gray-200 flex items-center gap-2"  
  >
    <ListIcon class="w-4 h-4" />
    <span>Filter</span>
  </button>

  {#if dropdownOpen}
    <div class="absolute mt-1 border rounded bg-white shadow p-4 w-64 z-10">
      <!-- File types -->
       <div class="mb-4">
        <h4 class="font-semibold mb-2">File types</h4>
        <div class="flex flex-col gap-1">
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="zip"
              checked={selectedTypes.includes("zip")}
              bind:group={selectedTypes}
            />
            ZIP
          </label>
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="pdf"
              checked={selectedTypes.includes("pdf")}
              bind:group={selectedTypes}
            />
            PDF
          </label>
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="png"
              checked={selectedTypes.includes("png")}
              bind:group={selectedTypes}
            />
            PNG
          </label>
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="jpg"
              checked={selectedTypes.includes("jpg")}
              bind:group={selectedTypes}
            />
            JPG
          </label>
        </div>
      </div>

      <!-- Size -->
      <div class="mb-4">
        <h4 class="font-semibold mb-2">Size (bytes)</h4>
        <div class="flex gap-2">
          <div class="flex flex-col">
            <label class="text-xs text-grap-600 mb-1">
              Min
              <input
                type="number"
                min="0"
                placeholder="e.g. 1024"
                bind:value={minSizeInput}
                class="border p-1 rounded w-20"
              />
            </label>
          </div>
          <div class="flex flex-col">
            <label class="text-xs text-grap-600 mb-1">
              Max
              <input
                type="number"
                min="0"
                placeholder="e.g. 1048576"
                bind:value={maxSizeInput}
                class="border p-1 rounded w-20"
              />
            </label>
          </div>
        </div>
      </div>

      <!-- Storage Class -->
      <div class="mb-4">
        <h4 class="font-semibold mb-2">Storage class</h4>
        <div class="flex flex-col gap-1">
          {#each allStorageClasses as storageClass}
            <label class="flex items-center gap-2">
              <input 
                type="checkbox"
                value={storageClass}
                checked={selectedStorageClasses.includes(storageClass)}
                bind:group={selectedStorageClasses}
              />
              {storageClass}
            </label>
          {/each}
        </div>
      </div>

      <!-- Date -->
      <div class="mb-4">
        <h4 class="font-semibold mb-2">Last modified</h4>
        <div class="flex gap-2 items center">
          <input
            type="date"
            bind:value={dateValue}
            class="border p-1 rounded w-32"
          />
          <select bind:value={dateCondition} class="border p-1 rounded">
            <option value="before">Before</option>
            <option value="after">After</option>
          </select>
        </div>
      </div>

      <button
        type="button"
        on:click={sendFilter}
        class="mt-2 bg-blue-500 text-white p-2 rounded w-full"
      >
        Apply filters
      </button>
    </div>
  {/if}
</div>