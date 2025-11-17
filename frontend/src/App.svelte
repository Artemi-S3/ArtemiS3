<script lang="ts">
  import { onMount } from "svelte";
  import {Search as SearchIcon, Menu as HamburgerMenu, Download as DownloadIcon, List as ListIcon, LayoutGrid} from "@lucide/svelte"

  let name = "ArtemiS3";

  let dropdownOpen = false;
  let selectedTypes: string[] = [];
  let dateValue = "";
  let dateCondition = "before";

  function toggleDropdown() {
    dropdownOpen = !dropdownOpen;
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter(t => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  async function sendFilter() {
    const res = await fetch("http://127.0.0.1:8000/api/filter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_types: selectedTypes, date: dateValue, condition: dateCondition })
    });
    const data = await res.json();
    console.log("Response from backend:", data);
  }

import { onMount, onDestroy } from "svelte";

// does not represent finalized json structure, simply for testing purposes
interface SearchRequest {
  keywords: string[]
}
interface FileInfo {
  file_name: string;
  file_type: string;
  size: string;
  date_uploaded: string; // ISO date string
  data_path: string;     // S3 bucket/key path
}
interface SearchResult {
  search_request: SearchRequest;
  result_files: FileInfo[];
}
const testResults: SearchResult = {
  search_request: {
    keywords: [
      "test",
      "results"
    ]
  },
  result_files: [
    {
      file_name: "test-results-1",
      file_type: "png",
      size: "46 KB",
      date_uploaded: "2025-11-03",
      data_path: "https://www.google.com",
    },
        {
      file_name: "test-results-2",
      file_type: "png",
      size: "51 KB",
      date_uploaded: "2025-11-04",
      data_path: "https://www.google.com",
    },  
    {
      file_name: "test-file-1",
      file_type: "pdf",
      size: "231 KB",
      date_uploaded: "2025-11-01",
      data_path: "https://www.google.com",
    },
    {
      file_name: "test-file-2",
      file_type: "txt",
      size: "1.2 KB",
      date_uploaded: "2025-11-02",
      data_path: "https://www.google.com",
    },
    {
      file_name: "results-doc",
      file_type: "docx",
      size: "23 KB",
      date_uploaded: "2025-11-05",
      data_path: "https://www.google.com",
    },
    {
      file_name: "scan-results-1",
      file_type: "csv",
      size: "12 KB",
      date_uploaded: "2025-11-06",
      data_path: "https://www.google.com",
    },
  ]
}

let showSort = false;
console.log(testResults)

// sort state
let sortField: "name" | "date" | "type" | "size" | null = null;
let sortDirection: "none" | "desc" | "asc" = "none";

// elements for click-outside
let sortButtonEl: HTMLElement | null = null;
let sortPanelEl: HTMLElement | null = null;

function cycleSortFor(field: "name" | "date" | "type" | "size") {
  if (sortField !== field) {
    // new field chosen => start with descending
    sortField = field;
    sortDirection = "desc";
  } else {
    // same field clicked => cycle: desc -> asc -> none
    if (sortDirection === "none") {
      sortDirection = "desc";
    } else if (sortDirection === "desc") {
      sortDirection = "asc";
    } else {
      // was asc -> clear
      sortField = null;
      sortDirection = "none";
    }
  }

  // 
  //    IMPLIMENT LATER!!!!
  //    Sorting logic
  //
  console.log("Sort state:", { sortField, sortDirection });
}

// click-outside to close panel
function handleDocClick(e: MouseEvent) {
  const t = e.target as Node;
  if (!showSort) return;
  if (sortPanelEl && sortPanelEl.contains(t)) return;
  if (sortButtonEl && sortButtonEl.contains(t)) return;
  showSort = false;
}

onMount(() => document.addEventListener("click", handleDocClick));
onDestroy(() => document.removeEventListener("click", handleDocClick));

// small inline SVG helpers returned as strings so we can render via {@html ...}
function DownIcon() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg"
         class="inline-block w-4 h-4 text-gray-700"
         fill="none"
         viewBox="0 0 24 24"
         stroke="currentColor">
      <path stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 9l-7 7-7-7" />
    </svg>`;
}

function UpIcon() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg"
         class="inline-block w-4 h-4 text-gray-700"
         fill="none"
         viewBox="0 0 24 24"
         stroke="currentColor">
      <path stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 15l7-7 7 7" />
    </svg>`;
}

</script>

<main>
  <h1>Welcome to {name}</h1>
  <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
  <button on:click={ping}>Test API</button>
    <!-- Dropdown button -->
  <div class="flex items-center gap-4 mt-4">

    <div class="relative">
    <button on:click={toggleDropdown} class="border p-2 rounded bg-gray-100 hover:bg-gray-200">
      Filter ▼
    </button>

    {#if dropdownOpen}
      <div class="absolute mt-1 border rounded bg-white shadow p-4 w-64 z-10">
        
        <!-- File Type Section with Checkboxes -->
        <div class="mb-4">
          <h4 class="font-semibold mb-2">File Types</h4>
          <div class="flex flex-col gap-1">
            <label class="flex items-center gap-2">
              <input type="checkbox" value="txt" checked={selectedTypes.includes("txt")} on:change={() => toggleType("txt")} />
              TXT
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" value="png" checked={selectedTypes.includes("png")} on:change={() => toggleType("png")} />
              PNG
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" value="jpeg" checked={selectedTypes.includes("jpeg")} on:change={() => toggleType("jpeg")} />
              JPEG
            </label>
          </div>
        </div>

        <!-- Date Section -->
        <div class="mb-4">
          <h4 class="font-semibold mb-2">Date</h4>
          <div class="flex gap-2 items-center">
            <input type="text" placeholder="dd/mm/yyyy" bind:value={dateValue} class="border p-1 rounded w-32" />
            <select bind:value={dateCondition} class="border p-1 rounded">
              <option value="before">Before</option>
              <option value="after">After</option>
            </select>
          </div>
        </div>

        <!-- Placeholder Section -->
        <div>
          <h4 class="font-semibold mb-2">Third Section</h4>
          <div class="border p-2 rounded text-gray-400">Coming soon...</div>
        </div>

        <button on:click={sendFilter} class="mt-4 bg-blue-500 text-white p-2 rounded w-full">Send Filter</button>
      </div>
    {/if}
    </div>

    <!-- Search bar -->
    <input type="text" placeholder="Search for files" class="border p-2 rounded flex-1" />
  </div>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem;
  }
</style>
