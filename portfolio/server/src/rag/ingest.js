// Run with: npm run ingest
// Reads knowledge/*.md, chunks it, embeds every chunk and writes data/index.json.

import { getConfig } from '../config.js';
import { buildIndex, saveIndex } from './store.js';

const cfg = getConfig();
console.log(`Embedding provider: ${cfg.embedProvider}`);
const index = await buildIndex(cfg.embedProvider);
await saveIndex(index);
console.log(`Indexed ${index.chunks.length} chunks (${index.dim} dimensions, provider "${index.provider}").`);
for (const c of index.chunks) console.log(`  ${c.id.padEnd(22)} ${c.docTitle} / ${c.heading} (${c.text.length} chars)`);
