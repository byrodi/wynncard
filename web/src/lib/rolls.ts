// Rolls of a preset's identifications. The values each one can roll come from the site data, worked
// out by wynncard.rolls in Python and checked there against the item API; only the percentage left.

import type { Identification } from './item.ts';

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
export function valueAt(values: readonly number[], percent: number): number {
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
