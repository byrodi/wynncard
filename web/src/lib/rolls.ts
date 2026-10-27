// Rolls of an identification, the TypeScript twin of wynncard.rolls: the slider needs the values a base
// can roll on every keystroke, too often to ask the worker. rolls.test.ts holds both to the same cases.

import type { Identification } from './item.ts';

/**
 * Every value an identification with this base can roll, as printed, from the worst roll to the best:
 * the base times 30 to 130 percent (70 to 130 for a negative base), rounded like Wynntils and never 0.
 * Spell costs (`inverted`) are worked out on the negated base. A base of 0 only rolls 0.
 */
export function possibleValues(base: number, inverted: boolean): number[] {
  if (base === 0) {
    return [0];
  }
  const stored = inverted ? -base : base;
  const found = new Set<number>();
  for (let roll = stored > 0 ? 30 : 70; roll <= 130; roll++) {
    found.add(scaled(stored, roll, inverted));
  }
  return [...found].sort((a, b) => a - b).map((value) => (inverted ? -value : value));
}

/** The value an internal roll gives, as Wynntils' calculateStatValue. */
export function valueAtRoll(base: number, internalRoll: number, inverted: boolean): number {
  const value = scaled(inverted ? -base : base, internalRoll, inverted);
  return inverted ? -value : value;
}

/**
 * `stored * roll / 100` rounded like Wynntils: halves away from zero for a positive base and towards
 * it for a negative one, the other way round for spell costs. Integer arithmetic keeps the halves exact.
 */
function scaled(stored: number, roll: number, inverted: boolean): number {
  const product = stored * roll;
  const whole = Math.trunc(product / 100);
  const rest = Math.abs(product - whole * 100);
  const halfAway = stored > 0 !== inverted;
  const value = rest > 50 || (rest === 50 && halfAway) ? whole + Math.sign(product) : whole;
  return value || (stored > 0 ? 1 : -1);
}

/**
 * Roll percentage of `value` among `values`, every value an identification can roll from worst to
 * best. It is Wynntils' formula: where the value sits between the worst and the best one. Undefined
 * when there is only one possible value.
 */
export function rollPercentage(values: readonly number[], value: number): number | undefined {
  const worst = values[0];
  const best = values.at(-1);
  if (worst === undefined || best === undefined || worst === best) {
    return undefined;
  }
  return ((value - worst) / (best - worst)) * 100;
}

/** The possible value whose roll percentage is closest to `percent`. */
export function valueNearest(values: readonly number[], percent: number): number {
  const worst = values[0] ?? 0;
  const target = worst + ((values.at(-1) ?? worst) - worst) * (percent / 100);
  let closest = worst;
  for (const value of values) {
    if (Math.abs(value - target) < Math.abs(closest - target)) {
      closest = value;
    }
  }
  return closest;
}

/**
 * The score of one Wynnpool weight profile: the weighted mean of the roll percentages of the
 * profile's stats that the item has, where a negative weight scores the roll from the other end.
 * Rounded to a tenth; undefined when the item has none of the profile's stats with a roll.
 */
export function weightedScore(
  weights: Readonly<Record<string, number>>,
  identifications: readonly Identification[]
): number | undefined {
  let score = 0;
  let matched = 0;
  for (const stat of identifications) {
    const weight = weights[stat.stat];
    if (weight === undefined || stat.roll === undefined) {
      continue;
    }
    matched += Math.abs(weight);
    score += weight > 0 ? stat.roll * weight : (100 - stat.roll) * -weight;
  }
  return matched > 0 ? Math.round((10 * score) / matched) / 10 : undefined;
}

/** The overall roll Wynntils puts after the name: the mean of every identification that has a roll. */
export function overallRoll(identifications: readonly Identification[]): number | null {
  const rolls = identifications.flatMap((stat) => (stat.roll === undefined ? [] : [stat.roll]));
  return rolls.length ? rolls.reduce((sum, roll) => sum + roll, 0) / rolls.length : null;
}
