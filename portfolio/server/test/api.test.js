import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';

process.env.EMBED_PROVIDER = 'local';
process.env.GEMINI_API_KEY = '';
process.env.LLM_BASE_URL = '';
process.env.CONTACT_RATE_LIMIT = '1000';
process.env.SMTP_USER = 'sender@example.com';
process.env.SMTP_PASS = 'secret';
process.env.CONTACT_TO = 'owner@example.com';
process.env.MAIL_DRY_RUN = 'false';
process.env.CLIENT_ORIGIN = 'http://localhost:5173';

const { createApp } = await import('../src/index.js');
const { mailer, validateContact, escapeHtml } = await import('../src/routes/contact.js');

let server;
let base;
const sent = [];
const realSend = mailer.send;

before(async () => {
  mailer.send = async (msg) => { sent.push(msg); return { messageId: '<test@id>', accepted: [msg.to] }; };
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => { mailer.send = realSend; server.close(); });

const post = (path, body, headers = {}) =>
  fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });

const good = { name: 'Sara Khan', email: 'sara@example.com', subject: 'Internship', message: 'Hello Ali, we would like to talk about an internship.', website: '', elapsed: 9000 };

test('health check works', async () => {
  const r = await fetch(`${base}/api/health`);
  assert.equal(r.status, 200);
});

test('valid contact message is emailed to the owner with reply-to set to the visitor', async () => {
  sent.length = 0;
  const r = await post('/api/contact', good);
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].to, 'owner@example.com');
  assert.equal(sent[0].subject, '[Portfolio] Internship');
  assert.match(sent[0].replyTo, /sara@example\.com/);
  assert.match(sent[0].text, /internship/);
});

test('invalid input is rejected with per-field errors', async () => {
  sent.length = 0;
  const r = await post('/api/contact', { name: '', email: 'not-an-email', subject: '', message: 'short', elapsed: 9000 });
  assert.equal(r.status, 400);
  const body = await r.json();
  assert.deepEqual(Object.keys(body.fields).sort(), ['email', 'message', 'name', 'subject']);
  assert.equal(sent.length, 0);
});

test('over-long fields are rejected', () => {
  const { ok, fields } = validateContact({ ...good, name: 'x'.repeat(81), message: 'y'.repeat(2001) });
  assert.equal(ok, false);
  assert.ok(fields.name && fields.message);
});

test('line breaks in subject/name cannot inject email headers', async () => {
  sent.length = 0;
  const r = await post('/api/contact', { ...good, subject: 'Hi\r\nBcc: victim@example.com', name: 'Eve\nTo: x@y.z' });
  assert.equal(r.status, 200);
  assert.ok(!/[\r\n]/.test(sent[0].subject));
  assert.ok(!/[\r\n]/.test(sent[0].replyTo));
});

test('HTML in the message is escaped in the HTML email body', async () => {
  sent.length = 0;
  await post('/api/contact', { ...good, message: '<script>alert(1)</script> hello there friend' });
  assert.ok(!sent[0].html.includes('<script>'));
  assert.match(sent[0].html, /&lt;script&gt;/);
  assert.equal(escapeHtml(`<a href="x">'&`), '&lt;a href=&quot;x&quot;&gt;&#39;&amp;');
});

test('honeypot submissions look successful but send nothing', async () => {
  sent.length = 0;
  const r = await post('/api/contact', { ...good, website: 'http://spam.example' });
  assert.equal(r.status, 200);
  assert.equal(sent.length, 0);
});

test('instant submissions (bots) are silently dropped', async () => {
  sent.length = 0;
  const r = await post('/api/contact', { ...good, elapsed: 300 });
  assert.equal(r.status, 200);
  assert.equal(sent.length, 0);
});

test('SMTP failure returns a friendly 502 without leaking details', async () => {
  const original = mailer.send;
  mailer.send = async () => { throw new Error('connect ECONNREFUSED smtp.secret.host:465'); };
  const r = await post('/api/contact', good);
  mailer.send = original;
  assert.equal(r.status, 502);
  const text = JSON.stringify(await r.json());
  assert.ok(!text.includes('secret.host'));
});

test('malformed JSON and oversized bodies are rejected', async () => {
  const bad = await fetch(`${base}/api/contact`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{nope' });
  assert.equal(bad.status, 400);
  const big = await post('/api/contact', { ...good, message: 'z'.repeat(20000) });
  assert.equal(big.status, 413);
});

test('requests from the site\'s own origin are allowed (single-service deployment)', async () => {
  const r = await fetch(`${base}/api/health`, { headers: { Origin: base } });
  assert.equal(r.status, 200);
});

test('requests from other origins are refused', async () => {
  const r = await fetch(`${base}/api/health`, { headers: { Origin: 'https://evil.example' } });
  assert.equal(r.status, 403);
});

/* ---------------- chatbot route ---------------- */
test('chat answers from the knowledge base and cites sources (offline mode)', async () => {
  const r = await post('/api/chat', { message: 'Which projects use Three.js?' });
  assert.equal(r.status, 200);
  const body = await r.json();
  assert.match(body.answer, /Museum Heist|WebCraft|Neon Vault/);
  assert.ok(body.sources.length >= 1);
  assert.ok(body.sources[0].anchor.startsWith('#'));
});

test('chat refuses to invent answers for unrelated questions', async () => {
  const r = await post('/api/chat', { message: 'What is his favourite pizza topping?' });
  const body = await r.json();
  assert.match(body.answer, /don't have that information/);
  assert.deepEqual(body.sources, []);
});

test('chat validates its input', async () => {
  assert.equal((await post('/api/chat', { message: '' })).status, 400);
  assert.equal((await post('/api/chat', { message: 'x'.repeat(501) })).status, 400);
  assert.equal((await post('/api/chat', {})).status, 400);
});

test('with an LLM configured, the answer is generated from retrieved context only', async () => {
  process.env.GEMINI_API_KEY = 'test-key';
  const realFetch = globalThis.fetch;
  let seenBody;
  globalThis.fetch = async (url, opts) => {
    if (String(url).includes('generativelanguage')) {
      seenBody = JSON.parse(opts.body);
      return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: 'Ali built Museum Heist, WebCraft and Neon Vault with Three.js.' }] } }] }), { status: 200 });
    }
    return realFetch(url, opts);
  };
  try {
    const r = await post('/api/chat', { message: 'Which projects use Three.js?' });
    const body = await r.json();
    assert.match(body.answer, /Museum Heist, WebCraft and Neon Vault/);
    assert.match(seenBody.systemInstruction.parts[0].text, /CONTEXT:/);
    assert.match(seenBody.systemInstruction.parts[0].text, /WebCraft/);
    assert.equal(seenBody.contents[0].parts[0].text, 'Which projects use Three.js?');
    assert.ok(body.sources.length > 0);

    // Model says it cannot answer -> friendly refusal, no citations.
    const llm = (make) => async (url, opts) => (String(url).includes('generativelanguage') ? make() : realFetch(url, opts));
    globalThis.fetch = llm(() => new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: 'NO_INFO' }] } }] }), { status: 200 }));
    const r2 = await post('/api/chat', { message: 'Which projects use Three.js?' });
    const b2 = await r2.json();
    assert.match(b2.answer, /don't have that information/);
    assert.deepEqual(b2.sources, []);

    // Upstream failure -> 502 with a friendly message.
    globalThis.fetch = llm(() => new Response('boom', { status: 500 }));
    const r3 = await post('/api/chat', { message: 'Which projects use Three.js?' });
    assert.equal(r3.status, 502);
  } finally {
    globalThis.fetch = realFetch;
    process.env.GEMINI_API_KEY = '';
  }
});
