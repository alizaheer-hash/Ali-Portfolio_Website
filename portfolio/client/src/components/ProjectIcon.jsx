import React from 'react';

// Simple outline icons (24x24 grid) drawn with currentColor, so they follow the theme.
const PATHS = {
  // guard's eye: detection / stealth
  eye: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  // voxel block
  cube: (
    <>
      <path d="M12 2.5l8.5 4.75v9.5L12 21.5l-8.5-4.75v-9.5z" />
      <path d="M3.5 7.25L12 12l8.5-4.75M12 12v9.5" />
    </>
  ),
  // vault / padlock
  lock: (
    <>
      <rect x="4" y="10.5" width="16" height="10.5" rx="2.5" />
      <path d="M8 10.5V7.5a4 4 0 018 0v3" />
      <circle cx="12" cy="15.7" r="1.4" />
    </>
  ),
  // medical cross
  cross: <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" />,
};

export default function ProjectIcon({ name, size = 44 }) {
  const body = PATHS[name];
  if (!body) return null;
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"
    >
      {body}
    </svg>
  );
}
