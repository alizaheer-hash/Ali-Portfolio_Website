import { test } from 'node:test';
import assert from 'node:assert/strict';

process.env.EMBED_PROVIDER = 'local';
process.env.MAIL_DRY_RUN = 'true';
delete process.env.CONTACT_RATE_LIMIT;

const { createApp } = await import('../src/index.js');

test('the contact endpoint is rate limited after 5 requests per hour per visitor', async () => {
  const server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  const url = `http://127.0.0.1:${server.address().port}/api/contact`;
  const body = JSON.stringify({ name: 'A B', email: 'a@b.co', subject: 'Hello', message: 'A message that is long enough.', elapsed: 9000 });
  const statuses = [];
  for (let i = 0; i < 7; i++) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
    statuses.push(r.status);
  }
  server.close();
  assert.deepEqual(statuses, [200, 200, 200, 200, 200, 429, 429]);
});
