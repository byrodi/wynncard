<script lang="ts">
  import type { IndexEntry } from '../lib/data.ts';
  import { TIER_COLOURS } from '../lib/colours.ts';

  interface Props {
    index: readonly IndexEntry[];
    current: string | undefined;
    onpick: (file: string) => Promise<void>;
    onblank: () => void;
  }

  let { index, current, onpick, onblank }: Props = $props();

  const LIMIT = 12;
  let query = $state('');
  let failure = $state('');
  let open = $state(false);

  const matches = $derived.by(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return [];
    }
    const found = index.filter(
      (entry) =>
        entry.name.toLowerCase().includes(needle) ||
        (entry.internal?.toLowerCase().includes(needle) ?? false)
    );
    // Names that start with the query first, then the rest in index order (by name).
    found.sort(
      (a, b) =>
        Number(!a.name.toLowerCase().startsWith(needle)) -
        Number(!b.name.toLowerCase().startsWith(needle))
    );
    return found.slice(0, LIMIT);
  });

  const currentEntry = $derived(index.find((entry) => entry.file === current));

  async function pick(entry: IndexEntry): Promise<void> {
    try {
      await onpick(entry.file);
      query = '';
      failure = '';
      open = false;
    } catch (error) {
      failure = `${entry.name} did not load: ${error instanceof Error ? error.message : String(error)}`;
    }
  }
</script>

<div class="search panel">
  <div class="head">
    <h2>Start from an item</h2>
    <button class="button button--quiet" type="button" onclick={onblank}>Start from scratch</button>
  </div>
  <!-- The results float over the editor, so typing a query never moves the sections below. -->
  <div
    class="combo"
    onfocusin={() => {
      open = true;
    }}
    onfocusout={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
        open = false;
      }
    }}
  >
    <label class="field">
      <span>Search {index.length ? `${index.length.toLocaleString('en')} items` : 'items'}</span>
      <input
        type="search"
        bind:value={query}
        oninput={() => {
          open = true;
        }}
        onkeydown={(event) => {
          if (event.key === 'Escape') {
            open = false;
          }
        }}
        placeholder="Spring, Warp, Nirvana…"
        autocomplete="off"
        spellcheck="false"
      />
    </label>
    {#if open && matches.length}
      <ul class="results" aria-label="Matching items">
        {#each matches as entry (entry.file)}
          <li>
            <button
              type="button"
              class="result"
              onclick={() => {
                void pick(entry); // pick reports its own failure
              }}
            >
              <span class="dot" style:background={TIER_COLOURS[entry.tier] ?? '#fff'}></span>
              <span class="result-name">{entry.name}</span>
              {#if entry.internal}<span class="muted small">{entry.internal}</span>{/if}
              <span class="muted small meta">{entry.tier} {entry.type}, lv. {entry.level}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
  {#if query.trim() && !matches.length}
    <p class="muted small">No item matches “{query.trim()}”.</p>
  {:else}
    <p class="muted small">
      {#if currentEntry}
        Editing <strong>{currentEntry.name}</strong>. Its rolls stay within what the game can roll.
      {:else}
        Custom item: every field is yours to set.
      {/if}
    </p>
  {/if}
  <p class="status status--error" role="alert">{failure}</p>
</div>

<style>
  .search {
    display: grid;
    gap: 12px;
    padding: 20px;
  }

  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .combo {
    position: relative;
  }

  .results {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    right: 0;
    z-index: 10;
    display: grid;
    max-height: min(420px, 60svh);
    overflow-y: auto;
    margin: 0;
    padding: 0;
    list-style: none;
    border: 1px solid var(--fd-control-line);
    border-radius: var(--fd-radius-md);
    background: var(--fd-surface);
    box-shadow: 0 12px 32px rgb(118 52 77 / 14%);
    overflow: hidden;
  }

  .results li + li {
    border-top: 1px solid var(--fd-line-app);
  }

  .result {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 10px;
    min-height: 44px;
    padding: 10px 14px;
    border: 0;
    background: var(--fd-surface);
    color: var(--fd-text);
    text-align: left;
    cursor: pointer;
  }

  .result:focus-visible {
    outline-offset: -3px;
  }

  @media (hover: hover) {
    .result:hover {
      background: var(--fd-rose-soft);
    }
  }

  .result-name {
    font-weight: 600;
  }

  .meta {
    margin-left: auto;
  }

  .small {
    font-size: 13px;
    margin: 0;
  }
</style>
