import React, { useEffect, useState } from 'react';
import Hero3D from './components/Hero3D.jsx';
import Projects from './components/Projects.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import ContactForm from './components/ContactForm.jsx';
import { useTheme } from './theme.js';
import { profile, skillGroups, education, certifications } from './data.js';

const NAV = [
  ['projects', 'Work'],
  ['about', 'About'],
  ['skills', 'Skills'],
  ['education', 'Education'],
  ['video', 'Video'],
  ['contact', 'Contact'],
];

/* Fade sections in as they scroll into view (skipped for reduced motion). */
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach((el) => el.classList.add('reveal--in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('reveal--in'); io.unobserve(e.target); } }),
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  });
}

function VideoSection() {
  const [missing, setMissing] = useState(false);
  return (
    <section id="video" className="section" aria-labelledby="video-h">
      <div className="section__head reveal"><h2 id="video-h">Intro video</h2></div>
      <div className="video reveal">
        {missing ? (
          <div className="video__missing">
            <p>The promo video will appear here.</p>
            <p className="muted">Add <code>promo.mp4</code> to <code>client/public/media/</code>.</p>
          </div>
        ) : (
          <video controls preload="metadata" poster="/media/poster.jpg" onError={() => setMissing(true)}>
            <source src="/media/promo.mp4" type="video/mp4" onError={() => setMissing(true)} />
            Your browser does not support embedded video.
          </video>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [chatOpen, setChatOpen] = useState(false);
  useReveal();

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>

      <header className="header">
        <a className="brand" href="#top">Ali Zaheer</a>
        <nav aria-label="Main">
          <ul>
            {NAV.map(([id, label]) => <li key={id}><a href={`#${id}`}>{label}</a></li>)}
          </ul>
        </nav>
        <button className="btn btn--ghost theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
          {theme === 'dark' ? 'Light theme' : 'Dark theme'}
        </button>
      </header>

      <main id="main">
        <section id="top" className="hero" aria-labelledby="hero-h">
          <div className="hero__text">
            <p className="eyebrow">{profile.role}</p>
            <h1 id="hero-h">Games, 3D and AI that earns its keep.</h1>
            <p className="lead">
              I'm <strong>{profile.name}</strong>, a Computer Science undergraduate at NED University. {profile.tagline}
            </p>
            <div className="hero__cta">
              <a className="btn btn--solid" href="#projects">See my work</a>
              <button className="btn btn--ghost" onClick={() => setChatOpen(true)}>Chat with my AI</button>
            </div>
            <p className="hint">Move your mouse over the scene, and click or tap the avatar to make it wave.</p>
          </div>
          <div className="hero__scene">
            <div className="hero__arch">
              <Hero3D theme={theme} />
            </div>
          </div>
        </section>

        <Projects />

        <section id="about" className="section split" aria-labelledby="about-h">
          <h2 id="about-h" className="reveal">About</h2>
          <div className="prose reveal">
            <p>{profile.intro}</p>
            <p>My interests run through AI and automation, game development and animation. Open to constructive feedback, strong at problem solving and teamwork.</p>
          </div>
        </section>

        <section id="skills" className="section" aria-labelledby="skills-h">
          <div className="section__head reveal"><h2 id="skills-h">Skills &amp; technologies</h2></div>
          <div className="cards">
            {skillGroups.map((g, i) => (
              <div key={g.title} className="card reveal" style={{ '--d': `${i * 80}ms` }}>
                <h3>{g.title}</h3>
                <ul className="skill-list">
                  {g.items.map(([name, level]) => (
                    <li key={name}><span>{name}</span><em>{level}</em></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section id="education" className="section" aria-labelledby="edu-h">
          <div className="section__head reveal"><h2 id="edu-h">Education &amp; certifications</h2></div>
          <div className="timeline-grid">
            <div className="reveal">
              <h3 className="sub">Education</h3>
              <ol className="timeline">
                {education.map((e) => (
                  <li key={e.title}><span className="when">{e.when}</span><strong>{e.title}</strong><span>{e.where}</span><span className="muted">{e.detail}</span></li>
                ))}
              </ol>
            </div>
            <div className="reveal">
              <h3 className="sub">Certifications</h3>
              <ol className="timeline">
                {certifications.map((e) => (
                  <li key={e.title}><span className="when">{e.when}</span><strong>{e.title}</strong><span>{e.where}</span><span className="muted">{e.detail}</span></li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <VideoSection />

        <section id="contact" className="contact" aria-labelledby="contact-h">
          <div className="contact__inner">
            <div className="reveal">
              <h2 id="contact-h">Let's talk.</h2>
              <p className="lead">Send a note, or ask my assistant first. It answers only from my CV and project notes and shows which section each answer came from.</p>
              <button className="btn btn--accent" onClick={() => setChatOpen(true)}>Ask my AI assistant</button>
            </div>
            <div className="reveal"><ContactForm /></div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>© {new Date().getFullYear()} {profile.name}</span>
        <span className="footer__links">
          {profile.links.github && <a href={profile.links.github} target="_blank" rel="noreferrer">GitHub</a>}
          {profile.links.linkedin && <a href={profile.links.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>}
          <a href="#top">Back to top</a>
        </span>
      </footer>

      <button className="chat-fab" onClick={() => setChatOpen((o) => !o)} aria-expanded={chatOpen} aria-label="Open AI assistant">
        Ask AI
      </button>
      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
    </>
  );
}
