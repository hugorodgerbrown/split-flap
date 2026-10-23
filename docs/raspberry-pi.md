# The Raspberry Pi kiosk

`raspberry-pi/` turns a Raspberry Pi into a box that does one thing: plug
it into a TV's HDMI and it shows your display's board, full screen, with
sound. It has no accounts, no apps and no home screen, so it works with any
TV, including ones (like Samsung's) that the Android TV app can't run on.
Why it is built this way:
[docs/decisions/a-raspberry-pi-is-the-tv-appliance.md](decisions/a-raspberry-pi-is-the-tv-appliance.md).

## What to buy

| Part | Notes |
| --- | --- |
| Raspberry Pi 4 Model B, 2GB or more | A Pi 5 works too. A Pi Zero 2 W is untested and may stutter on the flaps. |
| Its official power supply | USB-C, 15W for a Pi 4 (27W for a Pi 5). A phone charger often isn't enough. |
| A case | Any; one with a fan or heatsink if it sits behind a TV. |
| A microSD card, 16GB or more | A2-rated cards are quicker. |
| Micro-HDMI to HDMI cable | The Pi 4 and 5 have micro-HDMI sockets. Use the one nearest the power socket (HDMI 0). |

A starter kit usually has all of these.

## Setting it up

1. **Flash the card.** On a computer, install
   [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Choose your
   Pi, then **Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)**. When
   it offers to customise settings, set:
   - a hostname, like `riffle`
   - a username and password for you
   - your Wi-Fi network and country
   - **Services → Enable SSH** (password authentication is fine)
2. **Start the Pi.** Put the card in, plug the Pi into the TV, then power.
   The first boot takes a minute or two and ends at a login prompt.
3. **Install Riffle.** From your computer, on the same Wi-Fi:

   ```bash
   ssh <you>@riffle.local
   curl -fsSL https://raw.githubusercontent.com/hugorodgerbrown/split-flap/main/raspberry-pi/install.sh | sudo bash
   ```

   It takes a few minutes. When it finishes, the TV shows a pairing code.
4. **Pair it.** On your phone, scan the QR code, or go to
   `split-flap.ultraniche.ai/app/display/pair/` and type the code. The TV
   shows your board within a few seconds, and goes straight to it on every
   boot from then on.

The Pi doesn't need you after that. If the Wi-Fi drops or the server is
down, the TV says "Reconnecting to Riffle…" and goes back to the board by
itself.

## Looking after it

From your computer, `ssh <you>@riffle.local`, then:

| Command | What it does |
| --- | --- |
| `riffle-kiosk status` | Which display this Pi shows, and whether its board loads. |
| `sudo riffle-kiosk unlink` | Forget the display; the TV shows a new pairing code. |
| `sudo reboot` | Start again. It comes back to the board. |
| Run the install command again | Update the kiosk. The linked display is kept. |

Security updates install themselves each day (`unattended-upgrades`).

If you delete the display the Pi shows, it goes back to pairing on its own
within five minutes.

## When something is wrong

- **No sound.** Check the TV isn't muted, then on the Pi:
  `sudo -u riffle XDG_RUNTIME_DIR=/run/user/$(id -u riffle) wpctl status`.
  Under **Sinks**, the HDMI output should have a `*`; if not,
  `… wpctl set-default <its number>`. The board's own sound setting, on the
  display page, must be on too.
- **The sound is late.** TVs and soundbars play sound a little late. Turn up
  **Sound timing** on the display page and press **Replay** until the clacks
  land with the flaps (docs/android-tv.md, "When the sound is late").
- **A black screen.** `systemctl status riffle-kiosk riffle-display` and
  `journalctl -u riffle-display -b` say what went wrong.
- **The picture doesn't fill the TV.** Turn the TV's picture size to
  **Fit to screen** (Samsung: Picture → Picture Size Settings).

## How it works

`install.sh` installs Chromium, the `cage` kiosk compositor, PipeWire for
HDMI sound and `qrencode`, then two systemd services that start on boot:

- **`riffle-kiosk`** runs `riffle_kiosk.py serve` as the `riffle` user: a
  start page on `127.0.0.1:8737` and a worker that pairs with the server
  (`POST /d/pair/`, then polls, as the Android TV app does), keeps the link
  in `/var/lib/riffle/display.json`, and checks the board loads before
  sending the browser to it. While the board shows, it checks every five
  minutes that the display still exists; if it was deleted, it closes the
  browser so it reopens on a new pairing code.
- **`riffle-display`** runs Chromium under cage on the TV, full screen,
  allowed to play sound without a tap, always opening the start page. If
  the browser ever closes, systemd starts it again, which re-checks the
  board.

`/etc/riffle/kiosk.env` holds the server's address (`RIFFLE_SERVER`). To try
it against another server, install with
`curl … | sudo RIFFLE_SERVER=https://staging.example bash`.

## Changing it

`riffle_kiosk.py` uses only Python's standard library, and must run on the
Python Raspberry Pi OS ships (3.11 on Bookworm), not the app's: ruff checks
it as 3.11 (`per-file-target-version` in `pyproject.toml`) and CI compiles
it with Python 3.11. Its tests are `tests/raspberry_pi/`, including one that
runs its parsers against the real pairing endpoints. CI runs `shellcheck`
on `install.sh` (`.github/workflows/raspberry-pi.yml`).
