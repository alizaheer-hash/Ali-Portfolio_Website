// All portfolio content lives here, taken from Ali's CV.
// Fill in `repo`, `demo` and `image` for each project when you have them;
// empty values are simply hidden.

export const profile = {
  name: 'Ali Mohammad Zaheer',
  role: 'AI analyst · Game developer',
  tagline: 'I build 3D browser games and turn project data into automation and insight.',
  intro:
    "I'm a Computer Science undergraduate at NED University of Engineering & Technology and a Google AI Professional Certificate holder. I build browser games in Three.js and I'm looking for an AI Analyst role where I can analyse project data, build dashboards and reports, and automate repetitive work.",
  links: {
    github: '',
    linkedin: '',
  },
};

export const projects = [
  {
    id: 'museum-heist',
    title: 'Museum Heist: AI Guard Lab',
    description:
      'A 3D stealth demo with a guard AI state machine (patrol, chase, search), waypoint patrols, a detection radius, last-known-position search and a loot mechanic.',
    tech: ['Three.js', 'JavaScript'],
    tags: ['Game', 'AI'],
    note: 'Built with Claude',
    repo: '',
    demo: '',
    image: '',
  },
  {
    id: 'webcraft',
    title: 'WebCraft',
    description:
      'A voxel sandbox with procedural terrain, chunked meshing and collision. Break and place blocks, use the hotbar, sprint and fly.',
    tech: ['Three.js', 'JavaScript'],
    tags: ['Game', 'Graphics'],
    note: 'Built with Claude',
    repo: '',
    demo: '',
    image: '',
  },
  {
    id: 'neon-vault',
    title: 'Neon Vault',
    description:
      'A 3D browser escape-room game with ordered objectives, a timer, score and a live HUD. Modular design: game state, event bus, game loop and UI components.',
    tech: ['Three.js', 'Vite', 'JavaScript'],
    tags: ['Game'],
    note: 'Built with Claude',
    repo: '',
    demo: '',
    image: '',
  },
  {
    id: 'hospital-system',
    title: 'Hospital Management System',
    description:
      'A team project: a responsive web-based hospital management system with CRUD functionality for doctor records and backend integration.',
    tech: ['HTML', 'CSS', 'PHP', 'MySQL'],
    tags: ['Web', 'Team'],
    note: '',
    repo: '',
    demo: '',
    image: '',
  },
];

export const skillGroups = [
  { title: 'Game development', items: [['Unity', 'Intermediate'], ['C#', 'Intermediate'], ['C / C++', 'Intermediate'], ['OOP & gameplay mechanics', 'Intermediate']] },
  { title: 'Web & 3D', items: [['Three.js / JavaScript', 'Basic'], ['Blender', 'Basic'], ['MySQL', 'Basic'], ['Python', 'Basic']] },
  { title: 'AI & automation', items: [['n8n workflows', 'Workshop'], ['OpenAI / Gemini APIs', 'Workshop'], ['Prompt design & evaluation', 'Certified'], ['AI-assisted app building', 'Certified']] },
];

export const education = [
  {
    when: '2023 – 2027',
    title: 'BS Computer Science',
    where: 'NED University of Engineering & Technology',
    detail: 'Specialising in gaming and animation.',
  },
  {
    when: '2021 – 2023',
    title: 'Intermediate',
    where: 'Govt. Degree Boys & Girls College, Gulshan-e-Iqbal',
    detail: 'Grade A.',
  },
  {
    when: '2010 – 2021',
    title: 'Matriculation',
    where: 'White House Grammar School',
    detail: 'Grade A+.',
  },
];

export const certifications = [
  {
    when: 'Jun 2026',
    title: 'Google AI Professional Certificate',
    where: 'Google (Coursera)',
    detail:
      'Seven-course programme covering AI for research, writing, content creation, data analysis and app building. Built a portfolio of 20+ AI-assisted artifacts, including a custom AI solution.',
  },
  {
    when: 'Workshop',
    title: 'Practical n8n + AI Automation Workshop',
    where: 'Hands-on workshop',
    detail: 'Automation workflows with n8n, AI-powered email and chat automation, and API integrations (OpenAI, Gemini, SerpAPI).',
  },
];

export const suggestedQuestions = [
  'Which projects has Ali built with Three.js?',
  'What are his strongest skills?',
  'Tell me about his education.',
  'What kind of role is he looking for?',
];
