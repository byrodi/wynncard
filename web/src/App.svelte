<script lang="ts">
  import { onMount } from 'svelte';
  import BaseFields from './components/BaseFields.svelte';
  import ExtraFields from './components/ExtraFields.svelte';
  import IdentityFields from './components/IdentityFields.svelte';
  import PresetSearch from './components/PresetSearch.svelte';
  import Preview from './components/Preview.svelte';
  import StatFields from './components/StatFields.svelte';
  import {
    loadIndex,
    loadPreset,
    loadStats,
    type IndexEntry,
    type StatInfo,
    type Weight,
  } from './lib/data.ts';
  import {
    compact,
    emptyItem,
    isRecord,
    kindOf,
    specOf,
    toItem,
    type Identification,
    type Item,
  } from './lib/item.ts';
  import { Renderer, type RenderOptions, type RendererState } from './lib/renderer.ts';
  import {
    overallRoll,
    possibleValues,
    rollPercentage,
    valueAtRoll,
    valueNearest,
    weightedScore,
  } from './lib/rolls.ts';
  import { decodeShare, encodeShare } from './lib/share.ts';
  import { parseWynntils, type WynntilsItem } from './lib/wynntils.ts';

  const START = 'spring';
  const START_ROLL = 80;
  const SCALE_MODES = ['off', 'weights', 'manual'] as const;
  type ScaleMode = (typeof SCALE_MODES)[number];

  let item = $state<Item>(emptyItem());
  let preset = $state<string | undefined>();
  // The preset's own bases, to tell whether a copied item still matches the game's.
  let presetBases = $state<ReadonlyMap<string, { base: number; fixed: boolean }>>(new Map());
  let options = $state<RenderOptions>({ scale: 4, color_lerp: false, rolls: true, frame: true });
  let autoOverall = $state(true);
  // Wynnpool scales: none, scored from Wynnpool's weights and the current rolls, or typed by hand.
  let weights = $state<readonly Weight[]>([]);
  let scaleMode = $state<ScaleMode>('off');
  let index = $state<IndexEntry[]>([]);
  let stats = $state<StatInfo[]>([]);
  let dataError = $state('');
  let renderer = $state<RendererState>({ kind: 'loading', stage: 'Starting' });
  // Nothing is drawn before the first item is in place, so the stage does not flash a blank card.
  let started = $state(false);

  const engine = new Renderer((state) => {
    renderer = state;
  });

  const statInfo = $derived(
    new Map(stats.flatMap((info) => [[info.key, info] as const, [info.api, info] as const]))
  );

  /** Every value the identification can roll from its base, worst first; a fixed one only its base. */
  function valuesOf(stat: Identification): readonly number[] {
    const base = stat.base ?? stat.value;
    if (stat.fixed) {
      return [base];
    }
    return possibleValues(base, stat.inverted ?? statInfo.get(stat.stat)?.inverted ?? false);
  }

  /** The identification with the roll its value has between the worst and best of its base. */
  function withRoll(stat: Identification): Identification {
    const value = stat.fixed ? (stat.base ?? stat.value) : stat.value;
    const roll = stat.fixed ? undefined : rollPercentage(valuesOf(stat), value);
    const { roll: _old, ...rest } = stat;
    return roll === undefined ? { ...rest, value } : { ...rest, value, roll };
  }

  const rolled = $derived(item.identifications.map(withRoll));

  const weighted = $derived(
    weights.flatMap((weight) => {
      const score = weightedScore(weight.stats, rolled);
      return score === undefined ? [] : [{ profile: weight.name, score }];
    })
  );

  // What the worker draws: the editor's item with stray input dropped, rolls, overall and scales worked out.
  const drawn = $derived.by(() => {
    const clean = toItem($state.snapshot(item));
    clean.identifications = clean.identifications.map((stat) => specOf(withRoll(stat)));
    clean.overall_roll = autoOverall ? overallRoll(clean.identifications) : clean.overall_roll;
    if (scaleMode !== 'manual') {
      clean.scales = scaleMode === 'weights' ? weighted : [];
    }
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
    weights = loaded.weights;
    preset = file;
    presetBases = new Map(
      loaded.item.identifications.map((stat) => [
        stat.stat,
        { base: stat.base ?? stat.value, fixed: stat.fixed === true },
      ])
    );
    autoOverall = true;
    if (scaleMode === 'weights' && !weights.length) {
      scaleMode = 'off';
    }
    setAllRolls(START_ROLL);
  }

  function startBlank(): void {
    item = emptyItem();
    item.kind = 'weapon';
    item.type = 'spear';
    forgetPreset();
  }

  function forgetPreset(): void {
    weights = [];
    preset = undefined;
    presetBases = new Map();
    autoOverall = true;
    if (scaleMode === 'weights') {
      scaleMode = 'off';
    }
  }

  function setAllRolls(percent: number): void {
    for (const stat of item.identifications) {
      if (!stat.fixed) {
        stat.value = valueNearest(valuesOf(stat), percent);
      }
    }
  }

  function randomRolls(): void {
    for (const stat of item.identifications) {
      const values = valuesOf(stat);
      if (!stat.fixed) {
        stat.value = values[Math.floor(Math.random() * values.length)] ?? stat.value;
      }
    }
  }

  async function restore(shared: Record<string, unknown>): Promise<void> {
    if (typeof shared.preset === 'string') {
      await choosePreset(shared.preset);
    }
    item = toItem(shared.item);
    autoOverall = shared.auto !== false;
    const mode = SCALE_MODES.find((m) => m === shared.scales);
    scaleMode = mode ?? (item.scales.length ? 'manual' : 'off');
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
      scales: scaleMode,
    });
    history.replaceState(null, '', hash);
    return location.href;
  }

  /** Loads an item pasted from Wynncraft chat; the answer is what the search box tells the person. */
  async function loadWynntils(text: string): Promise<string> {
    const decoded = parseWynntils(await engine.call('wynntils_decode', text));
    const known = decoded.identifications.filter((stat) => statInfo.has(stat.stat));
    if (decoded.kind === 'crafted') {
      loadCrafted(decoded, known);
      return `Loaded ${item.name}, a crafted item shared by Wynntils.`;
    }
    const entry = await gearEntry(decoded);
    if (entry) {
      await choosePreset(entry.file);
    } else {
      item = emptyItem(decoded.name || 'Item');
      forgetPreset();
    }
    const current = new Map(item.identifications.map((stat) => [stat.stat, stat]));
    const next = known.map((stat): Identification => {
      const own = current.get(stat.stat);
      const base = stat.base ?? own?.base ?? stat.value ?? 0;
      const inverted = statInfo.get(stat.stat)?.inverted ?? false;
      const value =
        stat.value ??
        (stat.internal_roll === undefined ? base : valueAtRoll(base, stat.internal_roll, inverted));
      return {
        ...(own ?? { stat: stat.stat }),
        value,
        base,
        fixed: stat.fixed || own?.fixed === true,
      };
    });
    // The code leaves out the stats that never roll; they stay as the item has them.
    const named = new Set(known.map((stat) => stat.stat));
    next.push(...item.identifications.filter((stat) => stat.fixed && !named.has(stat.stat)));
    item.identifications = next;
    item.rerolls = decoded.rerolls;
    item.shiny = decoded.shiny;
    const skipped = decoded.identifications.length - known.length;
    return (
      `Loaded ${decoded.name} from a Wynntils item.` +
      (entry ? '' : ' The game has no item by that name, so its base stats are blank.') +
      (skipped
        ? ` ${skipped} stat${skipped > 1 ? 's' : ''} this site does not know were left out.`
        : '')
    );
  }

  /** The preset a decoded gear item names; of twins like the two Warps, the one with its stats. */
  async function gearEntry(decoded: WynntilsItem): Promise<IndexEntry | undefined> {
    const twins = index.filter(
      (entry) => entry.name === decoded.name || entry.internal === decoded.name
    );
    if (twins.length < 2) {
      return twins[0];
    }
    for (const entry of twins) {
      const keys = new Set((await loadPreset(entry.file)).item.identifications.map((s) => s.stat));
      if (decoded.identifications.every((stat) => keys.has(stat.stat))) {
        return entry;
      }
    }
    return twins[0];
  }

  function loadCrafted(decoded: WynntilsItem, known: WynntilsItem['identifications']): void {
    const loaded = decoded.base;
    loaded.name = decoded.name || `Crafted ${loaded.type || 'item'}`;
    loaded.kind = kindOf(loaded.type) ?? '';
    // A crafted item's stats have no rolls on the card: each is fixed at its value.
    loaded.identifications = known.map((stat) => ({
      stat: stat.stat,
      value: stat.value ?? 0,
      base: stat.value ?? 0,
      fixed: true,
    }));
    loaded.shiny = decoded.shiny;
    item = loaded;
    forgetPreset();
  }

  /**
   * The item as Wynntils shares it in chat. An item the game has travels as itself, so Wynntils draws
   * it from its own data with these rolls; anything else travels as crafted gear.
   */
  function itemCode(): { code: Promise<string>; note: string } {
    const snapshot = $state.snapshot(item);
    const entry = index.find((candidate) => candidate.file === preset);
    const encodable = snapshot.identifications.flatMap((stat) => {
      const key = statInfo.get(stat.stat)?.key;
      return key ? [{ ...stat, stat: key }] : [];
    });
    const skipped = snapshot.identifications.length - encodable.length;
    const leftOut = skipped
      ? ` ${skipped} custom stat${skipped > 1 ? 's' : ''} Wynntils does not know ${skipped > 1 ? 'were' : 'was'} left out.`
      : '';
    if (entry?.name === snapshot.name) {
      const sameBases =
        encodable.length === presetBases.size &&
        encodable.every((stat) => {
          const own = presetBases.get(stat.stat);
          return own !== undefined && own.base === stat.base && own.fixed === (stat.fixed === true);
        });
      const payload = {
        kind: 'gear',
        name: entry.name,
        extended: !sameBases,
        identifications: encodable.map((stat) => ({
          stat: stat.stat,
          value: stat.fixed ? stat.base : stat.value,
          base: stat.base,
          fixed: stat.fixed === true,
        })),
        rerolls: snapshot.rerolls,
        shiny: snapshot.shiny,
        powder_slots: 0,
        powders: [],
      };
      return {
        code: engine.call('wynntils_encode', JSON.stringify(payload)),
        note:
          `Copied ${entry.name} for Wynntils: paste it into Wynncraft chat. ` +
          'Tier, damage and requirements come from the game, the rest from this card.' +
          leftOut,
      };
    }
    const payload = {
      kind: 'crafted',
      name: snapshot.name,
      type: snapshot.type,
      attack_speed: snapshot.attack_speed,
      average_dps: snapshot.average_dps,
      damage: snapshot.damage,
      health: snapshot.health,
      defence: snapshot.defence,
      requirements: snapshot.requirements,
      identifications: encodable.map((stat) => ({ stat: stat.stat, value: stat.value })),
      shiny: null,
      powder_slots: 0,
      powders: [],
    };
    return {
      code: engine.call('wynntils_encode', JSON.stringify(payload)),
      note:
        'Copied as a crafted item for Wynntils: an item the game does not have travels that way.' +
        leftOut,
    };
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
      {itemCode}
    />
  </section>

  <section class="editor" aria-label="Item editor">
    {#if dataError}
      <p class="fd-notice fd-notice--error" role="alert">
        Item data did not load: {dataError}. Reload the page to try again.
      </p>
    {/if}
    <PresetSearch
      {index}
      current={preset}
      onpick={choosePreset}
      onblank={startBlank}
      onwynntils={loadWynntils}
    />
    <IdentityFields bind:item />
    <StatFields
      bind:item
      {rolled}
      {stats}
      {valuesOf}
      onall={setAllRolls}
      onrandom={randomRolls}
      overall={drawn.overall_roll ?? null}
    />
    <ExtraFields
      bind:item
      bind:autoOverall
      bind:scaleMode
      overall={drawn.overall_roll ?? null}
      {weighted}
      hasWeights={weights.length > 0}
    />
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
