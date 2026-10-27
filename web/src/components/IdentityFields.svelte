<script lang="ts">
  import { ELEMENT_COLOURS, TIER_COLOURS } from '../lib/colours.ts';
  import {
    ELEMENTS,
    EMBLEM_SHAPES,
    EMBLEM_VARIANTS,
    KINDS,
    RESTRICTIONS,
    TIERS,
    kindOf,
    type Item,
    type Kind,
  } from '../lib/item.ts';

  let { item = $bindable() }: { item: Item } = $props();

  const RESTRICTION_LABELS: Record<(typeof RESTRICTIONS)[number], string> = {
    '': 'None',
    untradable: 'Untradable',
    quest_item: 'Quest item',
  };

  const shape = $derived(item.emblem.split('_')[0] ?? 'diamond');
  const variant = $derived(Number(item.emblem.split('_')[1] ?? 1) || 1);

  function setType(type: string): void {
    item.type = type;
    item.kind = kindOf(type) ?? item.kind;
  }

  function toggleElement(element: string, on: boolean): void {
    // The strip under the banners keeps the game's element order.
    item.elements = ELEMENTS.filter((e) => (e === element ? on : item.elements.includes(e)));
  }
</script>

<div class="section panel">
  <h2>Item</h2>
  <div class="grid">
    <label class="field name">
      <span>Name</span>
      <input type="text" bind:value={item.name} maxlength="40" />
    </label>
    <label class="field">
      <span>Type</span>
      <select
        value={item.type}
        onchange={(event) => {
          setType(event.currentTarget.value);
        }}
      >
        {#if !kindOf(item.type)}<option value={item.type}>{item.type || 'Choose a type'}</option
          >{/if}
        {#each Object.keys(KINDS) as kind (kind)}
          <optgroup label={kind}>
            {#each KINDS[kind as Kind] as type (type)}
              <option value={type}>{type}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </label>
  </div>

  <fieldset class="segments">
    <legend class="label">Tier</legend>
    {#each TIERS as tier (tier)}
      <label class="segment">
        <input type="radio" name="tier" value={tier} bind:group={item.tier} />
        <span class="dot" style:background={TIER_COLOURS[tier]}></span>
        {tier}
      </label>
    {/each}
  </fieldset>

  <fieldset class="segments">
    <legend class="label">Elements</legend>
    {#each ELEMENTS as element (element)}
      <label class="segment">
        <input
          type="checkbox"
          checked={item.elements.includes(element)}
          onchange={(event) => {
            toggleElement(element, event.currentTarget.checked);
          }}
        />
        <span class="dot" style:background={ELEMENT_COLOURS[element]}></span>
        {element}
      </label>
    {/each}
  </fieldset>

  <div class="grid">
    <fieldset class="segments">
      <legend class="label">Emblem</legend>
      {#each EMBLEM_SHAPES as option (option)}
        <label class="segment">
          <input
            type="radio"
            name="emblem-shape"
            value={option}
            checked={shape === option}
            onchange={() => {
              item.emblem = `${option}_${variant}`;
            }}
          />
          {option}
        </label>
      {/each}
    </fieldset>
    <label class="field">
      <span>Emblem variant: {variant}</span>
      <input
        type="range"
        min="1"
        max={EMBLEM_VARIANTS.length}
        value={variant}
        oninput={(event) => {
          item.emblem = `${shape}_${event.currentTarget.value}`;
        }}
      />
    </label>
  </div>

  <fieldset class="segments">
    <legend class="label">Restriction</legend>
    {#each RESTRICTIONS as restriction (restriction)}
      <label class="segment">
        <input type="radio" name="restriction" value={restriction} bind:group={item.restriction} />
        {RESTRICTION_LABELS[restriction]}
      </label>
    {/each}
  </fieldset>
</div>

<style>
  .section {
    display: grid;
    gap: 16px;
    padding: 20px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    align-items: end;
  }

  .segment {
    text-transform: capitalize;
  }
</style>
