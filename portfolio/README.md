# Ali Mohammad Zaheer: Interactive 3D Portfolio

A responsive portfolio with a mouse-reactive 3D avatar, light and dark themes, a RAG-based AI chatbot and a working contact form.

- **Frontend** (`client/`): React, Vite, Three.js via react-three-fiber
- **Backend** (`server/`): Node.js, Express, Nodemailer
- **Chatbot**: Retrieval-Augmented Generation over the CV and project notes (Google Gemini, with an offline fallback)

## Quick start

Requires Node.js 18 or newer.

```bash
# 1. Backend
cd server
npm install
cp .env.example .env        # then fill in the values (see "Environment variables")
npm run ingest              # builds the vector index from server/knowledge/*.md
npm start                   # http://localhost:5000

# 2. Frontend (new terminal)
cd client
npm install
npm run dev                 # http://localhost:5173  (proxies /api to the backend)
```

The site works without any keys: the chatbot falls back to an offline mode and the contact form returns "not available" until SMTP is configured. Set `MAIL_DRY_RUN=true` to test the form without sending.

## Environment variables (`server/.env`)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Free key from https://aistudio.google.com/apikey. Used for embeddings and answers. |
| `EMBED_PROVIDER` | `gemini` (semantic) or `local` (offline hashing embedder, no key). |
| `GEMINI_MODEL` | Answer model, default `gemini-2.5-flash`. |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Optional: use any OpenAI-compatible LLM instead (Groq, OpenAI, OpenRouter). |
| `MIN_SCORE` | Minimum similarity for a chunk to count as relevant (provider defaults apply when empty). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | Outgoing mail. For Gmail, create an **App Password** (needs 2-Step Verification) and paste it as `SMTP_PASS`. |
| `CONTACT_TO` | The address that receives visitor messages. |
| `MAIL_DRY_RUN` | `true` logs the message instead of sending it. |
| `CLIENT_ORIGIN` | Allowed website origin(s) for CORS, comma separated. |

Secrets live only in `server/.env`, which is git-ignored. They are never sent to the browser.

## Project structure

```
client/
  public/models/avatar.glb   <- the avatar (rigged businessman with animation clips)
  blender/businessman/       build_businessman.py + helpers that add the Greet/Bow/Ponder clips
  blender/                   older low-poly avatar sources (no longer used)
  public/media/promo.mp4     <- put your After Effects export here
  src/App.jsx                page sections, theme toggle
  src/components/Hero3D.jsx  3D scene (avatar + mouse-reactive shapes)
  src/components/Projects.jsx   project gallery with filter and search
  src/components/ChatPanel.jsx  chatbot UI (citations, voice input)
  src/components/ContactForm.jsx   validated contact form
  src/data.js                all portfolio content (edit this)
server/
  knowledge/*.md             the documents the chatbot knows
  src/rag/                   chunk, embeddings, store, retrieve, llm, ingest
  src/routes/chat.js         POST /api/chat
  src/routes/contact.js      POST /api/contact
  test/                      31 automated tests
```

## How the 3D hero works

`Hero3D.jsx` renders a Three.js scene. A single pointer position is shared by every object:

- the avatar's head and body turn toward the cursor, it idles gently, and each click plays the next reaction (greet, nod, bow, look around, ponder)
- four floating shapes move with the cursor at different depths (parallax), spin faster on hover, and burst-spin on click
- a point light follows the cursor
- the scene colours change with the theme
- with `prefers-reduced-motion` the scene renders once and stays still; if WebGL is unavailable a static illustration is shown

**Avatar:** `client/public/models/avatar.glb` is a rigged, textured businessman model with `Idle` (loops), `Walk`, `Nod` and `LookAround` clips from the source file, plus `Greet`, `Bow` and `Ponder` added by `blender/businessman/build_businessman.py` (run it with `blender -b --python build_businessman.py -- out.glb`). The model's hands are clasped and skinned together, so the new clips move both arms symmetrically and the script re-skins the hands first. If the GLB is missing, the site falls back to a procedural placeholder.

## How the chatbot (RAG pipeline) works

```
 knowledge/*.md ──► 1. Chunk ──► 2. Embed ──► 3. Vector index (data/index.json)
                                                        │
 visitor question ──► embed question ──► 4. Retrieve top matches (cosine similarity)
                                                        │
                       5. LLM answers using ONLY the retrieved text ──► answer + citations
```

1. **Chunk** (`rag/chunk.js`): each markdown file is split at `##` headings; long sections are split into pieces of about 600 characters on sentence boundaries with a one-sentence overlap. Each chunk keeps its document title, heading and page anchor.
2. **Embed** (`rag/embeddings.js`): each chunk becomes a 768-dimension vector with Gemini `gemini-embedding-001`. Without a key, an offline hashing embedder is used so everything still runs.
3. **Index** (`rag/store.js`): vectors are saved to `server/data/index.json` and searched in memory. This is a real vector index sized for a few dozen chunks.
4. **Retrieve** (`rag/retrieve.js`): the question is embedded the same way and compared with every chunk by cosine similarity. The top 4 are kept, but only those above a minimum score.
5. **Generate** (`rag/llm.js`): the retrieved chunks are placed in the prompt as `CONTEXT`. The model is told to use only that text and to reply `NO_INFO` otherwise.

**Avoiding invented answers** works in three layers: (a) if no chunk is similar enough, the LLM is never called and the bot says it does not have that information; (b) the prompt forbids facts outside the context and the bot must reply `NO_INFO` when unsure; (c) citations are shown only for answers that were grounded. Visitor text is treated as a question, not as instructions.

**To update what the chatbot knows:** edit the files in `server/knowledge/`, then run `npm run ingest`.

## Contact form and security

- Validation in the browser (`ContactForm.jsx`) and again on the server (`routes/contact.js`): name, email, subject (required) and message (10-2000 characters)
- Spam protection: hidden honeypot field, an "instant submission" time check, and a rate limit of 5 messages per hour per visitor (chat: 25 per 5 minutes)
- Input handling: control characters and line breaks are stripped from header fields (blocks email header injection), the HTML email escapes all user text, request bodies are capped at 10 kB
- `helmet` security headers and a strict CORS allow-list; error responses never reveal internal details
- Delivery evidence: every successful send logs the SMTP `messageId` on the server, and the message arrives in the `CONTACT_TO` inbox with the visitor as `Reply-To`

## Tests

```bash
cd server && npm test
```

31 tests cover chunking, embeddings, retrieval of relevant and irrelevant questions, the prompt, the chat route (with a mocked LLM), contact validation, header injection, HTML escaping, spam traps, SMTP failure handling, CORS and rate limiting.

## Deployment

The simplest route is **one Render web service** that serves both the API and the built site:

1. Push the repository to GitHub.
2. On https://render.com create a **Web Service** from the repo. Build command: `cd client && npm install && npm run build && cd ../server && npm install`. Start command: `cd server && npm start`.
3. Add the environment variables from the table above in Render's dashboard (set `CLIENT_ORIGIN` to your Render URL).
4. Open the Render URL. The server serves `client/dist` automatically.

Alternative: frontend on Vercel or Netlify (set `VITE_API_URL` to your backend URL) and the backend on Render (set `CLIENT_ORIGIN` to the frontend URL).

## Submission checklist

- [ ] `client/public/models/avatar.glb` added, plus the `.blend` file kept for submission
- [ ] `client/public/media/promo.mp4` added, plus the `.aep` file
- [ ] Project links and screenshots filled in `client/src/data.js`
- [ ] SMTP and Gemini values set; send a test message and keep a screenshot of it arriving
- [ ] Deployed URL working; GitHub repository link ready
- [ ] Project report (PDF)

## AI assistance

This portfolio's code was developed with the help of Claude (Anthropic). The CV content and project descriptions are the author's own.
