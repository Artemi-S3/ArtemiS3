<script lang="ts">
  import IndexRefreshForm from "./lib/s3/IndexRefreshForm.svelte";
  import S3SearchSection from "./lib/s3/S3SearchSection.svelte";
</script>

<main>
  <h1 class="text-3xl font-bold mb-2">ArtemiS3</h1>
  <S3SearchSection />
  <IndexRefreshForm />
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem;
  }
</style>
