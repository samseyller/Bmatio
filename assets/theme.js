/* Optional color preference. Navigation and content remain usable without JS. */
(() => {
  'use strict';
  const key = 'bmatic-theme';
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference;
  try { preference = localStorage.getItem(key); } catch (_) { /* Storage may be blocked. */ }
  if (preference !== 'dark' && preference !== 'light') preference = null;
  const apply = () => {
    const dark = preference ? preference === 'dark' : system.matches;
    root.dataset.theme = dark ? 'dark' : 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.hidden = false;
      button.setAttribute('aria-pressed', String(dark));
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#081327' : '#F4F6FA';
  };
  apply(); // Before styles/content paint, restore the saved preference.
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.addEventListener('click', () => {
        preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(key, preference); } catch (_) { /* Still works for this page. */ }
        apply();
      });
    });
  });
  system.addEventListener('change', () => { if (!preference) apply(); });
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = event.newValue === 'light' || event.newValue === 'dark' ? event.newValue : null;
    apply();
  });
})();
