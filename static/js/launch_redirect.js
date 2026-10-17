/*
 * static/js/launch_redirect.js — open the app when the homepage is launched
 * from the Home Screen.
 *
 * A Home Screen copy of the homepage (saved from `/`, which has no
 * manifest) opens full screen on the homepage itself. This sends that
 * launch to the app's start page (<meta name="app-start">) before first
 * paint. It runs only on a cold start in standalone display mode: once an
 * app page has run launch_gate.js, the session is marked, so following the
 * wordmark home from inside the app still shows the homepage.
 *
 * Loaded as a blocking script in <head> (the CSP allows no inline script).
 */
(function () {
  'use strict';
  try {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    if (!standalone || sessionStorage.getItem('app:launched')) return;
    const meta = document.querySelector('meta[name="app-start"]');
    if (meta && meta.content) window.location.replace(meta.content);
  } catch (e) {
    // Storage blocked: stay on the homepage rather than risk a redirect loop.
  }
})();
