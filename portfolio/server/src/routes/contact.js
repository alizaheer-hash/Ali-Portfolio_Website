import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import nodemailer from 'nodemailer';
import { getConfig } from '../config.js';

const router = Router();

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const LIMITS = { name: 80, email: 254, subject: 120, message: 2000 };

/** Remove control characters and line breaks (prevents email header injection). */
const oneLine = (s) => String(s ?? '').replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
/** Keep line breaks in the message body but drop other control characters. */
const multiLine = (s) => String(s ?? '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').replace(/\r\n?/g, '\n').trim();
export const escapeHtml = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

export function validateContact(body = {}) {
  const v = {
    name: oneLine(body.name),
    email: oneLine(body.email),
    subject: oneLine(body.subject),
    message: multiLine(body.message),
  };
  const fields = {};
  if (!v.name) fields.name = 'Please enter your name.';
  else if (v.name.length > LIMITS.name) fields.name = `Name must be ${LIMITS.name} characters or fewer.`;
  if (!v.email) fields.email = 'Please enter your email address.';
  else if (v.email.length > LIMITS.email || !EMAIL_RE.test(v.email)) fields.email = 'That email address does not look right.';
  if (!v.subject) fields.subject = 'Please add a subject.';
  else if (v.subject.length > LIMITS.subject) fields.subject = `Subject must be ${LIMITS.subject} characters or fewer.`;
  if (v.message.length < 10) fields.message = 'Please write at least 10 characters.';
  else if (v.message.length > LIMITS.message) fields.message = `Message must be ${LIMITS.message} characters or fewer.`;
  return { values: v, fields, ok: Object.keys(fields).length === 0 };
}

let transport = null;
function getTransport() {
  const { mail } = getConfig();
  if (!transport) {
    transport = nodemailer.createTransport({
      host: mail.host,
      port: mail.port,
      secure: mail.port === 465,
      auth: { user: mail.user, pass: mail.pass },
    });
  }
  return transport;
}
export function resetTransport() { transport = null; }

/** Replaceable in tests. */
export const mailer = {
  async send(message) {
    return getTransport().sendMail(message);
  },
};

router.use(
  rateLimit({
    windowMs: 60 * 60 * 1000,
    limit: Number(process.env.CONTACT_RATE_LIMIT) || 5,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'You have sent several messages already. Please try again later.' },
  })
);

router.post('/', async (req, res) => {
  const body = req.body || {};

  // Spam protection 1: honeypot. Real visitors never fill the hidden field.
  // Spam protection 2: a form submitted in under 2.5 seconds was not filled in by a person.
  // In both cases we reply "ok" so bots learn nothing, but we send nothing.
  const elapsed = Number(body.elapsed);
  if (body.website || (Number.isFinite(elapsed) && elapsed < 2500)) {
    console.warn('[contact] blocked as probable spam');
    return res.json({ ok: true });
  }

  const { values, fields, ok } = validateContact(body);
  if (!ok) return res.status(400).json({ error: 'Please check the highlighted fields.', fields });

  const { mail } = getConfig();
  const text = `From: ${values.name} <${values.email}>\nSubject: ${values.subject}\n\n${values.message}\n`;
  const html =
    `<p><strong>From:</strong> ${escapeHtml(values.name)} &lt;${escapeHtml(values.email)}&gt;</p>` +
    `<p><strong>Subject:</strong> ${escapeHtml(values.subject)}</p>` +
    `<hr><p style="white-space:pre-wrap">${escapeHtml(values.message)}</p>`;

  if (mail.dryRun) {
    console.log('[contact] DRY RUN, not sending:\n' + text);
    return res.json({ ok: true, dryRun: true });
  }
  if (!mail.user || !mail.pass || !mail.to) {
    console.error('[contact] SMTP_USER, SMTP_PASS or CONTACT_TO is not set');
    return res.status(503).json({ error: 'The contact form is not available right now. Please try again later.' });
  }

  try {
    const info = await mailer.send({
      from: `"Portfolio contact form" <${mail.user}>`,
      to: mail.to,
      replyTo: `"${values.name.replace(/"/g, '')}" <${values.email}>`,
      subject: `[Portfolio] ${values.subject}`,
      text,
      html,
    });
    // This log line is the evidence of successful delivery: the SMTP server's message id.
    console.log(`[contact] sent messageId=${info.messageId} accepted=${JSON.stringify(info.accepted)} at ${new Date().toISOString()}`);
    res.json({ ok: true });
  } catch (err) {
    console.error('[contact] send failed:', err.message);
    res.status(502).json({ error: 'Your message could not be delivered. Please try again later.' });
  }
});

export default router;
