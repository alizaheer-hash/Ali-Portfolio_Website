import 'dotenv/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const embedProvider = (process.env.EMBED_PROVIDER || 'gemini').toLowerCase();

// Read lazily so tests can change process.env before calling.
export function getConfig() {
  const provider = (process.env.EMBED_PROVIDER || embedProvider).toLowerCase();
  const geminiKey = process.env.GEMINI_API_KEY || '';
  return {
    root,
    port: Number(process.env.PORT) || 5000,
    clientOrigins: (process.env.CLIENT_ORIGIN || 'http://localhost:5173').split(',').map((s) => s.trim()).filter(Boolean),
    knowledgeDir: path.join(root, 'knowledge'),
    indexPath: path.join(root, 'data', 'index.json'),
    clientDist: path.resolve(root, '..', 'client', 'dist'),
    gemini: {
      key: geminiKey,
      model: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
      embedModel: process.env.GEMINI_EMBED_MODEL || 'gemini-embedding-001',
    },
    openaiCompat: {
      baseUrl: (process.env.LLM_BASE_URL || '').replace(/\/$/, ''),
      key: process.env.LLM_API_KEY || '',
      model: process.env.LLM_MODEL || '',
    },
    // "gemini" needs a key; without one we quietly use the offline embedder.
    embedProvider: provider === 'gemini' && !geminiKey ? 'local' : provider,
    minScore: process.env.MIN_SCORE ? Number(process.env.MIN_SCORE) : null,
    mail: {
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: Number(process.env.SMTP_PORT) || 465,
      user: process.env.SMTP_USER || '',
      pass: process.env.SMTP_PASS || '',
      to: process.env.CONTACT_TO || '',
      dryRun: String(process.env.MAIL_DRY_RUN).toLowerCase() === 'true',
    },
  };
}
