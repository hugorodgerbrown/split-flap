#!/usr/bin/env bash
# Turn a fresh Raspberry Pi OS Lite (64-bit) into a Riffle kiosk: on every
# boot it opens a full-screen browser on this Pi's start page, which shows a
# pairing code until the Pi is linked to a display, then the display's board
# (docs/raspberry-pi.md).
#
#   curl -fsSL https://raw.githubusercontent.com/hugorodgerbrown/split-flap/main/raspberry-pi/install.sh | sudo bash
#
# Safe to run again: it brings the Pi up to date and leaves the linked
# display alone. RIFFLE_SERVER points it at another server, RIFFLE_REF at
# another branch of this repository.
set -euo pipefail

RIFFLE_SERVER="${RIFFLE_SERVER:-https://split-flap.ultraniche.ai}"
RIFFLE_REF="${RIFFLE_REF:-main}"
RAW="https://raw.githubusercontent.com/hugorodgerbrown/split-flap/${RIFFLE_REF}/raspberry-pi"
KIOSK_USER=riffle

say() { printf '\n==> %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run this with sudo." >&2
  exit 1
fi
if [[ ! "$RIFFLE_SERVER" =~ ^https?://[^/[:space:]]+$ ]]; then
  echo "RIFFLE_SERVER must be a bare address like https://split-flap.ultraniche.ai, not '$RIFFLE_SERVER'." >&2
  exit 1
fi

say "Installing the browser, the kiosk compositor and sound"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q --no-install-recommends \
  cage curl python3 qrencode fonts-dejavu-core \
  pipewire pipewire-pulse wireplumber \
  unattended-upgrades
# Raspberry Pi OS calls it chromium from Trixie, chromium-browser before.
apt-get install -y -q chromium || apt-get install -y -q chromium-browser
CHROMIUM="$(command -v chromium || command -v chromium-browser)"

say "Turning on automatic security updates"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

say "Adding the ${KIOSK_USER} user, who runs the browser and can't log in"
if ! id "$KIOSK_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/home/${KIOSK_USER}" --shell /usr/sbin/nologin "$KIOSK_USER"
fi
usermod -a -G video,render,input,audio "$KIOSK_USER"
# Keeps the user's sound service (PipeWire) running without a login.
loginctl enable-linger "$KIOSK_USER"

say "Installing the kiosk"
install -d -m 755 /opt/riffle /etc/riffle
here="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -n "$here" && -f "$here/riffle_kiosk.py" ]]; then
  install -m 644 "$here/riffle_kiosk.py" /opt/riffle/riffle_kiosk.py
else
  curl -fsSL "$RAW/riffle_kiosk.py" -o /opt/riffle/riffle_kiosk.py
  chmod 644 /opt/riffle/riffle_kiosk.py
fi
printf 'RIFFLE_SERVER=%s\n' "$RIFFLE_SERVER" > /etc/riffle/kiosk.env

cat > /usr/local/bin/riffle-kiosk <<'EOF'
#!/bin/sh
# riffle-kiosk status | unlink (docs/raspberry-pi.md)
set -a
. /etc/riffle/kiosk.env
set +a
exec /usr/bin/python3 /opt/riffle/riffle_kiosk.py "$@"
EOF
chmod 755 /usr/local/bin/riffle-kiosk

say "Starting the kiosk on boot"
cat > /etc/systemd/system/riffle-kiosk.service <<EOF
[Unit]
Description=Riffle kiosk: the start page on 127.0.0.1:8737
After=network.target

[Service]
User=${KIOSK_USER}
EnvironmentFile=/etc/riffle/kiosk.env
ExecStart=/usr/bin/python3 /opt/riffle/riffle_kiosk.py serve
StateDirectory=riffle
Restart=always
RestartSec=2
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

# cage runs one program full screen and quits with it, so systemd brings the
# browser back if it ever closes (github.com/cage-kiosk/cage/wiki).
cat > /etc/pam.d/riffle-display <<'EOF'
auth     required pam_unix.so nullok
account  required pam_unix.so
session  required pam_unix.so
session  required pam_systemd.so
EOF

cat > /etc/systemd/system/riffle-display.service <<EOF
[Unit]
Description=Riffle display: Chromium full screen on tty1
After=systemd-user-sessions.service plymouth-quit-wait.service riffle-kiosk.service
After=dbus.socket systemd-logind.service getty@tty1.service
Wants=dbus.socket systemd-logind.service riffle-kiosk.service
Conflicts=getty@tty1.service
ConditionPathExists=/dev/tty1

[Service]
User=${KIOSK_USER}
PAMName=riffle-display
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
StandardInput=tty-fail
StandardOutput=journal
StandardError=journal
UtmpIdentifier=tty1
UtmpMode=user
# Wait for the start page, or the browser would open on an error.
ExecStartPre=/usr/bin/curl -fsS --retry 30 --retry-connrefused --retry-delay 1 -o /dev/null http://127.0.0.1:8737/state
ExecStart=/usr/bin/cage -d -- ${CHROMIUM} --kiosk --noerrdialogs --no-first-run \\
  --disable-infobars --disable-session-crashed-bubble --hide-crash-restore-bubble \\
  --disable-features=Translate,MediaRouter --overscroll-history-navigation=0 \\
  --autoplay-policy=no-user-gesture-required --password-store=basic \\
  --check-for-update-interval=31536000 --ozone-platform=wayland \\
  http://127.0.0.1:8737/
Restart=always
RestartSec=2

[Install]
WantedBy=graphical.target
EOF

say "Keeping the screen on"
cmdline=/boot/firmware/cmdline.txt
[[ -f "$cmdline" ]] || cmdline=/boot/cmdline.txt
if [[ -f "$cmdline" ]] && ! grep -q 'consoleblank=0' "$cmdline"; then
  sed -i '1 s/$/ consoleblank=0/' "$cmdline"
fi

systemctl daemon-reload
systemctl set-default graphical.target
systemctl enable riffle-kiosk.service riffle-display.service
systemctl restart riffle-kiosk.service riffle-display.service

say "Done"
cat <<EOF
The TV now shows a pairing code (it may take a few seconds).
On your phone, go to ${RIFFLE_SERVER#*://}/app/display/pair/ and type it.

  riffle-kiosk status          which display this Pi shows
  sudo riffle-kiosk unlink     show a different display
EOF
