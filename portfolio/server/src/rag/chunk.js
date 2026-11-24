// Step 1 of the RAG pipeline: turn markdown documents into small, searchable chunks.
//
// Each document is split at "## " headings (one section = one topic). Long sections
// are further split into ~MAX_CHARS pieces on sentence boundaries, with one sentence
// of overlap so an answer that straddles two chunks is not lost.

const MAX_CHARS = 600;

export function parseDocument(raw, fileName) {
  const meta = {};
  let body = raw;
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  if (m) {
    body = raw.slice(m[0].length);
    for (const line of m[1].split('\n')) {
      const kv = line.match(/^(\w+):\s*(.*)$/);
      if (kv) meta[kv[1]] = kv[2].replace(/^["']|["']$/g, '');
    }
  }
  return {
    file: fileName,
    title: meta.title || fileName.replace(/\.md$/, ''),
    anchor: meta.anchor || '',
    body,
  };
}

function splitSections(body) {
  const sections = [];
  let current = { heading: '', lines: [] };
  for (const line of body.split('\n')) {
    const h = line.match(/^##\s+(.*)$/);
    if (h) {
      if (current.lines.join('').trim()) sections.push(current);
      current = { heading: h[1].trim(), lines: [] };
    } else {
      current.lines.push(line);
    }
  }
  if (current.lines.join('').trim()) sections.push(current);
  return sections.map((s) => ({ heading: s.heading, text: s.lines.join(' ').replace(/\s+/g, ' ').trim() }));
}

function splitLong(text) {
  if (text.length <= MAX_CHARS) return [text];
  const sentences = text.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) || [text];
  const pieces = [];
  let buf = [];
  let len = 0;
  for (const s of sentences) {
    if (len + s.length > MAX_CHARS && buf.length) {
      pieces.push(buf.join('').trim());
      buf = [buf[buf.length - 1]]; // one-sentence overlap
      len = buf[0].length;
    }
    buf.push(s);
    len += s.length;
  }
  if (buf.length) pieces.push(buf.join('').trim());
  return pieces;
}

export function chunkDocument(doc) {
  const chunks = [];
  let n = 0;
  for (const section of splitSections(doc.body)) {
    for (const piece of splitLong(section.text)) {
      chunks.push({
        id: `${doc.file.replace(/\.md$/, '')}-${n++}`,
        docTitle: doc.title,
        heading: section.heading,
        anchor: doc.anchor,
        text: piece,
        // The title and heading are included in the embedded text so short chunks keep their context.
        embedText: `${doc.title} - ${section.heading}: ${piece}`,
      });
    }
  }
  return chunks;
}
