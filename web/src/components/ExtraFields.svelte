<script lang="ts">
  import type { Item } from '../lib/item.ts';

  interface Props {
    item: Item;
    autoOverall: boolean;
    scaleMode: 'off' | 'weights' | 'manual';
    overall: number | null;
    /** Scores from Wynnpool's weights and the current rolls. */
    weighted: ReadonlyArray<{ profile: string; score: number }>;
    hasWeights: boolean;
  }

  let {
    item = $bindable(),
    autoOverall = $bindable(),
    scaleMode = $bindable(),
    overall,
    weighted,
    hasWeights,
  }: Props = $props();

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

  function setMode(mode: Props['scaleMode']): void {
    scaleMode = mode;
    if (mode === 'manual' && !item.scales.length) {
      item.scales = [{ profile: 'Main', score: 90 }];
    }
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
    <fieldset class="segments">
      <legend class="label">Wynnpool weight scales</legend>
      <label class="segment">
        <input
          type="radio"
          name="scales"
          checked={scaleMode === 'off'}
          onchange={() => {
            setMode('off');
          }}
        /> Off
      </label>
      <label class="segment" class:segment--unavailable={!hasWeights}>
        <input
          type="radio"
          name="scales"
          checked={scaleMode === 'weights'}
          disabled={!hasWeights}
          onchange={() => {
            setMode('weights');
          }}
        /> From Wynnpool
      </label>
      <label class="segment">
        <input
          type="radio"
          name="scales"
          checked={scaleMode === 'manual'}
          onchange={() => {
            setMode('manual');
          }}
        /> By hand
      </label>
    </fieldset>
    {#if !hasWeights}
      <p class="muted note">
        Wynnpool has no weights for this item; scales can still be typed by hand.
      </p>
    {/if}
    {#if scaleMode === 'weights'}
      <ul class="scales scored">
        {#each weighted as scale (scale.profile)}
          <li>
            <span>{scale.profile} Scale</span><span class="score">{scale.score.toFixed(1)}%</span>
          </li>
        {:else}
          <li class="muted">None of the weighted stats have a roll yet.</li>
        {/each}
      </ul>
    {/if}
    {#if scaleMode === 'manual'}
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

  .note {
    margin: 0;
    font-size: 13px;
  }

  /* Exists, but not for this item: the family's hatch instead of a faded control. */
  .segment--unavailable {
    color: var(--fd-muted);
    background-color: var(--fd-bg-app);
    background-image: repeating-linear-gradient(135deg, transparent 0 6px, var(--fd-line) 6px 8px);
    cursor: not-allowed;
  }

  .scored li {
    display: flex;
    justify-content: space-between;
    padding: 6px 2px;
    border-bottom: 1px solid var(--fd-line-app);
    font-size: 14px;
  }

  .score {
    font-variant-numeric: tabular-nums;
  }
</style>
