(function () {
  'use strict';

  const key = 'rf4-assistant-theme';
  let savedTheme = null;
  try {
    savedTheme = localStorage.getItem(key);
  } catch (_error) {
    // Storage can be unavailable (private mode, browser restrictions).
  }

  const currentTheme = savedTheme === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-bs-theme', currentTheme);

  function updateButton() {
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    button.querySelector('.theme-icon').textContent = isDark ? '☀' : '☾';
    button.querySelector('.theme-label').textContent = isDark ? 'Светлая тема' : 'Тёмная тема';
    const label = isDark ? 'Включить светлую тему' : 'Включить тёмную тему';
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
  }

  document.addEventListener('DOMContentLoaded', function () {
    updateButton();
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    button.addEventListener('click', function () {
      const next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', next);
      try { localStorage.setItem(key, next); } catch (_error) { /* Ignore storage errors. */ }
      updateButton();
    });
  });
})();
