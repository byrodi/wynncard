<script lang="ts">
  import type { StatInfo } from '../lib/data.ts';
  import type { Identification, Item } from '../lib/item.ts';
  import { overallRoll, rollPercentage, valueNearest } from '../lib/rolls.ts';

  interface Props {
    item: Item;
    /** The identifications with the rolls their values have, in the editor's order. */
    rolled: readonly Identification[];
    stats: readonly StatInfo[];
    valuesOf: (stat: Identification) => readonly number[];
    overall: number | null;
    onall: (percent: number) => void;
    onrandom: () => void;
  }

  let { item = $bindable(), rolled, stats, valuesOf, overall, onall, onrandom }: Props = $props();

  const GROUPS = [
    ['SKILL_', 'Skill points'],
    ['MISC_', 'General'],
    ['DEFENCE_', 'Defence'],
    ['DAMAGE_', 'Damage'],
    ['CRITICAL_', 'Damage'],
    ['SPELL_', 'Spell costs'],
  ] as const;
  const NEW_BASE = 10;

  const byKey = $derived(new Map(stats.flatMap((s) => [[s.key, s] as const, [s.api, s] as const])));
  const grouped = $derived(
    [...new Set(GROUPS.map(([, label]) => label))].map((label) => ({
      label,
      stats: stats.filter((s) =>
        GROUPS.some(([prefix, group]) => group === label && s.key.startsWith(prefix))
      ),
    }))
  );
  const rolling = $derived(item.identifications.some((stat) => !stat.fixed));
  // The top slider shows the mean of the rolls as they are, so moving any one roll moves it too.
  const average = $derived(overallRoll(rolled) ?? 0);
  let adding = $state('');

  function unit(stat: Identification): string {
    return stat.unit ?? byKey.get(stat.stat)?.unit ?? '';
  }

  function optionLabel(info: StatInfo): string {
    return `${info.name}${info.unit && info.unit !== ' tier' ? ` (${info.unit.trim()})` : ''}`;
  }

  function signed(value: number): string {
    return `${value > 0 ? '+' : ''}${value}`;
  }

  function setStat(stat: Identification, key: string): void {
    if (key === '') {
      stat.name ??= byKey.get(stat.stat)?.name ?? 'Custom Stat';
      stat.stat = stat.name;
      return;
    }
    stat.stat = key;
    delete stat.name;
    delete stat.unit;
    delete stat.inverted;
  }

  /** A new base keeps the roll where it was: the value moves to the same spot in the new range. */
  function setBase(stat: Identification, raw: string): void {
    const base = Number.parseInt(raw, 10);
    if (!Number.isFinite(base)) {
      return;
    }
    const percent = rollPercentage(valuesOf(stat), stat.value) ?? 70;
    stat.base = base;
    stat.value = stat.fixed ? base : valueNearest(valuesOf(stat), percent);
  }

  function setFixed(stat: Identification, fixed: boolean): void {
    stat.fixed = fixed;
    stat.value = stat.base ?? stat.value;
  }

  function add(): void {
    const stat: Identification =
      adding === ''
        ? { stat: 'Custom Stat', name: 'Custom Stat', value: NEW_BASE }
        : { stat: adding, value: NEW_BASE };
    stat.base = NEW_BASE;
    item.identifications.push(stat);
    adding = '';
  }
</script>

<div class="section panel">
  <div class="head">
    <h2>Identifications</h2>
    {#if overall !== null}
      <span class="muted">Overall {overall.toFixed(1)}%</span>
    {/if}
  </div>

  {#if rolling}
    <div class="all">
      <label class="field">
        <span>All rolls, {average.toFixed(1)}% on average</span>
        <input
          type="range"
          min="0"
          max="100"
          step="0.1"
          value={average}
          oninput={(event) => {
            onall(Number(event.currentTarget.value));
          }}
        />
      </label>
      <div class="all-buttons">
        <button
          class="button"
          type="button"
          onclick={() => {
            onall(100);
          }}
        >
          Perfect
        </button>
        <button class="button" type="button" onclick={onrandom}>Random</button>
      </div>
    </div>
  {/if}

  {#if item.identifications.length === 0}
    <p class="muted empty">No identifications yet. Add one below.</p>
  {/if}

  <ul class="rows">
    {#each item.identifications as stat, index (index)}
      {@const values = valuesOf(stat)}
      {@const roll = rolled[index]?.roll}
      {@const known = byKey.has(stat.stat)}
      <li class="row">
        <div class="line">
          <label class="field stat-pick">
            <span>Stat</span>
            <select
              value={known ? (byKey.get(stat.stat)?.key ?? '') : ''}
              onchange={(event) => {
                setStat(stat, event.currentTarget.value);
              }}
            >
              <option value="">Custom stat…</option>
              {#each grouped as group (group.label)}
                <optgroup label={group.label}>
                  {#each group.stats as info (info.key)}
                    <option value={info.key}>{optionLabel(info)}</option>
                  {/each}
                </optgroup>
              {/each}
            </select>
          </label>
          <label class="field base">
            <span>Base</span>
            <input
              type="number"
              step="1"
              value={stat.base ?? stat.value}
              oninput={(event) => {
                setBase(stat, event.currentTarget.value);
              }}
            />
          </label>
          <label class="check fixed" title="The stat never rolls: its value is its base">
            <input
              type="checkbox"
              checked={stat.fixed === true}
              onchange={(event) => {
                setFixed(stat, event.currentTarget.checked);
              }}
            />
            Fixed
          </label>
          <button
            class="button icon-button"
            type="button"
            aria-label={`Remove ${stat.name ?? byKey.get(stat.stat)?.name ?? stat.stat}`}
            title="Remove"
            onclick={() => item.identifications.splice(index, 1)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </div>

        {#if !known}
          <div class="line custom">
            <label class="field">
              <span>Name</span>
              <input
                type="text"
                value={stat.name ?? stat.stat}
                oninput={(event) => {
                  stat.name = event.currentTarget.value;
                  stat.stat = event.currentTarget.value || 'Custom Stat';
                }}
              />
            </label>
            <label class="field unit">
              <span>Unit</span>
              <select bind:value={stat.unit}>
                <option value="">none</option>
                <option value="%">%</option>
                <option value="/3s">/3s</option>
                <option value="/5s">/5s</option>
                <option value=" tier">tier</option>
              </select>
            </label>
          </div>
        {/if}

        {#if stat.fixed}
          <p class="muted range">
            Fixed at {signed(stat.base ?? stat.value)}{unit(stat)}, it never rolls
          </p>
        {:else}
          <label class="field roll">
            <span class="row-label">
              <span>Value</span>
              <span class="value">
                {signed(stat.value)}{unit(stat)}
                {#if roll !== undefined}<span class="muted">[{roll.toFixed(1)}%]</span>{/if}
              </span>
            </span>
            <input
              type="range"
              min="0"
              max={values.length - 1}
              value={Math.max(0, values.indexOf(stat.value))}
              aria-valuetext={`${signed(stat.value)}${unit(stat)}${roll === undefined ? '' : `, roll ${roll.toFixed(1)}%`}`}
              oninput={(event) => {
                stat.value = values[Number(event.currentTarget.value)] ?? stat.value;
              }}
            />
          </label>
          <span class="muted range">
            Rolls {signed(values[0] ?? 0)} to {signed(values.at(-1) ?? 0)}
          </span>
        {/if}
      </li>
    {/each}
  </ul>

  <div class="add">
    <label class="field">
      <span>Add an identification</span>
      <select bind:value={adding}>
        <option value="">Custom stat…</option>
        {#each grouped as group (group.label)}
          <optgroup label={group.label}>
            {#each group.stats as info (info.key)}
              <option value={info.key}>{optionLabel(info)}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </label>
    <button class="button" type="button" onclick={add}>Add</button>
  </div>
</div>

<style>
  .section {
    display: grid;
    gap: 16px;
    padding: 20px;
  }

  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  .all {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 12px 16px;
    padding: 12px 14px;
    border-radius: var(--fd-radius-md);
    background: var(--fd-rose-soft);
  }

  .all .field {
    flex: 1 1 220px;
  }

  .all-buttons {
    display: flex;
    gap: 8px;
  }

  .empty {
    margin: 0;
  }

  .rows {
    display: grid;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .row {
    display: grid;
    gap: 8px;
    padding-block: 14px;
  }

  .row + .row {
    border-top: 1px solid var(--fd-line-app);
  }

  .line {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 10px;
  }

  .stat-pick {
    flex: 1 1 220px;
  }

  .base {
    flex: 0 1 110px;
  }

  .custom .field {
    flex: 1 1 160px;
  }

  .custom .unit {
    flex: 0 1 110px;
  }

  .fixed {
    font-size: 14px;
  }

  .row-label {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--fd-text);
    font-size: 14px;
  }

  .value {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .range {
    margin: 0;
    font-size: 12px;
  }

  .add {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 8px;
  }

  .add .field {
    flex: 1 1 240px;
  }
</style>
