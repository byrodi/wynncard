<script lang="ts">
  import type { StatInfo } from '../lib/data.ts';
  import type { Identification, Item } from '../lib/item.ts';
  import { overallRoll, rollPercentage } from '../lib/rolls.ts';

  interface Props {
    item: Item;
    rolls: Readonly<Record<string, readonly number[]>>;
    fixed: readonly string[];
    stats: readonly StatInfo[];
    overall: number | null;
    onall: (percent: number) => void;
    onrandom: () => void;
  }

  let { item = $bindable(), rolls, fixed, stats, overall, onall, onrandom }: Props = $props();

  const GROUPS = [
    ['SKILL_', 'Skill points'],
    ['MISC_', 'General'],
    ['DEFENCE_', 'Defence'],
    ['DAMAGE_', 'Damage'],
    ['CRITICAL_', 'Damage'],
    ['SPELL_', 'Spell costs'],
  ] as const;

  const byKey = $derived(new Map(stats.flatMap((s) => [[s.key, s] as const, [s.api, s] as const])));
  const grouped = $derived(
    [...new Set(GROUPS.map(([, label]) => label))].map((label) => ({
      label,
      stats: stats.filter((s) =>
        GROUPS.some(([prefix, group]) => group === label && s.key.startsWith(prefix))
      ),
    }))
  );
  const rolling = $derived(item.identifications.some((stat) => rolls[stat.stat]));
  // The top slider shows the mean of the rolls as they are, so moving any one roll moves it too.
  const average = $derived(overallRoll(item.identifications) ?? 0);
  let adding = $state('');

  function label(stat: Identification): string {
    return stat.name ?? byKey.get(stat.stat)?.name ?? stat.stat;
  }

  function unit(stat: Identification): string {
    return stat.unit ?? byKey.get(stat.stat)?.unit ?? '';
  }

  function optionLabel(info: StatInfo): string {
    return `${info.name}${info.unit && info.unit !== ' tier' ? ` (${info.unit.trim()})` : ''}`;
  }

  function signed(value: number): string {
    return `${value > 0 ? '+' : ''}${value}`;
  }

  function slide(stat: Identification, values: readonly number[], index: number): void {
    stat.value = values[index] ?? stat.value;
    stat.roll = rollPercentage(values, stat.value);
  }

  function setStat(stat: Identification, key: string): void {
    if (key === '') {
      stat.stat = stat.name ?? 'Custom Stat';
      stat.name ??= stat.stat;
      return;
    }
    stat.stat = key;
    delete stat.name;
    delete stat.unit;
    delete stat.inverted;
  }

  function setRoll(stat: Identification, raw: string): void {
    const roll = Number.parseFloat(raw);
    if (Number.isFinite(roll)) {
      stat.roll = roll;
    } else {
      delete stat.roll;
    }
  }

  function add(): void {
    if (adding === '') {
      item.identifications.push({ stat: 'Custom Stat', name: 'Custom Stat', value: 1 });
    } else {
      item.identifications.push({ stat: adding, value: 1 });
    }
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
      {@const values = rolls[stat.stat]}
      <li class="row">
        {#if values}
          <div class="rolled">
            <label class="field">
              <span class="row-label">
                <span>{label(stat)}</span>
                <span class="value">
                  {signed(stat.value)}{unit(stat)}
                  {#if stat.roll !== undefined}<span class="muted">[{stat.roll.toFixed(1)}%]</span
                    >{/if}
                </span>
              </span>
              <input
                type="range"
                min="0"
                max={values.length - 1}
                value={Math.max(0, values.indexOf(stat.value))}
                aria-valuetext={`${signed(stat.value)}${unit(stat)}, roll ${stat.roll?.toFixed(1) ?? 'fixed'}%`}
                oninput={(event) => {
                  slide(stat, values, Number(event.currentTarget.value));
                }}
              />
            </label>
            <span class="muted range">{signed(values[0] ?? 0)} to {signed(values.at(-1) ?? 0)}</span
            >
          </div>
        {:else if fixed.includes(stat.stat)}
          <div class="rolled">
            <span class="row-label">
              <span>{label(stat)}</span>
              <span class="value">{signed(stat.value)}{unit(stat)}</span>
            </span>
            <span class="muted range">Fixed on this item, it never rolls</span>
          </div>
        {:else}
          <div class="custom">
            <label class="field stat-pick">
              <span>Stat</span>
              <select
                value={byKey.has(stat.stat) ? (byKey.get(stat.stat)?.key ?? '') : ''}
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
            {#if !byKey.has(stat.stat)}
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
              <label class="field small">
                <span>Unit</span>
                <select bind:value={stat.unit}>
                  <option value="">none</option>
                  <option value="%">%</option>
                  <option value="/3s">/3s</option>
                  <option value="/5s">/5s</option>
                  <option value=" tier">tier</option>
                </select>
              </label>
            {/if}
            <label class="field small">
              <span>Value</span>
              <input type="number" step="1" bind:value={stat.value} />
            </label>
            <label class="field small">
              <span>Roll %</span>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder="none"
                value={stat.roll ?? ''}
                oninput={(event) => {
                  setRoll(stat, event.currentTarget.value);
                }}
              />
            </label>
          </div>
        {/if}
        <button
          class="button icon-button"
          type="button"
          aria-label={`Remove ${label(stat)}`}
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
    display: flex;
    align-items: center;
    gap: 12px;
    padding-block: 10px;
  }

  .row + .row {
    border-top: 1px solid var(--fd-line-app);
  }

  .rolled {
    flex: 1;
    min-width: 0;
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
    font-size: 12px;
  }

  .custom {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 10px;
    min-width: 0;
  }

  .stat-pick {
    grid-column: span 2;
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
