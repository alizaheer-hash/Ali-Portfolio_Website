import { test } from 'node:test';
import assert from 'node:assert/strict';

process.env.EMBED_PROVIDER = 'local';
process.env.GEMINI_API_KEY = '';
process.env.LLM_BASE_URL = '';

const { parseDocument, chunkDocument } = await import('../src/rag/chunk.js');
const { getIndex } = await import('../src/rag/store.js');
const { retrieve } = await import('../src/rag/retrieve.js');
const { cosine, embedQuery } = await import('../src/rag/embeddings.js');
const { buildPrompt } = await import('../src/rag/llm.js');

test('chunker splits on headings and keeps metadata', () => {
  const doc = parseDocument('---\ntitle: T\nanchor: "#x"\n---\n\n## One\nHello world.\n\n## Two\nGoodbye.', 'a.md');
  const chunks = chunkDocument(doc);
  assert.equal(chunks.length, 2);
  assert.equal(chunks[0].heading, 'One');
  assert.equal(chunks[0].anchor, '#x');
  assert.match(chunks[1].embedText, /^T - Two: Goodbye/);
});

test('long sections are split with overlap and stay under the size limit', () => {
  const sentence = 'This is a fairly ordinary sentence about nothing in particular. ';
  const doc = parseDocument(`## Long\n${sentence.repeat(30)}`, 'b.md');
  const chunks = chunkDocument(doc);
  assert.ok(chunks.length > 1);
  assert.ok(chunks.every((c) => c.text.length <= 800));
});

test('embeddings are unit length and similar text scores higher than unrelated text', async () => {
  const a = await embedQuery('Three.js games', 'local');
  const b = await embedQuery('games built with Three.js', 'local');
  const c = await embedQuery('banana bread recipe', 'local');
  assert.ok(Math.abs(cosine(a, a) - 1) < 1e-9);
  assert.ok(cosine(a, b) > cosine(a, c));
});

test('the index covers every knowledge file', async () => {
  const index = await getIndex({ force: true });
  assert.ok(index.chunks.length >= 10);
  assert.equal(index.provider, 'local');
  const titles = new Set(index.chunks.map((c) => c.docTitle));
  for (const t of ['About Ali', 'Skills and technologies', 'Projects', 'Education and certifications']) assert.ok(titles.has(t), t);
});

const cases = [
  ['Which projects use Three.js?', /Three\.js|Museum|WebCraft|Neon/],
  ['Tell me about the guard AI in Museum Heist', /guard/i],
  ['What is the hospital management system built with?', /PHP/],
  ['Where does Ali study?', /NED University/],
  ['Does he know C++?', /C\+\+|C and C/],
  ['What certificate does he have from Google?', /Google AI Professional Certificate/],
];
for (const [q, expected] of cases) {
  test(`retrieves relevant context for: ${q}`, async () => {
    const { hits } = await retrieve(q);
    assert.ok(hits.length > 0, 'no hits');
    assert.match(hits.map((h) => h.chunk.text).join(' '), expected);
  });
}

const unanswerable = [
  'What is his favourite pizza topping?',
  'How much salary does he earn?',
  'Who won the world cup in 2018?',
  'What is the capital of France?',
];
for (const q of unanswerable) {
  test(`returns nothing for an unrelated question: ${q}`, async () => {
    const { hits } = await retrieve(q);
    assert.equal(hits.length, 0, `unexpected hits: ${hits.map((h) => h.chunk.id + ':' + h.score.toFixed(2))}`);
  });
}

test('prompt tells the model to use only the context and to answer NO_INFO otherwise', async () => {
  const { hits } = await retrieve('Which projects use Three.js?');
  const { system, user } = buildPrompt('Which projects use Three.js?', hits);
  assert.match(system, /ONLY the facts in the CONTEXT/);
  assert.match(system, /NO_INFO/);
  assert.match(system, /\[1\]/);
  assert.equal(user, 'Which projects use Three.js?');
});
