<script lang="ts">
  import { onMount } from 'svelte';
  import BaseFields from './components/BaseFields.svelte';
  import ExtraFields from './components/ExtraFields.svelte';
  import IdentityFields from './components/IdentityFields.svelte';
  import PresetSearch from './components/PresetSearch.svelte';
  import Preview from './components/Preview.svelte';
  import StatFields from './components/StatFields.svelte';
  import { loadIndex, loadPreset, loadStats, type IndexEntry, type StatInfo } from './lib/data.ts';
  import { compact, emptyItem, isRecord, toItem, type Item } from './lib/item.ts';
  import { Renderer, type RenderOptions, type RendererState } from './lib/renderer.ts';
  import { overallRoll, rollPercentage, valueAt } from './lib/rolls.ts';
  import { decodeShare, encodeShare } from './lib/share.ts';

  const START = 'spring';
  const START_ROLL = 80;

  let item = $state<Item>(emptyItem());
  let rolls = $state<Record<string, readonly number[]>>({});
  let preset = $state<string | undefined>();
  // Identifications the preset fixes: the game never rolls them, so the editor shows them as they are.
  let fixed = $state<string[]>([]);
  let options = $state<RenderOptions>({ scale: 4, color_lerp: false, rolls: true, frame: true });
  let autoOverall = $state(true);
  let index = $state<IndexEntry[]>([]);
  let stats = $state<StatInfo[]>([]);
  let dataError = $state('');
  let renderer = $state<RendererState>({ kind: 'loading', stage: 'Starting' });
  // Nothing is drawn before the first item is in place, so the stage does not flash a blank card.
  let started = $state(false);

  const engine = new Renderer((state) => {
    renderer = state;
  });

  // What the worker draws: the editor's item with stray input dropped and the overall worked out.
  const drawn = $derived.by(() => {
    const clean = toItem($state.snapshot(item));
    clean.overall_roll = autoOverall ? overallRoll(clean.identifications) : clean.overall_roll;
    return compact(clean);
  });

  onMount(() => {
    void start(); // errors end up in dataError, shown above the editor
  });

  async function start(): Promise<void> {
    try {
      const [loadedIndex, loadedStats, shared] = await Promise.all([
        loadIndex(),
        loadStats(),
        decodeShare(location.hash),
      ]);
      index = loadedIndex;
      stats = loadedStats;
      if (isRecord(shared)) {
        await restore(shared);
      } else {
        await choosePreset(START);
      }
    } catch (error) {
      dataError = error instanceof Error ? error.message : String(error);
    }
    started = true;
  }

  async function choosePreset(file: string): Promise<void> {
    const loaded = await loadPreset(file);
    item = loaded.item;
    rolls = loaded.rolls;
    fixed = fixedStats(loaded.item, loaded.rolls);
    preset = file;
    autoOverall = true;
    setAllRolls(START_ROLL);
  }

  function startBlank(): void {
    item = emptyItem();
    item.kind = 'weapon';
    item.type = 'spear';
    rolls = {};
    fixed = [];
    preset = undefined;
    autoOverall = true;
  }

  function fixedStats(base: Item, ranges: Readonly<Record<string, readonly number[]>>): string[] {
    return base.identifications.flatMap((stat) => (ranges[stat.stat] ? [] : [stat.stat]));
  }

  function setAllRolls(percent: number): void {
    for (const stat of item.identifications) {
      const values = rolls[stat.stat];
      if (values) {
        stat.value = valueAt(values, percent);
        stat.roll = rollPercentage(values, stat.value);
      }
    }
  }

  function randomRolls(): void {
    for (const stat of item.identifications) {
      const values = rolls[stat.stat];
      if (values) {
        stat.value = values[Math.floor(Math.random() * values.length)] ?? stat.value;
        stat.roll = rollPercentage(values, stat.value);
      }
    }
  }

  async function restore(shared: Record<string, unknown>): Promise<void> {
    if (typeof shared.preset === 'string') {
      const loaded = await loadPreset(shared.preset);
      rolls = loaded.rolls;
      fixed = fixedStats(loaded.item, loaded.rolls);
      preset = shared.preset;
    }
    item = toItem(shared.item);
    autoOverall = shared.auto !== false;
    const saved = isRecord(shared.options) ? shared.options : {};
    if (typeof saved.scale === 'number' && [1, 2, 3, 4, 5, 6].includes(saved.scale)) {
      options.scale = saved.scale;
    }
    for (const key of ['color_lerp', 'rolls', 'frame'] as const) {
      if (typeof saved[key] === 'boolean') {
        options[key] = saved[key];
      }
    }
  }

  async function shareLink(): Promise<string> {
    const hash = await encodeShare({
      item: compact($state.snapshot(item)),
      options: $state.snapshot(options),
      preset,
      auto: autoOverall,
    });
    history.replaceState(null, '', hash);
    return location.href;
  }
</script>

<header class="top wrap">
  <div class="brand">
    <span class="wordmark pixel">wynncard</span>
    <span class="by">by rodi<span class="by-dot">.</span></span>
  </div>
  <p class="tagline muted">Wynncraft item cards that look like the game's tooltips.</p>
  <a class="source" href="https://github.com/byrodi/wynncard">Source on GitHub</a>
</header>

<main class="layout wrap">
  <section class="preview-column" aria-label="Card preview">
    <Preview
      {engine}
      status={renderer}
      item={started ? drawn : undefined}
      bind:options
      name={item.name}
      share={shareLink}
    />
  </section>

  <section class="editor" aria-label="Item editor">
    {#if dataError}
      <p class="fd-notice fd-notice--error" role="alert">
        Item data did not load: {dataError}. Reload the page to try again.
      </p>
    {/if}
    <PresetSearch {index} current={preset} onpick={choosePreset} onblank={startBlank} />
    <IdentityFields bind:item />
    <StatFields
      bind:item
      {rolls}
      {fixed}
      {stats}
      onall={setAllRolls}
      onrandom={randomRolls}
      overall={drawn.overall_roll ?? null}
    />
    <ExtraFields bind:item bind:autoOverall overall={drawn.overall_roll ?? null} />
    <BaseFields bind:item />
  </section>
</main>

<footer class="bottom wrap muted">
  <p>
    Not affiliated with Wynncraft. The fonts, sprites and frames belong to Wynncraft Studios, the
    item data comes from the Wynncraft API. Cards are drawn in your browser by the
    <a href="https://github.com/byrodi/wynncard">wynncard</a> Python library running on Pyodide.
  </p>
</footer>

<style>
  .top {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 24px;
    padding-block: 24px 16px;
  }

  .brand {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .wordmark {
    font-size: 32px;
    line-height: 1;
    color: var(--fd-text);
  }

  .by {
    font-size: 14px;
    font-weight: 600;
    color: var(--fd-muted);
  }

  .by-dot {
    color: var(--fd-brand);
  }

  .tagline {
    margin: 0;
    flex: 1 1 260px;
  }

  .source {
    padding-block: 8px;
  }

  .layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 460px);
    grid-template-areas: 'editor preview';
    gap: 24px;
    align-items: start;
    padding-bottom: 48px;
  }

  .preview-column {
    grid-area: preview;
    position: sticky;
    top: calc(16px + env(safe-area-inset-top, 0px));
  }

  .editor {
    grid-area: editor;
    display: grid;
    gap: 16px;
    min-width: 0;
  }

  .bottom {
    padding-block: 24px 40px;
    border-top: 1px solid var(--fd-line);
    font-size: 14px;
  }

  .bottom p {
    max-width: 75ch;
    margin: 0;
  }

  @media (max-width: 900px) {
    .layout {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas: 'preview' 'editor';
    }

    .preview-column {
      position: static;
    }
  }
</style>
