// Runs wynncard in Pyodide, off the main thread: the same Python that renders cards anywhere else
// draws the preview here, so the browser and the library cannot disagree about a single pixel.

import type { ToWorker, FromWorker } from './renderer.ts';

// Pinned: a new Pyodide is a new Python and a new Pillow, and that is checked before it ships.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';

const DRAW = `
import json
from wynncard import from_dict, render, render_image

def draw(item, options, png):
    item = from_dict(json.loads(item))
    options = json.loads(options)
    if png:
        return 0, 0, render(item, **options)
    image = render_image(item, **options)
    return image.width, image.height, image.tobytes()
`;

interface PyProxy {
  toJs(): unknown;
  destroy(): void;
}

interface Pyodide {
  loadPackage(names: string): Promise<unknown>;
  runPython(code: string): unknown;
  unpackArchive(buffer: ArrayBuffer, format: string, options: { extractDir: string }): void;
  globals: { get(name: string): unknown };
}

interface WorkerScope {
  onmessage: ((event: MessageEvent<ToWorker>) => void) | null;
  postMessage(message: FromWorker, transfer?: Transferable[]): void;
}

// The dom lib types `self` as a window; in this file it is the worker's own scope.
const scope = self as unknown as WorkerScope;
let draw: ((item: string, options: string, png: boolean) => PyProxy) | undefined;
const queue: Array<Extract<ToWorker, { kind: 'render' }>> = [];

scope.onmessage = (event) => {
  const message = event.data;
  switch (message.kind) {
    case 'init':
      boot(message.base).catch((error: unknown) => {
        scope.postMessage({ kind: 'state', state: { kind: 'failed', error: describe(error) } });
      });
      break;
    case 'render':
      queue.push(message);
      drain();
      break;
    default:
      message satisfies never;
  }
};

async function boot(base: string): Promise<void> {
  const state = (stage: string): void => {
    scope.postMessage({ kind: 'state', state: { kind: 'loading', stage } });
  };
  state('Downloading Python');
  const module = (await import(/* @vite-ignore */ `${PYODIDE}pyodide.mjs`)) as {
    loadPyodide(options: { indexURL: string }): Promise<Pyodide>;
  };
  const py = await module.loadPyodide({ indexURL: PYODIDE });
  state('Loading Pillow');
  const [library] = await Promise.all([
    fetch(new URL('py/wynncard.zip', base)).then((response) => {
      if (!response.ok) {
        throw new Error(`Cannot load the renderer: HTTP ${response.status}`);
      }
      return response.arrayBuffer();
    }),
    py.loadPackage('pillow'),
  ]);
  state('Loading wynncard');
  const sitePackages = py.runPython('import site; site.getsitepackages()[0]');
  if (typeof sitePackages !== 'string') {
    throw new Error('Pyodide did not report its site-packages directory');
  }
  py.unpackArchive(library, 'zip', { extractDir: sitePackages });
  py.runPython(DRAW);
  // The first card pays for the font atlases and sprites; pay it before the first real request.
  py.runPython('render_image(from_dict({"name": "warm-up"}), scale=1)');
  draw = py.globals.get('draw') as typeof draw; // the function DRAW has just defined
  scope.postMessage({ kind: 'state', state: { kind: 'ready' } });
  drain();
}

function drain(): void {
  while (draw && queue.length) {
    const request = queue.shift();
    if (!request) {
      return;
    }
    try {
      const result = draw(
        JSON.stringify(request.item),
        JSON.stringify(request.options),
        request.png
      );
      const [width, height, bytes] = result.toJs() as [number, number, Uint8Array]; // DRAW's tuple
      result.destroy();
      const buffer = bytes.slice().buffer;
      scope.postMessage({ kind: 'done', id: request.id, width, height, buffer }, [buffer]);
    } catch (error) {
      scope.postMessage({ kind: 'error', id: request.id, error: describe(error) });
    }
  }
}

/** The last line of a Python traceback, `ValueError: tier must be a string`, is what a person needs. */
function describe(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return message.trim().split('\n').at(-1) ?? message;
}
