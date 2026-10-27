<script lang="ts">
  import type { Item } from '../lib/item.ts';

  interface Props {
    item: Item;
    autoOverall: boolean;
    overall: number | null;
  }

  let { item = $bindable(), autoOverall = $bindable(), overall }: Props = $props();

  const TRACKERS = [
    'Mobs Killed',
    'Raids Won',
    'Chests Opened',
    'Players Killed',
    'Deaths',
    'Lootruns Completed',
  ];

  function toggleShiny(on: boolean): void {
    item.shiny = on ? { name: 'Mobs Killed', value: 1000 } : null;
  }

  function toggleScales(on: boolean): void {
    item.scales = on ? [{ profile: 'Main', score: 90 }] : [];
  }
</script>

<div class="section panel">
  <h2>Roll details</h2>

  <div class="grid">
    <div class="field">
      <span>Overall roll</span>
      <label class="check">
        <input type="checkbox" bind:checked={autoOverall} />
        Average of the rolls{autoOverall && overall !== null ? `: ${overall.toFixed(1)}%` : ''}
      </label>
      {#if !autoOverall}
        <input
          type="number"
          min="0"
          max="100"
          step="0.1"
          placeholder="none"
          aria-label="Overall roll"
          value={item.overall_roll ?? ''}
          oninput={(event) => {
            const value = Number.parseFloat(event.currentTarget.value);
            item.overall_roll = Number.isFinite(value) ? value : null;
          }}
        />
      {/if}
    </div>
    <label class="field">
      <span>Rerolls</span>
      <input type="number" min="0" step="1" bind:value={item.rerolls} />
    </label>
  </div>

  <div class="block">
    <label class="check">
      <input
        type="checkbox"
        checked={item.shiny !== null}
        onchange={(event) => {
          toggleShiny(event.currentTarget.checked);
        }}
      />
      Shiny, with its tracker
    </label>
    {#if item.shiny}
      <div class="grid">
        <label class="field">
          <span>Tracker</span>
          <input type="text" list="trackers" bind:value={item.shiny.name} />
          <datalist id="trackers">
            {#each TRACKERS as tracker (tracker)}<option value={tracker}></option>{/each}
          </datalist>
        </label>
        <label class="field">
          <span>Count</span>
          <input type="number" min="0" step="1" bind:value={item.shiny.value} />
        </label>
      </div>
    {/if}
  </div>

  <div class="block">
    <label class="check">
      <input
        type="checkbox"
        checked={item.scales.length > 0}
        onchange={(event) => {
          toggleScales(event.currentTarget.checked);
        }}
      />
      Wynnpool weight scales
    </label>
    {#if item.scales.length}
      <ul class="scales">
        {#each item.scales as scale, index (index)}
          <li class="grid scale">
            <label class="field">
              <span>Scale</span>
              <input type="text" bind:value={scale.profile} />
            </label>
            <label class="field">
              <span>Score %</span>
              <input type="number" min="0" max="100" step="0.1" bind:value={scale.score} />
            </label>
            <button
              class="button icon-button"
              type="button"
              aria-label={`Remove the ${scale.profile} scale`}
              title="Remove"
              onclick={() => item.scales.splice(index, 1)}
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
      <button
        class="button add-scale"
        type="button"
        onclick={() => item.scales.push({ profile: 'Scale', score: 50 })}
      >
        Add a scale
      </button>
    {/if}
  </div>
</div>

<style>
  .section {
    display: grid;
    gap: 16px;
    padding: 20px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px 16px;
    align-items: end;
  }

  .block {
    display: grid;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--fd-line-app);
  }

  .scales {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .scale {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  }

  .add-scale {
    justify-self: start;
  }
</style>
