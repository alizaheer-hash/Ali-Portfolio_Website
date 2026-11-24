import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { retrieve, toSources } from '../rag/retrieve.js';
import { generateAnswer, NO_INFO_TEXT } from '../rag/llm.js';

const router = Router();

router.use(
  rateLimit({
    windowMs: 5 * 60 * 1000,
    limit: 25,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'You are asking a lot of questions. Please wait a few minutes and try again.' },
  })
);

router.post('/', async (req, res) => {
  const message = typeof req.body?.message === 'string' ? req.body.message.replace(/\s+/g, ' ').trim() : '';
  if (!message) return res.status(400).json({ error: 'Please type a question.' });
  if (message.length > 500) return res.status(400).json({ error: 'Please keep your question under 500 characters.' });

  try {
    const { hits } = await retrieve(message);
    // Nothing relevant found: say so without calling the LLM at all.
    if (hits.length === 0) return res.json({ answer: NO_INFO_TEXT, sources: [], grounded: false });

    const { answer, grounded } = await generateAnswer(message, hits);
    res.json({ answer, sources: grounded ? toSources(hits) : [], grounded });
  } catch (err) {
    console.error('[chat]', err.message);
    res.status(502).json({ error: 'The assistant is having trouble right now. Please try again in a moment, or use the contact form.' });
  }
});

export default router;
