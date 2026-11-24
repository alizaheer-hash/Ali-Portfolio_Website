// Sets the theme before first paint (saved choice, otherwise the system preference).
(function () {
  try {
    var saved = localStorage.getItem('theme');
    var dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.dataset.theme = saved || (dark ? 'dark' : 'light');
  } catch (e) {}
})();
