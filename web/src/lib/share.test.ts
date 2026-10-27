import assert from 'node:assert/strict';
import { test } from 'node:test';
import { decodeShare, encodeShare } from './share.ts';

test('a share fragment carries the data and back', async () => {
  const data = {
    item: { name: 'Spring ✦', tier: 'mythic' },
    options: { scale: 4 },
    preset: 'spring',
  };
  const hash = await encodeShare(data);
  assert.match(hash, /^#card=[A-Za-z0-9_-]+$/);
  assert.deepEqual(await decodeShare(hash), data);
});

test('anything else is not a card', async () => {
  assert.equal(await decodeShare(''), undefined);
  assert.equal(await decodeShare('#about'), undefined);
  assert.equal(await decodeShare('#card=not-deflate'), undefined);
});
