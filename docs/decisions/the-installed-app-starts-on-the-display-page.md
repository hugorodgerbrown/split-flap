# The installed app starts on the display page

Status: accepted (RAS-83), 2026-10-17

## Context

The Titan template's manifest starts the installed app on its example
feature, the notes list at `/app/`. Riffle's app is the display page
(`/app/display/`), so an install opened on Notes. Worse, the manifest is
linked only from the app's own pages: "Add to Home Screen" on the public
homepage, where people arrive, saves `/` itself, and iOS opens every Home
Screen site as a web app, so the "app" launched on the homepage.

## Decision

- The manifest's `start_url` is the display page. `id` and `scope` stay
  `/app/`, so installs made before the change keep their identity and pick
  up the new start page. Signed out, the display page sends the person to
  sign-in and back, as every app page does.
- The homepage carries a tiny blocking script, `launch_redirect.js`: on a
  cold start in standalone display mode it replaces itself with the
  display page before it paints. Once any app page has run, the session is
  marked (`launch_gate.js`), so the wordmark's link home from inside the
  app still shows the homepage.
- Public pages still link no manifest
  ([the-installed-app-is-scoped-to-app.md](the-installed-app-is-scoped-to-app.md)):
  the redirect covers a Home Screen copy of `/`, and installing from an app
  page installs the real app.

## Consequences

- The start page now redirects when signed out, so a signed-out first
  launch needs the network, as signing in does anyway. Signed in, the
  display page answers 200 and the worker caches it like any app page.
- `copier update` will conflict where the template changes `start_url`,
  the offline page's link or the homepage's head: keep this app's side.
