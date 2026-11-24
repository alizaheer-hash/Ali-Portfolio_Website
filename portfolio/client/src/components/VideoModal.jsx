import React, { useEffect, useRef } from 'react';

// Lightweight dialog that plays a project demo recording. Closes on Escape, backdrop click or the
// close button, locks page scroll while open and returns focus to the button that opened it.
export default function VideoModal({ project, onClose }) {
  const closeRef = useRef(null);

  useEffect(() => {
    const opener = document.activeElement;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      if (opener && opener.focus) opener.focus();
    };
  }, [onClose]);

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal__box" role="dialog" aria-modal="true" aria-label={`${project.title} demo video`} onClick={(e) => e.stopPropagation()}>
        <div className="modal__bar">
          <strong>{project.title}</strong>
          <button ref={closeRef} className="icon-btn" onClick={onClose} aria-label="Close video">✕</button>
        </div>
        <video className="modal__video" src={project.video} poster={project.poster || undefined} controls autoPlay playsInline preload="metadata" />
      </div>
    </div>
  );
}
