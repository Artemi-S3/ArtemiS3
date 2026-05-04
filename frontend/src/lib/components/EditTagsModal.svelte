<script lang="ts">
  /** Modal editor for adding/removing tags on a selected S3 object. */
  import { X } from "@lucide/svelte";

  export let editing: string | null;
  export let localTags: string[];
  export let setEditing: (key: string | null) => void;
  export let submitTags: (key: string, tags: string[]) => Promise<void>;

  let tagInput = "";

  $: clearInput(editing);
  /** Resets the tag input whenever edit target changes. */
  function clearInput(_editing: string | null) {
    tagInput = "";
  }

  /** Handles escape/enter keyboard behavior inside the modal. */
  function keydown(e: KeyboardEvent) {
    e.stopPropagation();
    if (e.key === "Escape") {
      setEditing(null);
    } else if (e.key === "Enter") {
      e.preventDefault();
      addToLocal();
    }
  }
  /** Svelte action that wires keyboard handlers and initial focus for dialog. */
  function modalAction(node: HTMLElement) {
    const returnFn: Array<() => void> = [];
    node.addEventListener("keydown", keydown);
    node.focus();
    returnFn.push(() => {
      node.removeEventListener("keydown", keydown);
    });
    return {
      destroy: () => returnFn.forEach((fn) => fn()),
    };
  }
  /** Adds the current text input to local tag list when valid and unique. */
  function addToLocal() {
    localTags =
      localTags.includes(tagInput) || tagInput === ""
        ? localTags
        : [...localTags, tagInput];
    tagInput = "";
  }

  /** Svelte action that portals modal markup into document.body. */
  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        if (node.parentNode) node.parentNode.removeChild(node);
      },
    };
  }
</script>

{#if editing}
  <div
    use:portal
    class="fixed inset-0 z-40 flex h-screen w-screen items-center justify-center"
    role="dialog"
    aria-modal="true"
    tabindex="0"
    use:modalAction
  >
    <div
      class="absolute h-screen w-screen bg-black/45 backdrop-blur-sm"
      role="dialog"
      tabindex="-1"
      on:click={() => setEditing(null)}
      on:keypress={() => setEditing(null)}
    ></div>
    <div
      class="z-50 max-w-xl rounded-md border border-slate-500/55 bg-slate-950/95 shadow-[0_22px_55px_rgba(0,0,0,0.5)]"
    >
      <div
        class="flex items-center justify-between border-b border-slate-600/70 px-3 py-2 text-lg font-semibold text-slate-100"
      >
        <span class="size-6"></span>
        <span>Edit File Tags</span>
        <button
          class="icon-button text-slate-300 hover:text-rose-300"
          on:click={() => setEditing(null)}
        >
          <X size={24} />
        </button>
      </div>
      <div class="flex flex-col gap-4 px-6 py-5 text-sm text-slate-200">
        <div class="space-y-2">
          Editing tags for:
          <div
            class="mono overflow-x-auto rounded border border-slate-600/65 bg-slate-900/80 p-2"
          >
            {editing}
          </div>
        </div>
        <form
          class="flex items-center gap-2 text-nowrap"
          on:submit={(e) => {
            e.preventDefault();
            addToLocal();
          }}
        >
          Enter Tags:
          <input
            class="w-full rounded border border-slate-500/55 bg-slate-900/75 px-2 py-1 text-sm text-slate-100 outline-none focus:border-amber-300/80"
            bind:value={tagInput}
            placeholder="mars-rover-2020"
          />
          <button type="submit" class="button whitespace-nowrap">Add Tag</button
          >
        </form>
        {#if localTags.length > 0}
          <div
            class="flex h-fit w-full flex-wrap gap-2 rounded border border-slate-600/65 bg-slate-900/75 px-3 py-3"
          >
            {#each localTags as tag}
              <div
                class="flex items-center gap-1 rounded-full border border-slate-500/60 bg-slate-800/80 pl-2"
              >
                <span>{tag}</span>
                <button
                  title="Delete Tag"
                  class="cursor-pointer pr-1 text-slate-400 transition hover:text-rose-300"
                  value={tag}
                  on:click={(e) =>
                    (localTags = localTags.filter(
                      (tag) =>
                        tag !== (e.currentTarget as HTMLButtonElement).value,
                    ))}
                >
                  <X size={20} />
                </button>
              </div>
            {/each}
          </div>
        {/if}
        <button
          class="button w-fit self-center"
          on:click={async () => {
            if (!editing) return;
            await submitTags(editing, localTags);
          }}>Save Changes</button
        >
      </div>
    </div>
  </div>
{/if}
