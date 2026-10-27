<script lang="ts">
  import type { Item } from '../lib/item.ts';
  import type { RenderOptions, Renderer, RendererState } from '../lib/renderer.ts';

  interface Props {
    engine: Renderer;
    status: RendererState;
    /** Undefined until the editor has its first item. */
    item: Partial<Item> | undefined;
    options: RenderOptions;
    name: string;
    share: () => Promise<string>;
  }

  let { engine, status, item, options = $bindable(), name, share }: Props = $props();

  const SCALES = [1, 2, 3, 4, 5, 6];
  // At most two CSS pixels per Minecraft pixel; less when the card would not fit the stage.
  const MAX_CSS_PER_PIXEL = 2;
  const STAGE_PADDING = 32;
  const DPR = globalThis.devicePixelRatio || 1;

  let canvas = $state<HTMLCanvasElement>();
  // The drawn card in Minecraft pixels and the export scale it was drawn at.
  let size = $state<{ width: number; height: number; scale: number } | undefined>();
  let stageWidth = $state(0);
  let stageHeight = $state(0);
  let renderError = $state('');
  let message = $state<{ text: string; error: boolean; attempt: number }>({
    text: '',
    error: false,
    attempt: 0,
  });

  // Latest wins: while one card is drawing, only the newest change waits behind it.
  let busy = false;
  let pending: { item: Partial<Item>; options: RenderOptions } | undefined;

  $effect(() => {
    if (!item) {
      return;
    }
    pending = { item, options: $state.snapshot(options) };
    if (!busy) {
      void drawPending(); // failures are kept in renderError
    }
  });

  async function drawPending(): Promise<void> {
    busy = true;
    while (pending) {
      const request = pending;
      pending = undefined;
      try {
        const image = await engine.pixels(request.item, request.options);
        paint(image, request.options.scale);
        renderError = '';
      } catch (error) {
        renderError = error instanceof Error ? error.message : String(error);
      }
    }
    busy = false;
  }

  function paint(image: ImageData, scale: number): void {
    if (!canvas) {
      return;
    }
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.getContext('2d')?.putImageData(image, 0, 0);
    size = { width: image.width / scale, height: image.height / scale, scale };
  }

  // Device pixels per Minecraft pixel. A whole number keeps the pixels even; below two the card would
  // get too small for that, so it takes the fractional fit and gives up a little sharpness instead.
  const devicePerPixel = $derived.by(() => {
    if (!size) {
      return 1;
    }
    const fit = Math.min(
      MAX_CSS_PER_PIXEL * DPR,
      ((stageWidth - STAGE_PADDING) * DPR) / size.width,
      ((stageHeight - STAGE_PADDING) * DPR) / size.height
    );
    return fit >= 2 ? Math.floor(fit) : Math.max(fit, 0.5);
  });
  // Nearest-neighbour only when enlarging; shrinking a large export that way drops whole rows.
  const crisp = $derived(size !== undefined && devicePerPixel >= size.scale);

  function say(text: string, error = false): void {
    message = { text, error, attempt: message.attempt + 1 };
  }

  function fileName(): string {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    return `${slug || 'card'}.png`;
  }

  async function download(): Promise<void> {
    if (!item) {
      return; // the button is disabled until a card is drawn
    }
    try {
      const blob = await engine.png(item, $state.snapshot(options));
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = fileName();
      link.click();
      setTimeout(() => {
        URL.revokeObjectURL(link.href);
      }, 10_000);
      say(`Saved ${link.download}.`);
    } catch (error) {
      say(
        `Could not save the card: ${error instanceof Error ? error.message : String(error)}`,
        true
      );
    }
  }

  async function copyImage(): Promise<void> {
    if (!item) {
      return; // the button is disabled until a card is drawn
    }
    try {
      // The promise goes straight into ClipboardItem, so Safari still counts this as the click's action.
      const png = engine.png(item, $state.snapshot(options));
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })]);
      say('Image copied. Paste it into Discord or anywhere else.');
    } catch {
      say('This browser did not let the page copy an image. Use Download instead.', true);
    }
  }

  async function copyLink(): Promise<void> {
    try {
      await navigator.clipboard.writeText(await share());
      say('Link copied. It opens this card with the same settings.');
    } catch {
      say('The link is in the address bar; the browser did not allow copying it.', true);
    }
  }
</script>

<div class="preview panel">
  <div class="options">
    <fieldset class="segments">
      <legend class="label">Export scale</legend>
      {#each SCALES as scale (scale)}
        <label class="segment">
          <input type="radio" name="scale" value={scale} bind:group={options.scale} />
          {scale}×
        </label>
      {/each}
    </fieldset>
    <fieldset class="segments">
      <legend class="label">Roll colours</legend>
      <label class="segment">
        <input type="radio" name="lerp" value={false} bind:group={options.color_lerp} /> Flat
      </label>
      <label class="segment">
        <input type="radio" name="lerp" value={true} bind:group={options.color_lerp} /> Smooth
      </label>
    </fieldset>
    <div class="toggles">
      <label class="check"
        ><input type="checkbox" bind:checked={options.rolls} /> Roll percentages</label
      >
      <label class="check"><input type="checkbox" bind:checked={options.frame} /> Frame</label>
    </div>
  </div>

  <div
    class="stage"
    class:stage--dark={!options.frame}
    bind:clientWidth={stageWidth}
    bind:clientHeight={stageHeight}
  >
    {#if status.kind !== 'ready' && !size}
      <div class="placeholder">
        {#if status.kind === 'failed'}
          <p class="status--error" role="alert">
            The renderer did not start: {status.error}. Reload the page to try again.
          </p>
        {:else}
          <p role="status">
            {status.stage}…<br /><span class="muted">The first visit downloads about 7 MB.</span>
          </p>
        {/if}
      </div>
    {/if}
    <div class="card" role="img" aria-label={`Card for ${name}`} hidden={!size}>
      <canvas
        bind:this={canvas}
        class:crisp
        style:width={size ? `${(size.width * devicePerPixel) / DPR}px` : undefined}
      ></canvas>
    </div>
  </div>

  <p class="status status--error render-error" role="alert">{renderError}</p>

  <div class="actions">
    <button class="button button--primary" type="button" onclick={download} disabled={!size}>
      Download PNG
    </button>
    <button class="button" type="button" onclick={copyImage} disabled={!size}>Copy image</button>
    <button class="button" type="button" onclick={copyLink}>Copy link</button>
  </div>
  {#key message.attempt}
    <p
      class="status"
      class:status--error={message.error}
      class:status--success={!message.error}
      class:flash={message.attempt > 0}
      role={message.error ? 'alert' : 'status'}
    >
      {message.text}
    </p>
  {/key}
</div>

<style>
  .preview {
    display: grid;
    gap: 16px;
    padding: 20px;
  }

  .options {
    display: grid;
    gap: 12px;
  }

  .toggles {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 20px;
  }

  .stage {
    display: grid;
    place-items: center;
    /* A fixed stage: a taller or shorter card never moves the buttons under it. */
    height: clamp(320px, 60svh, 780px);
    padding: 16px;
    border-radius: var(--fd-radius-md);
    background-color: var(--fd-bg-app);
    background-image: repeating-linear-gradient(135deg, transparent 0 6px, var(--fd-line) 6px 8px);
  }

  /* Without its frame the card is light text on nothing; a dark backdrop keeps it readable. */
  .stage--dark {
    background: #1d1420;
  }

  .card {
    max-width: 100%;
    line-height: 0;
  }

  canvas {
    max-width: 100%;
    height: auto;
    image-rendering: auto;
  }

  canvas.crisp {
    image-rendering: pixelated;
  }

  .placeholder {
    max-width: 30ch;
    text-align: center;
  }

  .placeholder p {
    margin: 0;
  }

  @media (max-width: 900px) {
    /* The editor sits under the preview on narrow screens; leave it room above the fold. */
    .stage {
      height: clamp(280px, 46svh, 560px);
    }
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
</style>
