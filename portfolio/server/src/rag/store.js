// Step 3: the vector index.
// For a portfolio-sized corpus (a few dozen chunks) a JSON file plus an in-memory cosine search
// is a real vector index with none of the operational weight of a separate database.

import fs from 'node:fs/promises';
import path from 'node:path';
import { getConfig } from '../config.js';
import { parseDocument, chunkDocument } from './chunk.js';
import { embedDocuments } from './embeddings.js';

export async function buildIndex(provider) {
  const cfg = getConfig();
  const files = (await fs.readdir(cfg.knowledgeDir)).filter((f) => f.endsWith('.md')).sort();
  const chunks = [];
  for (const file of files) {
    const raw = await fs.readFile(path.join(cfg.knowledgeDir, file), 'utf8');
    chunks.push(...chunkDocument(parseDocument(raw, file)));
  }
  const { provider: used, dim, vectors } = await embedDocuments(chunks.map((c) => c.embedText), provider);
  return {
    builtAt: new Date().toISOString(),
    provider: used,
    dim,
    chunks: chunks.map((c, i) => ({ ...c, vector: vectors[i] })),
  };
}

export async function saveIndex(index) {
  const { indexPath } = getConfig();
  await fs.mkdir(path.dirname(indexPath), { recursive: true });
  await fs.writeFile(indexPath, JSON.stringify(index));
}

export async function loadIndex() {
  const { indexPath } = getConfig();
  try {
    return JSON.parse(await fs.readFile(indexPath, 'utf8'));
  } catch {
    return null;
  }
}

let cached = null;

/** Load the saved index, or build it if missing or built with a provider we can no longer use. */
export async function getIndex({ force = false } = {}) {
  if (cached && !force) return cached;
  const cfg = getConfig();
  let index = force ? null : await loadIndex();
  const unusable = index && index.provider === 'gemini' && !cfg.gemini.key;
  if (!index || unusable) {
    index = await buildIndex(cfg.embedProvider);
    if (!unusable) await saveIndex(index).catch(() => {});
  }
  cached = index;
  return index;
}

export function resetIndexCache() {
  cached = null;
}
