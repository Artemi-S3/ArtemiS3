<script lang="ts">
  import {Search as SearchIcon, Menu as HamburgerMenu, Download as DownloadIcon, List as ListIcon, LayoutGrid} from "@lucide/svelte"

  let name = "ArtemiS3";
  async function ping() {
    const res = await fetch("/api/test?name=Svelte");
    const data = await res.json();
    alert(JSON.stringify(data))
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
  <div class="w-screen h-screen p-8">
    <h1>Welcome to {name}</h1>
    <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
    <button on:click={ping} class="button">Test API</button>
    <h2>Search Page Prototype:</h2>
      <div class="aspect-16/9 mt-2 w-6xl border-2">
        <div class="border-b h-1/6 flex flex-col items-center justify-center">
          <h1>ArtemiS3</h1>
        </div>
        <div class="flex flex-col h-5/6 items-center justify-evenly">
          <div class="flex flex-col items-center pt-4">
            <div class="text-nowrap w-80 flex">
              <input class="w-full !p-2 !rounded-r-none shadow z-2" placeholder="Search for Files" />
              <span class="border border-l-white border-gray-400 flex items-center justify-center
                           rounded-r-lg aspect-1/1 w-fit h-full hover:outline text-gray-500 hover:border-l-gray-400
                           hover:text-gray-700 active:bg-gray-200 cursor-pointer shadow z-1 hover:z-3">
                <SearchIcon />
              </span>
            </div>
          </div>
          <div class="w-5/6 h-8/10 flex flex-col items-center gap-2">
            <div class="w-full flex justify-end relative">
              <div class="relative">
                <button
                  bind:this={sortButtonEl}
                  on:click={() => (showSort = !showSort)}
                  class="flex items-center gap-2 px-3 py-2 bg-gray-100 border rounded hover:bg-gray-200"
                  type="button"
                  aria-expanded={showSort}
                >
                  <HamburgerMenu />
                  <span>Sort</span>
                </button>

                {#if showSort}
                  <div
                    bind:this={sortPanelEl}
                    class="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded shadow-lg z-30 overflow-hidden"
                  >
                    <!-- sort options list -->
                    <div class="flex flex-col">
                      <!-- Name -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("name")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Name</span>
                        {#if sortField === 'name'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Date -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("date")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Date</span>
                        {#if sortField === 'date'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Type -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("type")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Type</span>
                        {#if sortField === 'type'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>

                      <!-- Size -->
                      <button
                        type="button"
                        on:click={() => cycleSortFor("size")}
                        class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                      >
                        <span class="text-sm">Size</span>
                        {#if sortField === 'size'}
                          {@html sortDirection === 'desc' ? DownIcon() : (sortDirection === 'asc' ? UpIcon() : '')}
                        {/if}
                      </button>
                    </div>

                    <!-- footer actions -->
                    <div class="flex justify-between items-center px-2 py-2 border-t bg-gray-50">
                      <button
                        type="button"
                        class="text-xs text-gray-600 hover:underline"
                        on:click={() => { sortField = null; sortDirection = 'none'; }}
                      >
                        Clear
                      </button>
                      <button
                        type="button"
                        class="text-xs px-3 py-1 bg-blue-600 text-white rounded"
                        on:click={() => (showSort = false)}
                      >
                        Done
                      </button>
                    </div>
                  </div>
                {/if}
              </div>
            </div>
            <div class="w-full h-full text-center border rounded">
              <div class="w-full border-b p-2 flex items-center justify-between text-gray-900">
                <span class="max-w-1/2 overflow-x-auto flex gap-2">
                  <h3>Keywords: {testResults.search_request.keywords.join(", ")}</h3>
                  <div class="border-r"></div>
                  <h3>Filters: ...</h3>
                </span>
                <span class="flex items-center gap-2">
                  <button class="button" disabled>Download Selected</button>
                  <button class="button"><ListIcon /></button>
                  <button class="button"><LayoutGrid /></button>
                </span>
              </div>
                <div class="w-full flex flex-col">
                  <div class="w-full pt-2 pb-1 px-6 flex justify-between items-center">
                    <span class="w-full flex justify-between items-center">
                      <span class="w-1/3 text-left flex">
                        <span class="checkbox mr-3 mt-1"></span>
                        <span>Name</span>
                      </span>
                      <span class="w-1/6 text-left">Date Uploaded</span>
                      <span class="w-1/6 text-center">Type</span>
                      <span class="w-1/6 text-left">Size</span>
                    </span>
                    <span class="w-6"></span>
                  </div>
                  <div class="flex flex-col gap-[1px] overflow-y-auto px-2 py-1">
                    {#each testResults.result_files as file, index}
                    
                      <div class={`w-full outline-gray-600 rounded-sm py-1 px-4 flex justify-between items-center
                                  hover:outline focus-within:outline focus-within:outline-blue-500 hover:z-2 focus-within:z-3
                                  ${index % 2 === 0 ? "bg-gray-200 active:bg-gray-300" : "bg-white active:bg-gray-100"}`}>
                        <label class="flex w-full justify-between items-center text-nowrap">
                          <span class="w-1/3 text-left">
                            <input type="checkbox" class="checkbox mr-2 mt-1" />
                            {file.file_name}
                          </span>
                          <span class="w-1/6 text-left">{new Date(file.date_uploaded).toLocaleString()}</span>
                          <span class="w-1/6 text-center">{file.file_type}</span>
                          <span class="w-1/6 text-left">{file.size}</span>
                        </label>
                        <DownloadIcon class="text-gray-700 cursor-pointer" />
                      </div>
                    {/each}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
  </div>
</main>
