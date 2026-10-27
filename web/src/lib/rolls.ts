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

/** The overall roll Wynntils puts after the name: the mean of every identification that has a roll. */
export function overallRoll(identifications: readonly Identification[]): number | null {
  const rolls = identifications.flatMap((stat) => (stat.roll === undefined ? [] : [stat.roll]));
  return rolls.length ? rolls.reduce((sum, roll) => sum + roll, 0) / rolls.length : null;
}
