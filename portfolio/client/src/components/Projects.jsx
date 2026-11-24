import React, { useMemo, useState } from 'react';
import { projects } from '../data.js';

const allTags = ['All', ...Array.from(new Set(projects.flatMap((p) => [...p.tags])))];

function initials(title) {
  return title.split(/[\s:]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
}

export default function Projects() {
  const [tag, setTag] = useState('All');
  const [query, setQuery] = useState('');

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects.filter((p) => {
      const byTag = tag === 'All' || p.tags.includes(tag);
      const hay = [p.title, p.description, ...p.tech, ...p.tags].join(' ').toLowerCase();
      return byTag && (!q || hay.includes(q));
    });
  }, [tag, query]);

  return (
    <section id="projects" className="section" aria-labelledby="projects-h">
      <div className="section__head reveal">
        <h2 id="projects-h">Selected work</h2>
        <div className="filters">
          <div className="chips" role="group" aria-label="Filter projects by category">
            {allTags.map((t) => (
              <button key={t} className={`chip ${tag === t ? 'chip--on' : ''}`} aria-pressed={tag === t} onClick={() => setTag(t)}>{t}</button>
            ))}
          </div>
          <label className="search">
            <span className="sr-only">Search projects</span>
            <input type="search" placeholder="Search: three.js, php…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
        </div>
      </div>

      <div className="projects" aria-live="polite">
        {shown.map((p, i) => (
          <article key={p.id} className="project reveal" style={{ '--d': `${i * 70}ms` }}>
            <div className="project__no">{String(projects.indexOf(p) + 1).padStart(2, '0')}</div>
            <div className="project__thumb" aria-hidden={!p.image}>
              {p.image ? <img src={p.image} alt={`${p.title} screenshot`} loading="lazy" /> : <span>{initials(p.title)}</span>}
            </div>
            <div className="project__body">
              <h3>{p.title}</h3>
              <p>{p.description}</p>
              <ul className="tech" aria-label="Technologies">
                {p.tech.map((t) => <li key={t}>{t}</li>)}
              </ul>
              {p.note && <p className="project__note">{p.note}</p>}
              <div className="project__links">
                {p.demo && <a className="btn btn--ghost" href={p.demo} target="_blank" rel="noreferrer">Live demo</a>}
                {p.repo && <a className="btn btn--ghost" href={p.repo} target="_blank" rel="noreferrer">Source code</a>}
              </div>
            </div>
          </article>
        ))}
        {shown.length === 0 && <p className="empty">No projects match “{query}”. Try another word.</p>}
      </div>
    </section>
  );
}
