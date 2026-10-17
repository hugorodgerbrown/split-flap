// Tests for static/js/launch_redirect.js: a Home Screen launch of the homepage opens the app.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

let replace;

function standalone(matches) {
  vi.stubGlobal('matchMedia', () => ({ matches }));
}

beforeEach(() => {
  document.head.innerHTML = '<meta name="app-start" content="/app/display/">';
  replace = vi.fn();
  vi.stubGlobal('location', { replace });
  sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
  document.head.innerHTML = '';
});

describe('launch redirect', () => {
  it('opens the app on a standalone cold start', async () => {
    standalone(true);
    await import('../../static/js/launch_redirect.js?cold');
    expect(replace).toHaveBeenCalledWith('/app/display/');
  });

  it('redirects only once a session, so the way home from sign-in works', async () => {
    standalone(true);
    await import('../../static/js/launch_redirect.js?first');
    vi.resetModules();
    await import('../../static/js/launch_redirect.js?again');
    expect(replace).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem('app:launched')).toBeNull();
  });

  it('stays on the homepage in a browser tab', async () => {
    standalone(false);
    await import('../../static/js/launch_redirect.js?tab');
    expect(replace).not.toHaveBeenCalled();
  });

  it('stays on the homepage when an app page has already run', async () => {
    sessionStorage.setItem('app:launched', '1');
    standalone(true);
    await import('../../static/js/launch_redirect.js?later');
    expect(replace).not.toHaveBeenCalled();
  });
});
