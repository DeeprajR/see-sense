# SENSE Wayfinder

**Hold the button, say where you want to go, and get guided there.**

SENSE Wayfinder is the focused version of SENSE, a wearable AI for blind people built at the
Jugaad Junction hackathon. It solves one problem:
helping a blind person get from where they stand to a place they can't see indoors, such as the
door, the exit, a free seat or the counter, without bumping into things on the way.

```
Hold button: "Take me to the exit"
   │
   ▼
1. SURVEY      Claude looks through the chest camera. Unless the exit and a clear way are
               plainly in view, it looks around first: "Turn right about 60 degrees.",
               "Tilt the camera up.", "Take one step to your left." (to see past a corner).
               Left/right motor pulses until you've turned; the turn is measured from the camera.
2. NEAREST     It picks the nearest door or exit it can reach ("a cupboard door is not an exit").
3. WALKWAY     It traces how far the way is clear. A view from beside a corner or a table can
               look blocked when it isn't, so it checks from another angle before deciding.
4. BLOCKER     A chair or an empty wheelchair in the way: it guides you up to it. When the
               distance sensor says you've reached it: "The chair is right in front of you.
               Push it to your left to clear the way. Press the button when you're done."
               (It never asks you to move a person or someone's wheelchair: it routes around.)
5. GUIDE       "The nearest door is on your right. Turn right about 90 degrees." (pulses) ->
               "Walk about 3 steps." Press the button for each next step; every 2 steps it
               takes a new photo and updates the route.
               "The door is right in front of you. The handle is on the right."

Distance sensor (always on, no internet, no AI): buzz when something is under 1 m ahead,
"Stop. Something right in front of you." under 0.5 m.
```

## How to use it

| Do | What happens |
|---|---|
| **Hold** the button, speak, release | A new request ("take me to the exit", "find me a free seat", "where's the counter?") or the answer to Claude's question |
| **Press** the button | The next step. After every 2 steps it takes a new photo and updates the route |
| Hold and say "next", "repeat", "look again", "stop" | Same as the names say |
| Feel left or right pulses | Keep turning that way |
| Feel a long buzz on the front | Something within 1 m ahead |
| Feel fast front pulses + "Stop" | Something within 0.5 m |
| Feel three pulses | You've arrived |
| "...Push it to your left... Press the button when you're done." | Move the chair, then press: it takes a new photo to check the way is clear |

Each look takes about **3–5 seconds** while Claude thinks (measured: 4.5 s for a first answer,
3.1 s for a re-check; a survey with one turn: 8 s plus the time you take to turn). The distance
warning never waits for it.

## Hardware

| Part | Job | Connection (BCM numbering) |
|---|---|---|
| Raspberry Pi 5 + Active Cooler | Runs everything | — |
| Pi Camera 3, on the chest | Claude's eyes; also measures how far you turn | CAM port (22-pin cable) |
| INMP441 microphone | Hears your request | VDD→3.3V (pin 1), GND (pin 6), **L/R→GND**, SCK→GPIO18 (pin 12), WS→GPIO19 (pin 35), SD→GPIO20 (pin 38) |
| VL53L0X / VL53L1X distance sensor, next to the camera | "Something close ahead" | VIN→3.3V, GND, SDA→GPIO2 (pin 3), SCL→GPIO3 (pin 5) |
| Push button | Hold = speak, press = next step | GPIO17 (pin 11) ↔ GND |
| 4 vibration motors (left, front-left, front-right, right) | Turn left/right, obstacle ahead, arrived | GPIO12, 13, 16, 26, each through an NPN transistor (2N2222/S8050) + 1 kΩ base resistor + 1N4007 diode across the motor; motor power from the 3.7 V LiPo (TP4056), **grounds shared with the Pi** |
| Bluetooth earbuds | Speech | Paired with `pi/pair_earbuds.sh` |
| Power bank, USB-C PD 5 V 3 A | Powers the Pi | USB-C |

Don't connect motors straight to GPIO pins: they draw 50–90 mA and a pin gives about 16 mA.

### Pins used (Raspberry Pi 5)
```
                 3V3  (1) (2)  5V
   ToF SDA ── GPIO2   (3) (4)  5V
   ToF SCL ── GPIO3   (5) (6)  GND ── mic GND
                GPIO4 (7) (8)  GPIO14
                  GND (9) (10) GPIO15       (pin 9: ToF GND)
   Button ─── GPIO17 (11) (12) GPIO18 ── mic SCK
               GPIO27 (13) (14) GND ── button GND
               GPIO22 (15) (16) GPIO23
  ToF VIN ──── 3V3 (17) (18) GPIO24
               GPIO10 (19) (20) GND
                GPIO9 (21) (22) GPIO25
               GPIO11 (23) (24) GPIO8
                  GND (25) (26) GPIO7
                GPIO0 (27) (28) GPIO1
                GPIO5 (29) (30) GND ── motor switches' common ground
                GPIO6 (31) (32) GPIO12 ── motor LEFT
 motor FRONT-LEFT ── GPIO13 (33) (34) GND
    mic WS ── GPIO19 (35) (36) GPIO16 ── motor FRONT-RIGHT
 motor RIGHT ── GPIO26 (37) (38) GPIO20 ── mic SD (data)
                  GND (39) (40) GPIO21
   (mic VDD → pin 1, 3V3; mic L/R → GND)
```

### One motor switch (build four: on GPIO12, 13, 16 and 26)
```
   LiPo + (TP4056 OUT+) ──────────────────┬──────────────┐
                                          │              │
                                   ┌──────┴─────┐   1N4007 diode
                                   │  vibration │   (stripe toward LiPo +)
                                   │   motor    │        │
                                   └──────┬─────┘        │
                                          ├──────────────┘
                                          │ collector
   Pi GPIO12 ──[ 1 kΩ ]────────── base ──┤  2N2222 / S8050 (NPN)
                                          │ emitter
   Pi GND ════════════════════════════════┴════ LiPo − (TP4056 OUT−)   ← the grounds MUST be joined
```
When the pin goes high, the transistor switches on and the motor buzzes; the pin's PWM sets how
strongly. The diode absorbs the voltage spike when the motor stops.

### Power
```
  Power bank (5V, 3A+) ──USB-C──► Raspberry Pi 5
  USB charger ──► TP4056 (protected) ──► LiPo 3.7V
                     OUT+ ──► + of all 4 motors
                     OUT− ──► transistor emitters ═══ Pi GND   (shared ground)
```

## Set up the Pi

On the laptop, build the folder to copy (exactly what the Pi needs, including `.env` with your
keys; `--no-env` leaves them out):
```powershell
cd wayfinder
python tools/make_pi_upload.py            # -> dist\wayfinder (not committed)
scp -r dist\wayfinder <user>@<PI_IP>:~/
```
Or clone this repository on the Pi (`git clone <repo-url> ~/wayfinder`) and copy `.env` to it
separately: the keys are never in the repository.
On the Pi:
```bash
cd ~/wayfinder
bash pi/setup_pi.sh          # packages, mic + I2C drivers, backup voice; tells you what's missing
sudo reboot                  # first time only (mic and I2C drivers)
bash pi/setup_pi.sh          # once more: now it can see the distance sensor and install its driver
bash pi/pair_earbuds.sh      # pick the earbuds from the list
bash pi/test_mic.sh          # records 4 s and plays it back
python pi/test_tof.py        # live distance readings
source .venv/bin/activate
python pi/camera_check.py --ask "where is the door?"   # focus, brightness and Claude's answer
python main.py               # run it
bash pi/install_autostart.sh # start at boot (turns off the full SENSE service if installed)
```

**To update** after changing code: run `python tools/make_pi_upload.py` and copy the folder again
with the same `scp` command (or `git pull` on the Pi), then
`ssh <user>@<PI_IP> "systemctl --user restart wayfinder"`.

## Try it on the laptop

```powershell
cd wayfinder
python -m pip install -r requirements.txt
copy .env.example .env                                        # add your keys
python main.py --source 0 --show                              # webcam
python main.py --source http://<PHONE_IP>:4747/video --show   # phone camera (DroidCam)
python tests/test_wayfinder.py                                # 18 tests, no hardware or internet needed
```
Type a request in the terminal ("take me to the door"), or in the preview window press **v** to
talk (v again to send), **n**/space = next step, **l** = look again, **r** = repeat, **s** = stop,
**q** = quit.

## API keys (`.env`, never committed)

| Key | For |
|---|---|
| `ANTHROPIC_API_KEY` (+ `ANTHROPIC_WORKSPACE_ID` if the key isn't workspace-scoped) | Claude: seeing and planning (required) |
| `ELEVENLABS_API_KEY` | Natural voice (optional; the local voice is used without it) |

## Files

| File | Role |
|---|---|
| `main.py` | The app: button and voice, guiding loop, turn guidance, distance warning |
| `planner.py` | Claude: look / ask / plan / arrived / answer, a few steps at a time |
| `motion.py` | How far you turned, measured from the camera picture |
| `camera.py` | Pi Camera (autofocus, full width, short exposure), webcam, phone, video |
| `distance.py` | VL53L0X / VL53L1X distance sensor (chip detected automatically) |
| `haptics.py` | The 4 motors and their patterns |
| `voice.py` | Push-to-talk microphone + offline speech recognition (Vosk) |
| `speech.py`, `voices.py` | Speaking: ElevenLabs recordings cached on the device, local voice as backup |
| `controls.py` | Button, preview-window keys, typed requests |
| `config.py` | Every setting and pin |
| `pi/` | Setup, earbud pairing, mic / sensor / camera checks, autostart |
| `tools/` | Build the Pi upload folder; record the fixed sentences |
| `tests/` | 18 automated tests with a stand-in for Claude |

## What gets installed on the Pi

Only what Wayfinder uses (`pi/setup_pi.sh`):

| Package | For |
|---|---|
| `python3-picamera2`, `python3-opencv`, `python3-numpy` (apt) | Camera, turn measurement, pictures for Claude |
| `pipewire-audio`, `wireplumber`, `libspa-0.2-bluetooth`, `bluez` (apt) | Bluetooth earbuds |
| `alsa-utils`, `libportaudio2` (apt); `sounddevice` (pip) | Microphone and playing sound |
| `espeak-ng` (apt) | Backup voice when a sentence isn't recorded and there's no internet |
| `python3-gpiozero`, `python3-lgpio` (apt) | Motors and button |
| `i2c-tools` (apt); `smbus2` (pip) | Finding the distance sensor |
| `vl53l1x` **or** `adafruit-circuitpython-vl53l0x` + `adafruit-blinka` (pip) | The distance sensor: only the driver for the chip that's connected |
| `anthropic` (pip) | Claude (also brings `httpx`, which the ElevenLabs voice uses) |
| `vosk` (pip) + its 40 MB English model | Offline speech recognition |

## Limits

- **Needs internet** for Claude. Without it, Wayfinder says so; the distance warning still works.
- **Indoor wayfinding, not street safety.** It doesn't warn about traffic. Keep using the cane.
- Distances are estimates ("about 4 steps"); Claude re-checks every 2 steps.
- The distance sensor only sees straight ahead, not drops, kerbs or stairs going down.
- Costs about $0.01–0.02 per Claude look (Sonnet 5.5).
