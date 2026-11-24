import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import fs from 'node:fs';
import path from 'node:path';
import { getConfig } from './config.js';
import chatRoute from './routes/chat.js';
import contactRoute from './routes/contact.js';
import { getIndex } from './rag/store.js';

export function createApp() {
  const cfg = getConfig();
  const app = express();

  app.set('trust proxy', 1); // so rate limits see the real visitor IP behind Render/Vercel proxies
  app.disable('x-powered-by');

  app.use(
    helmet({
      // The built site loads fonts from Google and plays local media.
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", "'wasm-unsafe-eval'"],
          styleSrc: ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
          fontSrc: ["'self'", 'https://fonts.gstatic.com'],
          imgSrc: ["'self'", 'data:', 'blob:'],
          mediaSrc: ["'self'", 'blob:'],
          connectSrc: ["'self'", 'https://www.gstatic.com'],
          workerSrc: ["'self'", 'blob:'],
        },
      },
      crossOriginResourcePolicy: { policy: 'cross-origin' },
    })
  );
  // Allow: no Origin header (curl, server-to-server), the site's own origin (when this server also
  // hosts the built frontend), and the origins listed in CLIENT_ORIGIN.
  app.use((req, res, next) =>
    cors({
      origin(origin, cb) {
        if (!origin || cfg.clientOrigins.includes(origin)) return cb(null, true);
        try {
          if (new URL(origin).host === req.headers.host) return cb(null, true);
        } catch {
          /* malformed Origin: fall through to rejection */
        }
        cb(new Error('Origin not allowed'));
      },
      methods: ['GET', 'POST'],
    })(req, res, next)
  );
  app.use(express.json({ limit: '10kb' }));

  app.get('/api/health', (_req, res) => res.json({ ok: true }));
  app.use('/api/chat', chatRoute);
  app.use('/api/contact', contactRoute);
  app.use('/api', (_req, res) => res.status(404).json({ error: 'Not found' }));

  // If the frontend has been built, serve it too: one service can host the whole site.
  if (fs.existsSync(path.join(cfg.clientDist, 'index.html'))) {
    app.use(express.static(cfg.clientDist, { maxAge: '1h' }));
    app.get('*', (_req, res) => res.sendFile(path.join(cfg.clientDist, 'index.html')));
  }

  // Error handler: never leak stack traces.
  // eslint-disable-next-line no-unused-vars
  app.use((err, _req, res, _next) => {
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'Invalid request.' });
    if (err.type === 'entity.too.large') return res.status(413).json({ error: 'Request too large.' });
    if (err.message === 'Origin not allowed') return res.status(403).json({ error: 'Origin not allowed.' });
    console.error(err);
    res.status(500).json({ error: 'Something went wrong.' });
  });

  return app;
}

// Vercel (and other serverless hosts) import this file and use the default export as the handler.
export default createApp();

// Start the server unless this file is imported by tests.
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const cfg = getConfig();
  const app = createApp();
  getIndex()
    .then((idx) => console.log(`[rag] index ready: ${idx.chunks.length} chunks, provider "${idx.provider}"`))
    .catch((e) => console.error('[rag] could not prepare index:', e.message));
  app.listen(cfg.port, () => console.log(`API listening on http://localhost:${cfg.port}`));
}
