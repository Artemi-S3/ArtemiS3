<script>
  let s3Bucket = "";
  async function refreshIndex() {
    if (s3Bucket !== "") {
      const queries = new URLSearchParams();
      queries.set("s3_uri", s3Bucket);
      fetch(`/api/s3/refresh?${queries.toString()}`);
    }
  }
</script>

<main>
  <div class="p-4 my-2 border w-fit rounded flex gap-2 items-center">
    Index Refresh test:
    <input
      id="s3Bucket"
      placeholder="s3://bucket/prefix"
      bind:value={s3Bucket}
      required
    />
    <button class="button" onclick={refreshIndex}>Refresh Index</button>
  </div>
  <div class="border rounded p-4 w-fit">
    Test Buckets:
    <ul>
      <li>s3://asc-pds-services</li>
      <li>s3://asc-pds-services/pigpen</li>
      <li>s3://asc-astropedia</li>
      <li>s3://asc-astropedia/Mars</li>
    </ul>
  </div>
</main>
