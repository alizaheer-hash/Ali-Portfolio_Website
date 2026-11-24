import React, { useRef, useState } from 'react';
import { API_URL } from '../theme.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const LIMITS = { name: 80, subject: 120, message: 2000 };

function validate(v) {
  const e = {};
  if (!v.name.trim()) e.name = 'Please enter your name.';
  else if (v.name.length > LIMITS.name) e.name = `Name must be ${LIMITS.name} characters or fewer.`;
  if (!v.email.trim()) e.email = 'Please enter your email address.';
  else if (!EMAIL_RE.test(v.email.trim())) e.email = 'That email address does not look right.';
  if (!v.subject.trim()) e.subject = 'Please add a subject.';
  else if (v.subject.length > LIMITS.subject) e.subject = `Subject must be ${LIMITS.subject} characters or fewer.`;
  if (v.message.trim().length < 10) e.message = 'Please write at least 10 characters.';
  else if (v.message.length > LIMITS.message) e.message = `Message must be ${LIMITS.message} characters or fewer.`;
  return e;
}

export default function ContactForm() {
  const [values, setValues] = useState({ name: '', email: '', subject: '', message: '', website: '' });
  const [errors, setErrors] = useState({});
  const [status, setStatus] = useState({ type: 'idle', text: '' });
  const startedAt = useRef(Date.now());

  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length) {
      setStatus({ type: 'error', text: 'Please fix the highlighted fields.' });
      return;
    }
    setStatus({ type: 'sending', text: 'Sending…' });
    try {
      const res = await fetch(`${API_URL}/api/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // `website` is a hidden honeypot field; `elapsed` helps the server spot instant bot posts.
        body: JSON.stringify({ ...values, elapsed: Date.now() - startedAt.current }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (data.fields) setErrors(data.fields);
        throw new Error(data.error || 'Could not send your message. Please try again.');
      }
      setStatus({ type: 'success', text: 'Thank you! Your message has been sent.' });
      setValues({ name: '', email: '', subject: '', message: '', website: '' });
      startedAt.current = Date.now();
    } catch (err) {
      setStatus({ type: 'error', text: err.message || 'Network error. Please try again.' });
    }
  }

  const field = (id, label, props = {}) => (
    <div className="field">
      <label htmlFor={`c-${id}`}>{label}</label>
      {props.as === 'textarea' ? (
        <textarea id={`c-${id}`} rows={5} value={values[id]} onChange={set(id)} maxLength={LIMITS[id]}
          aria-invalid={!!errors[id]} aria-describedby={errors[id] ? `c-${id}-err` : undefined} />
      ) : (
        <input id={`c-${id}`} type={props.type || 'text'} value={values[id]} onChange={set(id)} maxLength={LIMITS[id]}
          autoComplete={props.autoComplete} aria-invalid={!!errors[id]} aria-describedby={errors[id] ? `c-${id}-err` : undefined} />
      )}
      {errors[id] && <span id={`c-${id}-err`} className="field__error">{errors[id]}</span>}
    </div>
  );

  return (
    <form className="contact-form" onSubmit={onSubmit} noValidate>
      {field('name', 'Name', { autoComplete: 'name' })}
      {field('email', 'Email', { type: 'email', autoComplete: 'email' })}
      {field('subject', 'Subject')}
      {field('message', 'Message', { as: 'textarea' })}
      {/* Honeypot: invisible to people, tempting to bots. */}
      <div className="hp" aria-hidden="true">
        <label htmlFor="c-website">Leave this field empty</label>
        <input id="c-website" tabIndex={-1} autoComplete="off" value={values.website} onChange={set('website')} />
      </div>
      <button className="btn btn--solid" type="submit" disabled={status.type === 'sending'}>
        {status.type === 'sending' ? 'Sending…' : 'Send message'}
      </button>
      <p className={`form-status form-status--${status.type}`} role="status" aria-live="polite">{status.text}</p>
    </form>
  );
}
