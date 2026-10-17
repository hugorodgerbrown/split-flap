# A TV app pairs with a short code

Status: accepted (2026-10-17)

## Context

The Android TV app (RAS-67) needs the display's secret link, `/d/<uuid>/`.
Typing 36 characters with a TV remote is the worst moment of setting one
up, and a TV is a poor place to sign in (docs/decisions/the-tv-polls-a-secret-address.md).

## Decision

The TV asks for a pairing (`POST /d/pair/`) and shows a six-character code
and a QR code. Its owner, signed in on their phone, types the code at
`/app/display/pair/` (the QR code opens that page with the code filled
in). The TV polls `/d/pair/<token>/` every three seconds and, once the code
is claimed, is handed the display's link. It can ask again until the
pairing expires (ten minutes from the claim), so a reply lost on a flaky
network doesn't strand the TV. This is the device flow
YouTube and Netflix use. It lives in its own app, `apps/pairing`, so it
stays apart from the display pages.

## Consequences

- Only hashes are stored: the poll token's sha256 and the code's HMAC with
  the server's secret. Codes last ten minutes and work once.
- Starting a pairing is CSRF-exempt: the TV sends no cookies, so there is
  no session for a forged request to use, and all it makes is a code that
  soon expires. It is rate limited per address; code guesses are rate
  limited per account.
- A code in the QR link appears in access logs. A code can only be
  claimed by a signed-in person, and claiming it puts *their* display on
  the TV that showed it, so a leaked code shows a stranger's board on your
  TV for a moment at worst, never your board on theirs.
- `purge_tv_pairings` clears expired rows with the other daily purges.
