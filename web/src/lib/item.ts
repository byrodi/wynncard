// The item as the editor holds it: the dict form of wynncard.spec with every key present.
// The Python side validates again on every render; this side only has to keep the editor's state sane.

export const TIERS = ['normal', 'unique', 'rare', 'set', 'legendary', 'fabled', 'mythic'] as const;
export const ELEMENTS = ['earth', 'thunder', 'water', 'fire', 'air'] as const;
export const DAMAGE_ELEMENTS = ['neutral', ...ELEMENTS] as const;
export const SKILLS = ['strength', 'dexterity', 'intelligence', 'defence', 'agility'] as const;
export const CLASSES = ['warrior', 'mage', 'archer', 'assassin', 'shaman'] as const;
export const ATTACK_SPEEDS = [
  'superSlow',
  'verySlow',
  'slow',
  'normal',
  'fast',
  'veryFast',
  'superFast',
] as const;
export const EMBLEM_SHAPES = [
  'diamond',
  'square',
  'hexagon',
  'shield',
  'sticker',
  'circle',
] as const;
export const EMBLEM_VARIANTS = [1, 2, 3, 4, 5, 6] as const;
export const RESTRICTIONS = ['', 'untradable', 'quest_item'] as const;
export const KINDS = {
  weapon: ['bow', 'spear', 'wand', 'dagger', 'relik'],
  armour: ['helmet', 'chestplate', 'leggings', 'boots'],
  accessory: ['ring', 'bracelet', 'necklace'],
} as const;

export type Kind = keyof typeof KINDS;
export type Skill = (typeof SKILLS)[number];

export interface Identification {
  stat: string;
  value: number;
  roll?: number;
  name?: string;
  unit?: string;
  inverted?: boolean;
  /** Editor only: the base the values it rolls come from, as the item API's `raw`. */
  base?: number;
  /** Editor only: the stat never rolls, its value is its base. */
  fixed?: boolean;
}

export type Requirements = { level: number; class_name: string; quest: string } & Record<
  Skill,
  number
>;

export interface Item {
  name: string;
  tier: string;
  kind: string;
  type: string;
  emblem: string;
  elements: string[];
  restriction: string;
  attack_speed: string;
  average_dps: number | null;
  health: number | null;
  damage: Record<string, [number, number]>;
  defence: Record<string, number>;
  requirements: Requirements;
  identifications: Identification[];
  major_ids: Record<string, string>;
  overall_roll: number | null;
  rerolls: number;
  shiny: { name: string; value: number } | null;
  scales: Array<{ profile: string; score: number }>;
}

export function emptyItem(name = 'New Item'): Item {
  return {
    name,
    tier: 'normal',
    kind: '',
    type: '',
    emblem: 'diamond_1',
    elements: [],
    restriction: '',
    attack_speed: '',
    average_dps: null,
    health: null,
    damage: {},
    defence: {},
    requirements: {
      level: 0,
      class_name: '',
      quest: '',
      strength: 0,
      dexterity: 0,
      intelligence: 0,
      defence: 0,
      agility: 0,
    },
    identifications: [],
    major_ids: {},
    overall_roll: null,
    rerolls: 0,
    shiny: null,
    scales: [],
  };
}

/** The editor's item from untrusted JSON: known keys of the right type are taken, the rest dropped. */
export function toItem(value: unknown): Item {
  const data = isRecord(value) ? value : {};
  const item = emptyItem(text(data.name) || 'Item');
  for (const key of ['tier', 'kind', 'type', 'emblem', 'restriction', 'attack_speed'] as const) {
    item[key] = text(data[key]) || item[key];
  }
  item.elements = list(data.elements).filter((e): e is string => typeof e === 'string');
  item.average_dps = integer(data.average_dps) ?? null;
  item.health = integer(data.health) ?? null;
  for (const [element, range] of entries(data.damage)) {
    const [low, high] = Array.isArray(range) ? range.map(integer) : [];
    if (low !== undefined && high !== undefined) {
      item.damage[element] = [low, high];
    }
  }
  for (const [element, defence] of entries(data.defence)) {
    const parsed = integer(defence);
    if (parsed !== undefined) {
      item.defence[element] = parsed;
    }
  }
  const requirements = isRecord(data.requirements) ? data.requirements : {};
  item.requirements.class_name = text(requirements.class_name);
  item.requirements.quest = text(requirements.quest);
  for (const key of ['level', ...SKILLS] as const) {
    item.requirements[key] = integer(requirements[key]) ?? 0;
  }
  item.identifications = list(data.identifications).flatMap((stat) => {
    const parsed = toIdentification(stat);
    return parsed ? [parsed] : [];
  });
  for (const [name, lore] of entries(data.major_ids)) {
    item.major_ids[name] = text(lore);
  }
  item.overall_roll = number(data.overall_roll) ?? null;
  item.rerolls = integer(data.rerolls) ?? 0;
  if (isRecord(data.shiny)) {
    item.shiny = { name: text(data.shiny.name), value: integer(data.shiny.value) ?? 0 };
  }
  item.scales = list(data.scales).flatMap((scale) =>
    isRecord(scale) ? [{ profile: text(scale.profile), score: number(scale.score) ?? 0 }] : []
  );
  return item;
}

function toIdentification(value: unknown): Identification | undefined {
  if (!isRecord(value) || typeof value.stat !== 'string') {
    return undefined;
  }
  const out: Identification = { stat: value.stat, value: number(value.value) ?? 0 };
  const roll = number(value.roll);
  if (roll !== undefined) {
    out.roll = roll;
  }
  if (typeof value.name === 'string') {
    out.name = value.name;
  }
  if (typeof value.unit === 'string') {
    out.unit = value.unit;
  }
  if (typeof value.inverted === 'boolean') {
    out.inverted = value.inverted;
  }
  // Older share links have no base: the value stands in for it.
  out.base = integer(value.base) ?? Math.round(out.value);
  if (value.fixed === true) {
    out.fixed = true;
  }
  return out;
}

/** The identification as wynncard.spec takes it: the editor's base and fixed flag left out. */
export function specOf(stat: Identification): Identification {
  const { base: _base, fixed: _fixed, ...spec } = stat;
  return spec;
}

/** The item without the keys that still hold their default, for short share links. */
export function compact(item: Item): Partial<Item> {
  const defaults = emptyItem();
  const out: Partial<Item> = { name: item.name };
  for (const key of Object.keys(item) as Array<keyof Item>) {
    if (key !== 'name' && JSON.stringify(item[key]) !== JSON.stringify(defaults[key])) {
      Object.assign(out, { [key]: item[key] });
    }
  }
  return out;
}

export function kindOf(type: string): Kind | undefined {
  return (Object.keys(KINDS) as Kind[]).find((kind) =>
    (KINDS[kind] as readonly string[]).includes(type)
  );
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function entries(value: unknown): Array<[string, unknown]> {
  return isRecord(value) ? Object.entries(value) : [];
}

function list(value: unknown): unknown[] {
  // Array.isArray narrows to any[]; unknown[] only takes that back.
  return Array.isArray(value) ? (value as unknown[]) : [];
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function number(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function integer(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) ? value : undefined;
}
