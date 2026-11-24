// Step 2: turn text into vectors (embeddings).
//
// Two providers share one interface:
//   gemini - Google's gemini-embedding-001 (semantic, needs GEMINI_API_KEY, free tier available)
//   local  - an offline hashing embedder (no key, keyword-flavoured). It exists so the whole
//            pipeline runs and can be tested without any account.

import { getConfig } from '../config.js';

const GEMINI_DIM = 768;
const LOCAL_DIM = 512;

const STOP = new Set(('a an and are as at be by for from has have he his how i in is it its of on or that the their this to was ' +
  'what which who with you your about tell me can do does did ali s').split(' '));

export function normalize(vec) {
  let sum = 0;
  for (const v of vec) sum += v * v;
  const norm = Math.sqrt(sum) || 1;
  return vec.map((v) => v / norm);
}

export function cosine(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot; // vectors are unit length
}

/* ---------- local hashing embedder ---------- */
function fnv(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Very light stemming plus a small domain vocabulary. Words in the same group also emit a shared
// "concept" token, so "study", "university" and "degree" land near each other even without a neural model.
const CONCEPTS = {
  educ: ['study', 'studi', 'univers', 'colleg', 'school', 'degree', 'bs', 'cgpa', 'educ', 'graduat', 'matric', 'intermed', 'learn', 'student'],
  skill: ['skill', 'know', 'proficien', 'expert', 'strong', 'technolog', 'tool', 'language', 'abilit', 'good', 'level'],
  career: ['role', 'job', 'career', 'seek', 'look', 'object', 'hire', 'position', 'work', 'want'],
  cert: ['certif', 'certificate', 'course', 'workshop', 'coursera', 'credential'],
  project: ['project', 'built', 'build', 'made', 'portfolio', 'develop', 'creat'],
};

function stem(w) {
  if (w.length > 4 && w.endsWith('ies')) return `${w.slice(0, -3)}y`;
  if (w.length > 5 && w.endsWith('ing')) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith('ed')) return w.slice(0, -2);
  if (w.length > 3 && w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
  return w;
}

export function tokenize(text) {
  const base = text
    .toLowerCase()
    .replace(/c\+\+/g, 'cpp')
    .replace(/c#/g, 'csharp')
    .replace(/three\.js/g, 'threejs')
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w && !STOP.has(w))
    .map(stem);
  const out = [...base];
  for (const w of base) {
    for (const [concept, roots] of Object.entries(CONCEPTS)) {
      if (roots.some((r) => w.startsWith(r) && (r.length > 3 || w === r))) out.push(`~${concept}`);
    }
  }
  return out;
}

function localEmbed(text) {
  const vec = new Array(LOCAL_DIM).fill(0);
  const tokens = tokenize(text);
  const feats = [...tokens];
  for (let i = 0; i < tokens.length - 1; i++) feats.push(`${tokens[i]}_${tokens[i + 1]}`);
  const counts = new Map();
  for (const f of feats) counts.set(f, (counts.get(f) || 0) + 1);
  for (const [f, c] of counts) {
    const h = fnv(f);
    const sign = h & 1 ? 1 : -1;
    vec[(h >>> 1) % LOCAL_DIM] += sign * (1 + Math.log(c));
  }
  return normalize(vec);
}

/* ---------- Gemini ---------- */
async function geminiEmbedBatch(texts, taskType) {
  const { gemini } = getConfig();
  const model = `models/${gemini.embedModel}`;
  const out = [];
  for (let i = 0; i < texts.length; i += 50) {
    const batch = texts.slice(i, i + 50);
    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/${model}:batchEmbedContents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': gemini.key },
      body: JSON.stringify({
        requests: batch.map((t) => ({
          model,
          content: { parts: [{ text: t }] },
          taskType,
          outputDimensionality: GEMINI_DIM,
        })),
      }),
    });
    if (!res.ok) throw new Error(`Gemini embeddings failed (${res.status}): ${(await res.text()).slice(0, 200)}`);
    const data = await res.json();
    // Truncated dimensions are not unit length, so re-normalise.
    for (const e of data.embeddings) out.push(normalize(e.values));
  }
  return out;
}

/** Embed document chunks. Returns { provider, dim, vectors }. */
export async function embedDocuments(texts, provider = getConfig().embedProvider) {
  if (provider === 'gemini') {
    const vectors = await geminiEmbedBatch(texts, 'RETRIEVAL_DOCUMENT');
    return { provider, dim: GEMINI_DIM, vectors };
  }
  return { provider: 'local', dim: LOCAL_DIM, vectors: texts.map(localEmbed) };
}

/** Embed one user question with the same provider that built the index. */
export async function embedQuery(text, provider) {
  if (provider === 'gemini') {
    const [v] = await geminiEmbedBatch([text], 'RETRIEVAL_QUERY');
    return v;
  }
  return localEmbed(text);
}
