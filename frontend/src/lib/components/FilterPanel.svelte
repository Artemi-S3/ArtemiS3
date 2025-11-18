<script lang="ts">
  import { List as ListIcon } from "@lucide/svelte";

  export let onApply: (payload: {
    selectedTypes: string[]; 
    date: string; 
    condition: string 
  }) => void = () => {};

  let dropdownOpen = false;
  let selectedTypes: string[] = [];
  let dateValue = "";
  let dateCondition = "before";

  function toggleDropdown() {
    dropdownOpen = !dropdownOpen;
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter((t) => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  function sendFilter() {
    onApply({
      selectedTypes: selectedTypes, 
      date: dateValue, 
      condition: dateCondition
    });
    dropdownOpen = false;
  }
</script>

<div class="relative">
  <button 
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
              value="txt"
              checked={selectedTypes.includes("txt")}
              on:change={() => toggleType("txt")}
            />
            TXT
          </label>
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="png"
              checked={selectedTypes.includes("png")}
              on:change={() => toggleType("png")}
            />
            PNG
          </label>
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              value="jpeg"
              checked={selectedTypes.includes("jpeg")}
              on:change={() => toggleType("jpeg")}
            />
            JPEG
          </label>
        </div>
      </div>

      <!-- Date -->
      <div class="mb-4">
        <h4 class="font-semibold mb-2">Date</h4>
        <div class="flex gap-2 items center">
          <input
            type="text"
            placeholder="dd/mm/yyyy"
            bind:value={dateValue}
            class="border p-1 rounded w-32"
          />
          <select bind:value={dateCondition} class="border p-1 rounded">
            <option value="before">Before</option>
            <option value="after">After</option>
          </select>
        </div>
      </div>

      <!-- Placeholder -->
      <div>
        <h4 class="font-semibold mb-2">Third section</h4>
        <div class="border p-2 rounded text-gray-400">Coming soon…</div>
      </div>

      <button
        on:click={sendFilter}
        class="mt-4 bg-blue-500 text-white p-2 rounded w-full"
      >
        Send filter
      </button>
    </div>
  {/if}
</div>