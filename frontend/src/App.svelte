<script lang="ts">
  let name = "ArtemiS3";
  async function ping() {
    const res = await fetch("/api/test?name=Svelte");
    const data = await res.json();
    alert(JSON.stringify(data))
  }
</script>

<main>
  <h1>Welcome to {name}</h1>
  <p>Frontend is up. NGINX proxies this page and /api to FastAPI.</p>
  <button on:click={ping}>Test API</button>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem
  }
</style>
