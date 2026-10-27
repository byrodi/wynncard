<script lang="ts">
  import { ELEMENT_COLOURS } from '../lib/colours.ts';
  import {
    ATTACK_SPEEDS,
    CLASSES,
    DAMAGE_ELEMENTS,
    ELEMENTS,
    SKILLS,
    type Item,
  } from '../lib/item.ts';

  let { item = $bindable() }: { item: Item } = $props();

  const weapon = $derived(item.kind === 'weapon');
  let majorName = $state('');

  function speedLabel(speed: string): string {
    return speed.replace(/([A-Z])/g, ' $1').replace(/^./, (first) => first.toUpperCase());
  }

  function whole(raw: string): number | undefined {
    const value = Number.parseInt(raw, 10);
    return Number.isFinite(value) ? value : undefined;
  }

  function without<T>(record: Record<string, T>, key: string): Record<string, T> {
    return Object.fromEntries(Object.entries(record).filter(([name]) => name !== key));
  }

  function setDamage(element: string, side: 0 | 1, raw: string): void {
    const value = whole(raw);
    const range: [number, number] = [...(item.damage[element] ?? [0, 0])];
    if (value === undefined && range[side === 0 ? 1 : 0] === 0) {
      item.damage = without(item.damage, element); // both ends blank: no damage of this element
      return;
    }
    range[side] = value ?? 0;
    item.damage[element] = range;
  }

  function setDefence(element: string, raw: string): void {
    const value = whole(raw);
    if (value === undefined) {
      item.defence = without(item.defence, element);
    } else {
      item.defence[element] = value;
    }
  }

  function setOptional(key: 'average_dps' | 'health', raw: string): void {
    item[key] = whole(raw) ?? null;
  }

  function addMajor(): void {
    const name = majorName.trim() || 'Major ID';
    item.major_ids[name] = item.major_ids[name] ?? 'What it does.';
    majorName = '';
  }

  function removeMajor(name: string): void {
    item.major_ids = without(item.major_ids, name);
  }
</script>

<details class="panel">
  <summary><h2>Base stats and requirements</h2></summary>
  <div class="body">
    {#if weapon}
      <div class="grid">
        <label class="field">
          <span>Attack speed</span>
          <select bind:value={item.attack_speed}>
            <option value="">none</option>
            {#each ATTACK_SPEEDS as speed (speed)}<option value={speed}>{speedLabel(speed)}</option
              >{/each}
          </select>
        </label>
        <label class="field">
          <span>Average DPS</span>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="none"
            value={item.average_dps ?? ''}
            oninput={(event) => {
              setOptional('average_dps', event.currentTarget.value);
            }}
          />
        </label>
      </div>
      <fieldset class="table">
        <legend class="label">Damage, low to high</legend>
        {#each DAMAGE_ELEMENTS as element (element)}
          <div class="table-row">
            <span class="element"
              ><span class="dot" style:background={ELEMENT_COLOURS[element]}></span>{element}</span
            >
            <input
              type="number"
              min="0"
              step="1"
              placeholder="–"
              aria-label={`${element} damage, low`}
              value={item.damage[element]?.[0] ?? ''}
              oninput={(event) => {
                setDamage(element, 0, event.currentTarget.value);
              }}
            />
            <input
              type="number"
              min="0"
              step="1"
              placeholder="–"
              aria-label={`${element} damage, high`}
              value={item.damage[element]?.[1] ?? ''}
              oninput={(event) => {
                setDamage(element, 1, event.currentTarget.value);
              }}
            />
          </div>
        {/each}
      </fieldset>
    {:else}
      <label class="field narrow">
        <span>Health</span>
        <input
          type="number"
          step="1"
          placeholder="none"
          value={item.health ?? ''}
          oninput={(event) => {
            setOptional('health', event.currentTarget.value);
          }}
        />
      </label>
      <fieldset class="table">
        <legend class="label">Defence</legend>
        {#each ELEMENTS as element (element)}
          <div class="table-row table-row--single">
            <span class="element"
              ><span class="dot" style:background={ELEMENT_COLOURS[element]}></span>{element}</span
            >
            <input
              type="number"
              step="1"
              placeholder="–"
              aria-label={`${element} defence`}
              value={item.defence[element] ?? ''}
              oninput={(event) => {
                setDefence(element, event.currentTarget.value);
              }}
            />
          </div>
        {/each}
      </fieldset>
    {/if}

    <h3 class="label">Requirements</h3>
    <div class="grid">
      <label class="field">
        <span>Combat level</span>
        <input type="number" min="0" max="200" step="1" bind:value={item.requirements.level} />
      </label>
      <label class="field">
        <span>Class</span>
        <select bind:value={item.requirements.class_name}>
          <option value="">any</option>
          {#each CLASSES as name (name)}<option value={name}>{name}</option>{/each}
        </select>
      </label>
      <label class="field">
        <span>Quest</span>
        <input type="text" bind:value={item.requirements.quest} placeholder="none" />
      </label>
    </div>
    <div class="skills">
      {#each SKILLS as skill (skill)}
        <label class="field">
          <span>{skill}</span>
          <input type="number" min="0" step="1" bind:value={item.requirements[skill]} />
        </label>
      {/each}
    </div>

    <h3 class="label">Major IDs</h3>
    {#each Object.keys(item.major_ids) as name (name)}
      <div class="major">
        <label class="field">
          <span>{name}</span>
          <textarea bind:value={item.major_ids[name]}></textarea>
        </label>
        <button
          class="button icon-button"
          type="button"
          aria-label={`Remove ${name}`}
          title="Remove"
          onclick={() => {
            removeMajor(name);
          }}
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
    {/each}
    <div class="add">
      <label class="field">
        <span>New major ID name</span>
        <input type="text" bind:value={majorName} placeholder="Freerunner" />
      </label>
      <button class="button" type="button" onclick={addMajor}>Add</button>
    </div>
  </div>
</details>

<style>
  details {
    padding: 20px;
  }

  summary {
    min-height: 32px;
    cursor: pointer;
  }

  summary h2 {
    display: inline;
  }

  .body {
    display: grid;
    gap: 16px;
    padding-top: 16px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px 16px;
    align-items: end;
  }

  .narrow {
    max-width: 220px;
  }

  .table {
    display: grid;
    gap: 6px;
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
  }

  .table legend {
    margin-bottom: 6px;
    padding: 0;
  }

  .table-row {
    display: grid;
    grid-template-columns: 110px minmax(0, 1fr) minmax(0, 1fr);
    gap: 8px;
    align-items: center;
  }

  .table-row--single {
    grid-template-columns: 110px minmax(0, 200px);
  }

  .element {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    text-transform: capitalize;
    font-size: 14px;
  }

  h3 {
    margin: 0;
    font-size: 13px;
  }

  .skills {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 10px;
  }

  .skills span {
    text-transform: capitalize;
  }

  .major,
  .add {
    display: flex;
    align-items: end;
    gap: 8px;
  }

  .major .field,
  .add .field {
    flex: 1;
  }
</style>
