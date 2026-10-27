// The main thread's side of the render worker: requests go out with an id, replies come back by it.

import type { Item } from './item.ts';

export interface RenderOptions {
  scale: number;
  color_lerp: boolean;
  rolls: boolean;
  frame: boolean;
}

export type RendererState =
  { kind: 'loading'; stage: string } | { kind: 'ready' } | { kind: 'failed'; error: string };

/** Python functions the worker exposes besides drawing; each takes and returns a string. */
export type PythonCall = 'wynntils_decode' | 'wynntils_encode';

export type ToWorker =
  | { kind: 'init'; base: string }
  | {
      kind: 'render';
      id: number;
      item: Partial<Item>;
      options: RenderOptions;
      png: boolean;
    }
  | { kind: 'call'; id: number; fn: PythonCall; arg: string };

export type FromWorker =
  | { kind: 'state'; state: RendererState }
  | { kind: 'done'; id: number; width: number; height: number; buffer: ArrayBuffer }
  | { kind: 'result'; id: number; value: string }
  | { kind: 'error'; id: number; error: string };

type Reply = Extract<FromWorker, { kind: 'done' | 'result' }>;

interface Waiting {
  resolve(reply: Reply): void;
  reject(error: Error): void;
}

export class Renderer {
  private readonly worker: Worker;
  private readonly waiting = new Map<number, Waiting>();
  private nextId = 0;

  constructor(onState: (state: RendererState) => void) {
    this.worker = new Worker(new URL('./render-worker.ts', import.meta.url), { type: 'module' });
    this.worker.onmessage = (event: MessageEvent<FromWorker>) => {
      const message = event.data;
      switch (message.kind) {
        case 'state':
          onState(message.state);
          break;
        case 'done':
        case 'result':
          this.waiting.get(message.id)?.resolve(message);
          this.waiting.delete(message.id);
          break;
        case 'error':
          this.waiting.get(message.id)?.reject(new Error(message.error));
          this.waiting.delete(message.id);
          break;
        default:
          message satisfies never;
      }
    };
    const base = new URL(import.meta.env.BASE_URL, document.baseURI).href;
    this.post({ kind: 'init', base });
  }

  /** The card as pixels for a canvas: no PNG encoding, which costs more than drawing it. */
  async pixels(item: Partial<Item>, options: RenderOptions): Promise<ImageData> {
    const reply = await this.request({ kind: 'render', id: 0, item, options, png: false });
    if (reply.kind !== 'done') {
      throw new Error('The worker answered a drawing with something else');
    }
    return new ImageData(new Uint8ClampedArray(reply.buffer), reply.width, reply.height);
  }

  async png(item: Partial<Item>, options: RenderOptions): Promise<Blob> {
    const reply = await this.request({ kind: 'render', id: 0, item, options, png: true });
    if (reply.kind !== 'done') {
      throw new Error('The worker answered a drawing with something else');
    }
    return new Blob([reply.buffer], { type: 'image/png' });
  }

  /** Runs one of the worker's Python functions; a Python error rejects with its message. */
  async call(fn: PythonCall, arg: string): Promise<string> {
    const reply = await this.request({ kind: 'call', id: 0, fn, arg });
    if (reply.kind !== 'result') {
      throw new Error('The worker answered a call with something else');
    }
    return reply.value;
  }

  private request(message: Extract<ToWorker, { id: number }>): Promise<Reply> {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject });
      this.post({ ...message, id });
    });
  }

  private post(message: ToWorker): void {
    this.worker.postMessage(message);
  }
}
