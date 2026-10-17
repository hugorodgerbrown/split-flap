# The display's sound is a saved setting that starts at the first tap

Status: accepted (2026-10-17)

## Context

The flap sound can be switched on from the display page (RAS-71), but the
TV is a different device. Browsers don't let a page play sound until
someone taps it, clicks it or presses a key. So a setting saved somewhere
else can't make a TV play sound on its own.

## Decision

`Display.sound` is saved on the server and sent in the state the TV
polls. "On" means "play as soon as the browser allows it":

- The TV tries to start the sound when the setting turns on. Where the
  browser allows it, as in some kiosk browsers, the sound starts straight
  away.
- Otherwise the TV shows "Tap for sound" until the first tap or key press,
  so a TV remote's arrow keys also start it.
- The TV's own Sound button and its S key switch the sound for that screen
  until the setting next changes.

## Consequences

- Turning the sound on from the display page doesn't make a quiet room
  noisy by surprise: someone has to be at the TV.
- The hint is the only thing on the TV that isn't the board or its
  controls. It stays up while the controls hide, because the person who
  has to tap is usually across the room.
