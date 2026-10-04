#!/usr/bin/env bash
# Start SEE SENSE automatically at boot -- no screen, keyboard or SSH needed.
#
#   bash pi/install_autostart.sh            # enable
#   bash pi/install_autostart.sh --stream   # enable, with the live camera view on port 8000
#   bash pi/install_autostart.sh --remove   # disable
#
# Runs as a *user* service (not root) so it can use the user's PipeWire session, which routes
# audio to the Bluetooth earbuds. Turns off the full SENSE service if it was installed: only one
# program can use the camera at a time.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/seesense.service"

if [[ "${1:-}" == "--remove" ]]; then
    systemctl --user disable --now seesense.service 2>/dev/null || true
    rm -f "$UNIT"
    systemctl --user daemon-reload
    echo "SEE SENSE autostart removed."
    exit 0
fi

EXTRA=""
[[ "${1:-}" == "--stream" ]] && EXTRA=" --stream"

if systemctl --user is-enabled sense.service >/dev/null 2>&1; then
    systemctl --user disable --now sense.service
    echo "Turned off the full SENSE service (it would compete for the camera)."
fi
# This app used to be called Wayfinder: remove its old service so only one runs.
if [[ -f "$UNIT_DIR/wayfinder.service" ]]; then
    systemctl --user disable --now wayfinder.service 2>/dev/null || true
    rm -f "$UNIT_DIR/wayfinder.service"
    echo "Removed the old wayfinder service (renamed to seesense)."
fi

mkdir -p "$UNIT_DIR"
cat > "$UNIT" <<EOF
[Unit]
Description=SEE SENSE - guided to where you want to go
After=pipewire.service wireplumber.service network-online.target
Wants=pipewire.service wireplumber.service

[Service]
WorkingDirectory=$APP_DIR
# Give Bluetooth a moment to reconnect the earbuds after boot.
ExecStartPre=/bin/sleep 8
ExecStart=$APP_DIR/.venv/bin/python main.py --source picam$EXTRA
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

# Lingering lets user services (and PipeWire) start at boot without anyone logging in.
sudo loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now seesense.service

echo "SEE SENSE will now start at every boot."
echo "  Logs:     journalctl --user -u seesense -f"
echo "  Stop:     systemctl --user stop seesense"
echo "  Restart:  systemctl --user restart seesense"
if [[ -n "$EXTRA" ]]; then echo "  Live view: http://$(hostname -I | cut -d' ' -f1):8000"; fi
