// Step 4: find the chunks most relevant to the user's question.

import { getConfig } from '../config.js';
import { cosine, embedQuery } from './embeddings.js';
import { getIndex } from './store.js';

// Chunks scoring below this are treated as "not about this", so the bot admits it does not know
// instead of answering from loosely related text.
const DEFAULT_MIN_SCORE = { gemini: 0.5, local: 0.16 };

export async function retrieve(question, { k = 4 } = {}) {
  const cfg = getConfig();
  const index = await getIndex();
  const qv = await embedQuery(question, index.provider);
  const minScore = cfg.minScore ?? DEFAULT_MIN_SCORE[index.provider] ?? 0.3;

  const scored = index.chunks
    .map((c) => ({ chunk: c, score: cosine(qv, c.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);

  return { hits: scored.filter((s) => s.score >= minScore), best: scored[0]?.score ?? 0, minScore, provider: index.provider };
}

/** Unique, human-readable citations for the UI. */
export function toSources(hits) {
  const seen = new Set();
  const sources = [];
  for (const { chunk } of hits) {
    const key = `${chunk.docTitle}|${chunk.heading}`;
    if (seen.has(key)) continue;
    seen.add(key);
    sources.push({ id: chunk.id, title: chunk.heading ? `${chunk.docTitle}: ${chunk.heading}` : chunk.docTitle, anchor: chunk.anchor });
  }
  return sources;
}
