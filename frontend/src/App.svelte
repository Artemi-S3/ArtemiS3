<script lang="ts">
  import { Menu as HamburgerMenu } from "@lucide/svelte";
  import FilterPanel from "./lib/components/FilterPanel.svelte";
  import S3SearchSection from "./lib/s3/S3SearchSection.svelte";

  async function ping() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      console.log("Health response:", data);
      alert("Backend healthy. See console for details.");
    } catch (err) {
      console.error("Ping failed:", err);
      alert("Ping failed. Check console.");
    }
  }

  // This receives the payload from FilterPanel via prop callback
  async function handleFilterApply(payload: {
    selectedTypes: string[];
    date: string;
    condition: string;
  }) {
    try {
      const res = await fetch("/api/filter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      console.log("Response from backend (filter):", data);
    } catch (err) {
      console.error("Filter request failed:", err);
    }
  }
</script>

<main>
  <h1 class="text-3xl font-bold mb-2">ArtemiS3</h1>

  <div class="flex items-center gap-4 mt-4">
    <FilterPanel onApply={handleFilterApply} />

    <div class="flex items-center flex-1 gap-2">
      <input
        type="text"
        placeholder="Search for files"
        class="border p-2 rounded flex-1"
      />
      <button
        class="border p-2 rounded bg-gray-100 hover:bg-gray-200"
        title="Ping backend"
        on:click={ping}
      >
        <HamburgerMenu class="w-4 h-4" />
      </button>
    </div>
  </div>

  <S3SearchSection />
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem;
  }
</style>
