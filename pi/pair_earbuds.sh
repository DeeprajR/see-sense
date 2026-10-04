#!/usr/bin/env bash
# Pair Bluetooth earbuds and make them the default audio output.
#
#   bash pi/pair_earbuds.sh                  # scan, then pick from the list
#   bash pi/pair_earbuds.sh AA:BB:CC:DD:EE:FF
#
# Put the earbuds in pairing mode first (usually: in the case, lid open, hold the button).
set -euo pipefail

MAC="${1:-}"
bluetoothctl power on >/dev/null
bluetoothctl agent on >/dev/null 2>&1 || true

if [[ -z "$MAC" ]]; then
    echo "Scanning for 15 s..."
    bluetoothctl --timeout 15 scan on >/dev/null || true
    echo
    bluetoothctl devices | nl -w2 -s') '
    echo
    read -rp "Number of your earbuds: " n
    MAC="$(bluetoothctl devices | sed -n "${n}p" | awk '{print $2}')"
    [[ -n "$MAC" ]] || { echo "No such entry" >&2; exit 1; }
fi

echo "Pairing $MAC ..."
bluetoothctl pair "$MAC" || true      # fails harmlessly if already paired
bluetoothctl trust "$MAC"             # trusted = reconnects automatically after reboot
bluetoothctl connect "$MAC"

sleep 3
# Make the earbuds the default output: find their line in the "Sinks:" section of wpctl status.
NAME="$(bluetoothctl info "$MAC" | sed -n 's/^[[:space:]]*Name: //p')"
SINK=""
if [[ -n "$NAME" ]]; then
    SINK="$(wpctl status | awk '/Sinks:/{f=1;next} /Sources:/{f=0} f' \
            | grep -F -m1 "$NAME" | grep -o -E '[0-9]+\.' | head -1 | tr -d '.')" || true
fi
if [[ -n "$SINK" ]]; then
    wpctl set-default "$SINK"
    echo "Default audio output set to sink $SINK"
else
    echo "Couldn't find the earbuds in 'wpctl status' -- set it by hand: wpctl set-default <id>"
fi

espeak-ng "Earbuds connected"
echo "Did you hear 'Earbuds connected' in the earbuds?"
