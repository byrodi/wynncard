// An item from Wynncraft chat as wynncard.wynntils.decode describes it, checked on its way out of the worker.

import { isRecord, toItem, type Item } from './item.ts';

export interface WynntilsStat {
  readonly stat: string;
  /** Undefined in the older formats, which carry `internal_roll` instead. */
  readonly value: number | undefined;
  /** Only with extended encoding; otherwise the game's own base applies. */
  readonly base: number | undefined;
  readonly fixed: boolean;
  readonly internal_roll: number | undefined;
}

export interface WynntilsItem {
  readonly kind: 'gear' | 'crafted';
  readonly name: string;
  readonly identifications: readonly WynntilsStat[];
  readonly rerolls: number;
  readonly shiny: { name: string; value: number } | null;
  /** The decoded fields that share wynncard.spec's names: a crafted item's type, damage and requirements. */
  readonly base: Item;
}

/** Characters from the private-use areas Wynntils packs its item codes into. */
export const WYNNTILS_CODE = /[\u{F0000}-\u{FFFFD}\u{100000}-\u{10FFFD}]/u;

export function parseWynntils(json: string): WynntilsItem {
  const data: unknown = JSON.parse(json);
  if (!isRecord(data) || (data.kind !== 'gear' && data.kind !== 'crafted')) {
    throw new Error('The item decoder answered with something that is not an item');
  }
  const base = toItem({ ...data, identifications: [] });
  const shiny = isRecord(data.shiny) ? data.shiny : undefined;
  return {
    kind: data.kind,
    name: typeof data.name === 'string' ? data.name : '',
    identifications: (Array.isArray(data.identifications)
      ? (data.identifications as unknown[])
      : []
    )
      .filter(isRecord)
      .flatMap((stat) =>
        typeof stat.stat === 'string'
          ? [
              {
                stat: stat.stat,
                value: whole(stat.value),
                base: whole(stat.base),
                fixed: stat.fixed === true,
                internal_roll: whole(stat.internal_roll),
              },
            ]
          : []
      ),
    rerolls: whole(data.rerolls) ?? 0,
    shiny:
      shiny && typeof shiny.name === 'string'
        ? { name: shiny.name, value: whole(shiny.value) ?? 0 }
        : null,
    base,
  };
}

function whole(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) ? value : undefined;
}
