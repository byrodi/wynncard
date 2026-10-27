import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  overallRoll,
  possibleValues,
  rollPercentage,
  valueAtRoll,
  valueNearest,
  weightedScore,
} from './rolls.ts';

// The cases of tests/test_spec.py RollsTest, so the two implementations cannot drift apart.
test('a positive base rolls 30 to 130 percent', () => {
  assert.deepEqual(
    possibleValues(30, false),
    Array.from({ length: 31 }, (_, i) => 9 + i)
  );
  assert.deepEqual(possibleValues(300, false).slice(0, 3), [90, 93, 96]);
});

test('halves round like Wynntils', () => {
  assert.deepEqual(possibleValues(5, false), [2, 3, 4, 5, 6, 7]);
  assert.deepEqual(possibleValues(-5, true), [-1, -2, -3, -4, -5, -6]);
});

test('a negative base rolls 70 to 130 percent', () => {
  assert.deepEqual(possibleValues(-10, false), [-13, -12, -11, -10, -9, -8, -7]);
  assert.equal(rollPercentage(possibleValues(-10, false), -7), 100);
});

test('a spell cost reduction is best at its largest', () => {
  assert.deepEqual(possibleValues(-2, true), [-1, -2, -3]);
  assert.equal(rollPercentage(possibleValues(-11, true), -14), 100);
  assert.deepEqual(possibleValues(5, true), [7, 6, 5, 4]);
});

test('a single possible value has no percentage', () => {
  assert.deepEqual(possibleValues(1, false), [1]);
  assert.equal(rollPercentage([1], 1), undefined);
  assert.deepEqual(possibleValues(0, false), [0]);
});

test('an internal roll gives the value Wynntils calculates', () => {
  assert.equal(valueAtRoll(20, 130, false), 26);
  assert.equal(valueAtRoll(20, 30, false), 6);
  assert.equal(valueAtRoll(-3, 130, true), -4);
});

test('valueNearest picks the closest value the item can roll', () => {
  const manaRegen = possibleValues(20, false);
  assert.equal(valueNearest(manaRegen, 100), 26);
  assert.equal(valueNearest(manaRegen, 52), 16);
  assert.equal(valueNearest([-1, -2, -3, -4], 70), -3);
});

test('a weight profile is a weighted mean, negative weights from the other end', () => {
  const stats = [
    { stat: 'MISC_MANA_REGEN', value: 20, roll: 90 },
    { stat: 'MISC_HEALTH', value: 900, roll: 20 },
    { stat: 'SKILL_AGILITY', value: 5 },
  ];
  // (90 * 0.6 + (100 - 20) * 0.4) / 1.0
  assert.equal(weightedScore({ MISC_MANA_REGEN: 0.6, MISC_HEALTH: -0.4 }, stats), 86);
  // Stats the item lacks leave the mean over the ones it has.
  assert.equal(weightedScore({ MISC_MANA_REGEN: 0.5, MISC_WALK_SPEED: 0.5 }, stats), 90);
  assert.equal(weightedScore({ SKILL_AGILITY: 1 }, stats), undefined);
});

test('overall is the mean of the rolled identifications', () => {
  assert.equal(
    overallRoll([
      { stat: 'a', value: 1, roll: 100 },
      { stat: 'b', value: 1 },
      { stat: 'c', value: 1, roll: 50 },
    ]),
    75
  );
  assert.equal(overallRoll([{ stat: 'a', value: 1 }]), null);
});
