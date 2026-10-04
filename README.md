# SENSE Wayfinder

**Hold the button, say where you want to go, and get guided there.**

SENSE Wayfinder is a wearable that guides a blind person to a place they can't see indoors, such as
the door, the exit, a free seat or the counter, one step at a time. It is the focused version of SENSE, built by team Jugaad Junction in Claude Impact Lab - Superhhuman Lab hackathon conducted at Tinkerhub calicut.

> *We give you another way to find your way.*

**Status:** MVP complete 
**The current build** is a Raspberry Pi 5 with the camera, microphone, button and Bluetooth earbuds; it has run in a real classroom and the fixes from that run are shipped.
**Not built yet:** the vibration motors and the distance sensor. Their software is already written and waiting (see [Future scope](#9-future-scope)). 
**Not tested with blind users yet.**

## Contents
1. [The person](#1-the-person) · 2. [The barrier](#2-the-barrier) · 3. [The bridge](#3-the-bridge) ·
4. [The possibility](#4-the-possibility) · 5. [Components](#5-components-what-how-and-why) ·
6. [Features](#6-features) · 7. [Setup](#7-setup) · 8. [Limitations](#8-limitations) ·
9. [Future scope](#9-future-scope)

---

## 1. The person

### Who we are designing for
- **Blind and low-vision adults who move around on their own**, in places they don't know well:
  colleges, offices, hospitals, stations, shops, event halls. Mainly in **Indian cities**, where buildings change often and have few accessible signs.
- They already use a **white cane** (some a guide dog) and often a phone with a screen reader.
  **Wayfinder works alongside the cane. It does not replace it.**
- They are independent and capable: they don't need something that talks all the time. They need
  help at one moment: **"where is it, and how do I get there?"**
- ⚠️ **We have not tested with blind users yet.** This is our understanding so far; the next step is
  to build it *with* them.

### What they are trying to do
- **Get to a place in a room they can't see:** the door, the exit, the toilet, a free seat, the
  reception desk, a counter.
- **Do it on their own,** without waiting for a sighted person to help.
- **Get there safely:** around tables, chairs, people and bags.
- **Keep their hands free:** one hand holds the cane.

---

## 2. The barrier

What makes this difficult, impossible or inaccessible today:

| | The barrier |
|---|---|
| **Body** | No vision, or very little. **One hand holds the cane**, so a phone is hard to use while walking. **Hearing is a safety sense:** footsteps, voices and echoes tell them about the room, so a device that talks all the time gets in the way. |
| **Environment** | Rooms they've never been in. Tables, chairs and bags in the walkway, which **move around**. People walking across. Glass doors. Corners and pillars that hide the door. Few tactile or audio cues indoors. |
| **Information** | Where the door is, which way to face, how far it is and whether the way is clear are all **visual**. A cane finds what's at your feet, not where the door is across the room. **GPS doesn't work indoors.** Signs can't be read. |
| **Interaction** | Description apps say what's in **one photo** ("there's a door"), not **how to get there**, and need a hand and a touchscreen. Video-calling a volunteer needs another person to be available. Asking a stranger isn't always possible, and costs independence. |

---

## 3. The bridge

How AI and hardware work together to remove those barriers (**now** = in the current build):

| Step | What Wayfinder does | With what | |
|---|---|---|---|
| **Hear** | Hold the button and say where you want to go | Button, INMP441 microphone, **Vosk** (offline speech recognition) | now |
| **Check** | Was that a real request, a command said another way, or misheard words? (~0.3 s) | **JEV** (TypeSafe) | now |
| **See and survey** | Looks through the chest camera; asks you to turn, tilt or step aside until it finds the nearest door | Pi Camera 3, **Claude Sonnet 5.5** | now |
| **Plan** | Traces how far the walkway is clear and plans a route around what's in the way | **Claude** | now |
| **Guide** | Speaks the route a few steps at a time in your earbuds; measures your turn from the camera: "Keep turning right" … "OK, stop." when you face the right way | Earbuds, **turn measurement** from the camera (OpenCV) | now |
| **Clear the way** | Guides you up to a chair in the way and, when the next photo shows you've reached it, tells you how to move it | **Claude** | now |
| **Warn only when it matters** | Decides which things it saw need a spoken warning, or nothing | **JEV** | now |
| **Feel the direction** | A vibration on your left or right until you face the right way; a short pulse on the side of something minor | 4 vibration motors | **planned** (software ready) |
| **Protect** | Buzz when something is under 1 m ahead; "Stop" under 0.5 m. **No internet, no AI** | VL53L0X/L1X distance sensor | **planned** (software ready) |

```
Hold button: "Take me to the exit"
   │
   ▼  JEV: a real request? (misheard words -> "Sorry, I didn't catch that." at once)
1. SURVEY      Claude looks through the chest camera. Unless the exit and a clear way are
               plainly in view, it looks around first: "Turn right about 60 degrees.",
               "Tilt the camera up.", "Take one step to your left." (to see past a corner).
               The turn is measured from the camera: "Keep turning right." … "OK, stop."
2. NEAREST     It picks the nearest door or exit it can reach (a cupboard door is not an exit).
3. WALKWAY     It traces how far the way is clear. A view from beside a corner or a table can
               look blocked when it isn't, so it checks from another angle before deciding.
4. BLOCKER     A chair or an empty wheelchair in the way: it guides you up to it, and when the
               next photo shows you've reached it: "The chair is right in front of you. Push it
               to your left to clear the way." (It never asks you to move a person or
               someone's wheelchair: it routes around.)
5. GUIDE       "The nearest door is on your right. Turn right about 90 degrees." ->
               "Walk about 3 steps." Press the button for each next step; every 2 steps it
               takes a new photo and updates the route. Along the way JEV picks what's worth
               a warning: "A person on your left, coming toward you, about 3 steps away."
               "The door is right in front of you. The handle is on the right."
```

**The rules it follows:**
1. **Quiet by default.** Only instructions and real warnings are spoken; minor things are left out.
2. **Be honest.** Say when it's unsure. **Never say a path is "safe".**
3. **Respect people.** Never ask the wearer to move a person or someone's wheelchair.
4. **Planned with the motors and sensor:** direction by touch instead of words, and an obstacle
   warning that works without the internet.

---

## 4. The possibility

What the person can do now that they couldn't before:

| Before | With Wayfinder |
|---|---|
| Walks into an unfamiliar room and has to ask someone where the door is | Holds the button: **"Take me to the exit"** |
| Turns around, unsure which way to face | "Turn right about 90 degrees" … "OK, stop." when they're facing the door, measured as they turn |
| The cane finds a chair only by hitting it | Is guided up to it, then told "The chair is right in front of you. Push it to your left." |
| A description app says "there is a door", but not how to get there | Gets a route: "Walk about 3 steps. The tables will be on your left." |
| A video call needs a volunteer to be free, and a hand for the phone | Hands-free, with no other person needed |
| Doesn't know someone is walking into their path | "A person on your left, coming toward you, about 3 steps away." |
| Reaches the door but has to feel around for the handle | "The door is right in front of you. The handle is on the right." |
| A talking device fills their ears | Quiet unless it matters |

---

## 5. Components: what, how and why

### Hardware in the current build

| Part | How it's used | Why this part |
|---|---|---|
| **Raspberry Pi 5** (4 GB) + Active Cooler | Runs everything on the body: camera, turn measurement, button, mic; talks to Claude and JEV over Wi-Fi | Small, battery-powered, has the pins for every part; no AI model runs on it, so it stays cool |
| **Pi Camera 3**, on the chest | Takes the pictures Claude sees (1024 px); the same frames measure how far you turn | Sharp, with autofocus; a direct connection; faces where your body faces |
| **INMP441 microphone** (I2S) | Records only while the button is held | Digital, so less noise than an analogue mic; Bluetooth earbud mics lower the sound quality |
| **Push button** | Hold = speak, short press = next step | Works in noisy rooms where a wake word fails; the user is in control |
| **Bluetooth earbuds** | All instructions and warnings, spoken | Hands-free; the wearer already owns them |
| **Power bank**, USB-C PD 5 V 3 A | Powers the Pi while walking | Wearable; no wall socket |

### Planned hardware (software already written)

| Part | How it will be used | Why |
|---|---|---|
| **4 vibration motors** (left, front-left, front-right, right), from old phones | Left / right = which way to turn; front = something close; short pulse on a side = something worth knowing there | Direction by touch keeps the ears free and needs fewer words |
| **4 NPN transistors** (2N2222 / S8050) + 1 kΩ resistors + 1N4007 diodes | Switch each motor from a GPIO pin | A pin gives ~16 mA; a motor needs 50–90 mA. The diode absorbs the spike when a motor stops |
| **3.7 V LiPo + TP4056 charger** (protected) | Powers the motors only | Keeps motor noise off the Pi's power |
| **VL53L0X or VL53L1X distance sensor** (ToF), next to the camera | Measures the distance straight ahead ~20 times a second: buzz under 1 m, "Stop" under 0.5 m; tells Wayfinder the moment you reach a chair to move | Catches walls, poles and glass the camera may miss; works with no AI and no internet. Either chip works (detected automatically) |

Until they're fitted, Wayfinder simply runs without them: no setting needs changing.

#### Pins (Raspberry Pi 5): used now, and reserved for the planned parts
```
                 3V3  (1) (2)  5V
   ToF SDA ── GPIO2   (3) (4)  5V                       (ToF = planned distance sensor)
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
                GPIO5 (29) (30) GND ── motor switches' common ground   (planned)
motor FRONT-RIGHT ── GPIO6 (31) (32) GPIO12 ── motor LEFT             (planned)
 motor FRONT-LEFT ── GPIO13 (33) (34) GND                             (planned)
    mic WS ── GPIO19 (35) (36) GPIO16      (reserved by the mic driver: don't use)
 motor RIGHT ── GPIO26 (37) (38) GPIO20 ── mic SD (data)
                  GND (39) (40) GPIO21
   (mic VDD → pin 1, 3V3; mic L/R → GND)
```

#### Planned: one motor switch (build four: on GPIO12, 13, 6 and 26)
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
strongly. **Don't connect motors straight to GPIO pins.**

#### Power
```
  Now:      Power bank (5V, 3A+) ──USB-C──► Raspberry Pi 5
  Planned:  USB charger ──► TP4056 (protected) ──► LiPo 3.7V
                               OUT+ ──► + of all 4 motors
                               OUT− ──► transistor emitters ═══ Pi GND   (shared ground)
```

### Software

| Component | How it's used | Why |
|---|---|---|
| **Claude Sonnet 5.5** (Anthropic API) | Sees each photo; surveys, picks the nearest goal, traces the walkway, plans the route, handles blockers; returns a structured answer (look / ask / plan / arrived / answer) and a list of the important things it saw | Understands a whole room and reasons about routes, which fixed object detectors can't. Sonnet is fast and about $0.01–0.02 per look; Opus is one setting away |
| **JEV** (TypeSafe) | Two quick checks: is what the mic heard a request, a command or misheard words? Which things Claude saw need a spoken warning, or nothing? | Answers in ~0.3 s with a confidence score, so misheard speech doesn't cost a slow Claude call, and the device stays quiet unless it matters. If unsure or unavailable, Wayfinder carries on without it |
| **Vosk** (small English model) | Turns the recording into text, on the Pi | Offline, private, light enough for a Pi; it only runs when the button is released |
| **ElevenLabs** (Flash voice) + on-device cache | Natural voice; fixed sentences are recorded once and played from the Pi | Clear and pleasant; cached sentences play instantly and offline |
| **espeak-ng** | Backup voice when a sentence isn't recorded and ElevenLabs can't be reached | Tiny and always available |
| **OpenCV** | Measures how far you've turned by comparing camera frames (phase correlation, ~1° accuracy); prepares pictures for Claude and the live view | No compass or extra sensor needed |
| **picamera2 / libcamera** | Runs the camera: full sensor width (16:9), continuous autofocus, short exposure so walking doesn't blur | The Pi's own camera software |
| **gpiozero** (+ lgpio) | Reads the button; drives the motors once fitted | Simple, and supports the Pi 5 |
| **smbus2 + VL53L0X / VL53L1X driver** | Detects and reads the distance sensor once fitted | Only the driver for your chip is installed |
| **sounddevice, PipeWire, BlueZ** | Microphone in; sound out to the Bluetooth earbuds | Works with the digital mic and Bluetooth audio |
| **Python's built-in web server** | The live camera view in a browser (`--stream`) | No extra package; only works while someone is watching |
| **systemd** (user service) | Starts Wayfinder at boot and restarts it if it stops | No screen, keyboard or SSH needed at a demo |
| **Python 3** | All of it | Every library needed exists; quick to build and change |

**Why no YOLO or other model on the Pi?** Finding a door and planning a route needs understanding
the whole room; a fixed detector only labels boxes (and called windows "stairs" in our tests). Without
on-device models, the Pi stays light (73 MB to install, no PyTorch) and cool.

### Code

| File | Role |
|---|---|
| `main.py` | The app: button and voice, JEV routing, guiding loop, turn guidance, overlay; obstacle warning once the sensor is fitted |
| `planner.py` | Claude: survey / ask / plan / arrived / answer, a few steps at a time |
| `jev.py` | JEV: what did they say? Which things need an alert? |
| `motion.py` | How far you turned, from the camera picture |
| `camera.py` | Pi Camera (autofocus, full width, short exposure), webcam, phone, video |
| `voice.py` | Push-to-talk microphone + Vosk |
| `speech.py`, `voices.py` | Speaking: cached ElevenLabs recordings, local voice as backup |
| `liveview.py` | The live camera view in a browser |
| `controls.py` | Button, preview-window keys, typed requests |
| `haptics.py` | The 4 motors and their patterns (planned hardware; simulated until fitted) |
| `distance.py` | Distance sensor, chip detected automatically (planned hardware; does nothing until fitted) |
| `config.py` | Every setting and pin |
| `pi/` | Setup, earbud pairing, mic / camera checks, sensor test, autostart |
| `tools/` | Build the Pi upload folder; record the fixed sentences |
| `tests/` | 27 automated tests with stand-ins for Claude and JEV |
| `docs/` | 90-second explainer video script and pitch deck content |

---

## 6. Features

**In the current build:**

| Do / hear | What happens |
|---|---|
| **Hold** the button, speak, release | A new request ("take me to the exit", "find me a free seat", "where's the counter?") or the answer to a question |
| **Press** the button | The next step. Every 2 steps it takes a new photo and updates the route |
| Say "next", "repeat", "look again", "stop" (or in your own words: "what do I do now", "cancel that") | Same as the names say |
| "Turn right about 90 degrees." … "Keep turning right." … "OK, stop." | Turn slowly; it measures the turn from the camera and says "OK, stop." when you've turned far enough |
| "The chair is right in front of you. Push it to your left." | Move the chair, then press the button: it checks the way is clear |
| "A person on your left, coming toward you…" | A warning JEV decided matters |
| "Sorry, I didn't catch that." | The mic misheard you: say it again |
| "Still looking." | Claude is taking longer than 8 s |
| "The door is right in front of you…" | You've arrived |

**Also:**
- **Survey before planning:** turn, tilt or step aside to see past corners; finds the *nearest* door.
- **Blocker handling:** guides you to a movable chair and tells you how to clear it; never asks you
  to move a person.
- **Natural voice offline** for every fixed sentence.
- **Live view** (`--stream`): a helper, trainer or demo audience sees what the camera sees and the
  sentence spoken, in any browser.
- **Self-checks:** says when the camera is missing or disconnected, when it can't reach the
  internet, or when route planning isn't set up.
- **Starts at boot** with no screen or keyboard.

**Ready in software, waiting for the hardware:** turn-by-vibration, a short pulse on the side of
minor things, three pulses on arrival, and the distance sensor's offline obstacle warning (buzz
under 1 m, "Stop" under 0.5 m) that also tells Wayfinder the exact moment you reach a chair.

**Measured:**

| What | Result |
|---|---|
| Live test: found a glass door past tables, warned it's glass | First answer **4.5 s**, re-check **3.1 s** |
| Survey with one turn (cupboard → glass door) | **8 s** plus turning time, 2 Claude calls |
| JEV decisions | **0.3 s**; caught "uh the the" as misheard (0.98); "what do I do now" → next, "cancel that" → stop |
| On the Pi, in a real classroom | Understood "go to the bathroom"; found an open glass door to a balcony with chairs in front |
| Live view | ~10 pictures a second while watched |

---

## 7. Setup

### On the Raspberry Pi

**1. Get the code onto the Pi** (either way):
- **Clone:** `git clone <repo-url> ~/wayfinder`, then copy your keys from the laptop:
  `scp .env <user>@<PI_IP>:~/wayfinder/` (keys are never in the repository).
- **Or the upload folder** (includes `.env` and the speech model):
  ```powershell
  cd wayfinder
  python tools/make_pi_upload.py            # -> dist\wayfinder   (--no-env leaves the keys out)
  scp -r dist\wayfinder <user>@<PI_IP>:~/
  ```

**2. Set up and test** (on the Pi, Raspberry Pi OS Bookworm 64-bit):
```bash
cd ~/wayfinder
bash pi/setup_pi.sh          # packages, mic driver, speech model; says what's missing
sudo reboot                  # first time only (mic driver)
bash pi/pair_earbuds.sh      # pick the earbuds from the list
bash pi/test_mic.sh          # records 4 s and plays it back
source .venv/bin/activate
python pi/camera_check.py --ask "where is the door?"   # focus, brightness and Claude's answer
python main.py --stream      # run it, with the live view at http://<PI_IP>:8000
bash pi/install_autostart.sh # start at boot (add --stream for the live view)
```
If the picture is upside down, set `PICAM_ROTATE_180 = True` in `config.py`.

**When the distance sensor is fitted:** run `bash pi/setup_pi.sh` once more (it detects the chip
and installs only its driver), then check it with `python pi/test_tof.py`.

**3. Update later:** `cd ~/wayfinder && git pull && systemctl --user restart wayfinder`
(or rebuild and copy the upload folder again).

### Live view
Run with `--stream`, then open **http://<PI_IP>:8000** on a laptop or phone on the same Wi-Fi
(`hostname -I` on the Pi shows the IP). It shows the camera picture with how far the wearer has
turned, the goal and step, the last sentence spoken and what Claude saw (and, once fitted, the
distance ahead and the 4 motors). Anyone on the same network can open it: use a private network.

### API keys (`.env`, never committed)

| Key | For |
|---|---|
| `ANTHROPIC_API_KEY` (+ `ANTHROPIC_WORKSPACE_ID` if the key isn't workspace-scoped) | Claude: seeing and planning (**required**) |
| `TYPESAFE_API_KEY` | JEV (optional: without it, speech goes straight to Claude and nothing extra is announced) |
| `ELEVENLABS_API_KEY` | Natural voice (optional: the local voice is used without it) |

### Try it on a laptop
```powershell
cd wayfinder
python -m pip install -r requirements.txt
copy .env.example .env                                        # add your keys
python main.py --source 0 --show                              # webcam
python main.py --source http://<PHONE_IP>:4747/video --show   # phone camera (DroidCam)
python tests/test_wayfinder.py                                # 27 tests, no hardware or internet needed
```
Type a request in the terminal, or in the preview window press **v** to talk (v again to send),
**n**/space = next step, **l** = look again, **r** = repeat, **s** = stop, **q** = quit.

### What gets installed on the Pi
Only what Wayfinder uses (`pi/setup_pi.sh`):

| Package | For |
|---|---|
| `python3-picamera2`, `python3-opencv`, `python3-numpy` (apt) | Camera, turn measurement, pictures |
| `pipewire-audio`, `wireplumber`, `libspa-0.2-bluetooth`, `bluez` (apt) | Bluetooth earbuds |
| `alsa-utils`, `libportaudio2` (apt); `sounddevice` (pip) | Microphone and playing sound |
| `espeak-ng` (apt) | Backup voice |
| `python3-gpiozero`, `python3-lgpio` (apt) | Button (and the motors, once fitted) |
| `i2c-tools` (apt); `smbus2` (pip) | Finding the distance sensor, once fitted |
| `vl53l1x` **or** `adafruit-circuitpython-vl53l0x` + `adafruit-blinka` (pip) | Only installed once a sensor is connected, and only for its chip |
| `anthropic` (pip) | Claude |
| `typesafe-sdk` (pip) | JEV |
| `vosk` (pip) + its 40 MB English model | Offline speech recognition |

The ElevenLabs voice and the live view use Python's own web tools: no extra package.

---

## 8. Limitations

- **Not yet tested with blind users.** Timings, wording and instructions need their input.
- **No vibration motors or distance sensor yet.** All guidance is spoken, so it uses the wearer's
  ears more than planned, and turning is guided by spoken cues ("Keep turning right", "OK, stop.")
  rather than a vibration. There is **no obstacle warning that works without the internet**: the
  cane is the only protection against what Claude doesn't mention.
- **Needs internet** for Claude (seeing and planning). Without it, Wayfinder says so and can't
  guide. It doesn't yet warn the moment the network drops; you find out at the next request.
- **Answers take seconds:** 3–5 s per look on a good connection; the first Pi run saw 6–29 s
  (pictures are now smaller, and it says "Still looking."; being measured again).
- **It only knows you've reached a chair from the next photo,** so the timing of "the chair is right
  in front of you" is approximate until the distance sensor is fitted.
- **Indoor wayfinding, not street safety.** No traffic warnings. **Keep using the cane.**
- **Distances are estimates** ("about 4 steps"); it re-checks every 2 steps.
- **Speech recognition can mishear** in noisy rooms (Vosk small model). JEV catches clear nonsense,
  not every mistake.
- **Turn measurement** needs a textured view; a blank wall or fast turning can confuse it.
- **English only.**
- **Privacy:** photos go to Claude during a request (nothing is stored on the device); JEV gets text
  only. The live view is reachable by anyone on the same network while it's on.
- **Cost:** about $0.01–0.02 per Claude look; a trip is a few looks.

---

## 9. Future scope

1. **Fit the vibration motors** (software ready): turn by touch instead of words, a short pulse on
   the side of minor things, three pulses on arrival. Parts: 4 phone motors, 4 NPN transistors,
   resistors, diodes, a LiPo and a TP4056 charger.
2. **Fit the distance sensor** (software ready): an obstacle warning that works with no internet
   (buzz under 1 m, "Stop" under 0.5 m), and the exact moment you reach a chair to move.
3. **Test with blind users** and tune the timing, wording and vibration patterns with them.
4. **Faster answers:** smaller pictures, streaming the reply, and caching the instructions, to bring
   each look under 3 s on the Pi.
5. **Better speech recognition:** a cloud speech-to-text (e.g. ElevenLabs) when online, Vosk when
   offline.
6. **Network alerts:** "Internet lost" / "Internet is back" the moment it happens.
7. **More safety sensing:** a second distance sensor pointing down for steps and drops; one at head
   height.
8. **Remember familiar buildings:** keep what was seen, so the second visit is faster and needs less
   internet.
9. **Offline fallback:** a small on-device detector for "door ahead" / "person ahead" when there's no
   internet.
10. **More languages,** starting with Malayalam and Hindi.
11. **A wearable build:** one compact case, a single battery, a haptic belt or vest.
12. **Pilots** with a blind school, college or hospital.
