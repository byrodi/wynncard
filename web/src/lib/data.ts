// The site data written by tools/build_site_data.py: the preset index, one file per preset and the
// identification table. It is our own output, but it still arrives over the network, so it is checked.

import { isRecord, toItem, type Item } from './item.ts';

export interface IndexEntry {
  readonly name: string;
  readonly tier: string;
  readonly type: string;
  readonly level: number;
  readonly file: string;
  /** The internal name when it differs from the printed one, such as Masterwork Aftershock. */
  readonly internal: string | undefined;
}

export interface Preset {
  readonly file: string;
  readonly item: Item;
  /** Wynnpool's weight profiles for the item, empty for the many items it does not weigh. */
  readonly weights: readonly Weight[];
}

export interface Weight {
  readonly name: string;
  /** Weight by stat key; the absolute weights of a profile add up to 1. */
  readonly stats: Readonly<Record<string, number>>;
}

export interface StatInfo {
  readonly key: string;
  readonly name: string;
  readonly unit: string;
  readonly api: string;
  readonly inverted: boolean;
}

export async function loadIndex(): Promise<IndexEntry[]> {
  const rows = await getJson('data/index.json');
  return (Array.isArray(rows) ? (rows as unknown[]) : []).flatMap((row) => {
    if (!Array.isArray(row)) {
      return [];
    }
    const [name, tier, type, level, file, internal] = row as unknown[];
    if (
      typeof name !== 'string' ||
      typeof tier !== 'string' ||
      typeof type !== 'string' ||
      typeof level !== 'number' ||
      typeof file !== 'string'
    ) {
      return [];
    }
    return [
      {
        name,
        tier,
        type,
        level,
        file,
        internal: typeof internal === 'string' ? internal : undefined,
      },
    ];
  });
}

export async function loadPreset(file: string): Promise<Preset> {
  const data = await getJson(`data/items/${encodeURIComponent(file)}.json`);
  if (!isRecord(data)) {
    throw new Error(`Preset ${file} is not an object`);
  }
  // Each identification's value is its base; `fixed` names the ones that never roll.
  const fixed = Array.isArray(data.fixed) ? (data.fixed as unknown[]) : [];
  const item = toItem(data.item);
  for (const stat of item.identifications) {
    stat.base = stat.value;
    if (fixed.includes(stat.stat)) {
      stat.fixed = true;
    }
  }
  const weights = (Array.isArray(data.weights) ? (data.weights as unknown[]) : []).flatMap(
    (profile) => {
      if (!isRecord(profile) || typeof profile.name !== 'string' || !isRecord(profile.stats)) {
        return [];
      }
      const stats: Record<string, number> = {};
      for (const [key, weight] of Object.entries(profile.stats)) {
        if (typeof weight === 'number') {
          stats[key] = weight;
        }
      }
      return [{ name: profile.name, stats }];
    }
  );
  return { file, item, weights };
}

export async function loadStats(): Promise<StatInfo[]> {
  const rows = await getJson('data/stats.json');
  return (Array.isArray(rows) ? (rows as unknown[]) : []).flatMap((row) =>
    isRecord(row) &&
    typeof row.key === 'string' &&
    typeof row.name === 'string' &&
    typeof row.unit === 'string' &&
    typeof row.api === 'string'
      ? [
          {
            key: row.key,
            name: row.name,
            unit: row.unit,
            api: row.api,
            inverted: row.inverted === true,
          },
        ]
      : []
  );
}

async function getJson(path: string): Promise<unknown> {
  const response = await fetch(new URL(path, document.baseURI));
  if (!response.ok) {
    throw new Error(`Cannot load ${path}: HTTP ${response.status}`);
  }
  return (await response.json()) as unknown;
}
