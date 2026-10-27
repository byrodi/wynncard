import assert from 'node:assert/strict';
import { test } from 'node:test';
import { overallRoll, rollPercentage, valueAt } from './rolls.ts';

// Values as tools/build_site_data.py writes them, worst first.
const MANA_REGEN = Array.from({ length: 21 }, (_, i) => 6 + i); // raw 20: 6 to 26
const SPELL_COST = [-1, -2, -3, -4]; // raw -3, a cost reduction: -4 is the best roll

test('roll percentage follows Wynntils', () => {
  assert.equal(rollPercentage(MANA_REGEN, 26), 100);
  assert.equal(rollPercentage(MANA_REGEN, 6), 0);
  assert.equal(rollPercentage(MANA_REGEN, 16), 50);
  assert.equal(rollPercentage(SPELL_COST, -4), 100);
  assert.equal(rollPercentage([7], 7), undefined);
});

test('valueAt picks the closest value the item can roll', () => {
  assert.equal(valueAt(MANA_REGEN, 100), 26);
  assert.equal(valueAt(MANA_REGEN, 52), 16);
  assert.equal(valueAt(SPELL_COST, 0), -1);
  assert.equal(valueAt(SPELL_COST, 70), -3);
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
