<script lang="ts">
  /** Root application shell with global header and search section. */
  import S3SearchSection from "./lib/components/S3SearchSection.svelte";
</script>

<main class="min-h-screen text-slate-100 art-soft-in">
  <header class="border-b border-slate-500/35 bg-slate-950/65 backdrop-blur">
    <div
      class="mx-auto flex w-full max-w-[1600px] items-center justify-between px-6 py-4 md:px-10"
    >
      <h1
        class="text-3xl font-extrabold leading-none tracking-tight md:text-4xl"
      >
        <a href="/" class="inline-block text-inherit no-underline">
          <span>Artemi</span><span class="text-amber-400">S3</span>
        </a>
      </h1>
      <nav
        class="flex items-center gap-6 text-base font-bold tracking-wide md:text-xl"
      >
        <a
          href="https://github.com/Artemi-S3/ArtemiS3/blob/main/README.md"
          class="text-slate-100/90 transition hover:text-amber-300">[Docs]</a
        >
        <a
          href="https://www.sce.nau.edu/capstone/projects/CS/2026/ArtemiS3_F25/"
          class="text-slate-100/90 transition hover:text-amber-300">[About]</a
        >
      </nav>
    </div>
  </header>

  <section class="mx-auto w-full max-w-[1600px] px-3 py-6 md:px-6 md:py-8">
    <S3SearchSection />
  </section>
</main>
