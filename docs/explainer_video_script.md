# SENSE Wayfinder: 90-second explainer video

**Goal:** in 90 seconds, a viewer understands the problem, sees Wayfinder guide someone to a door,
and remembers one line: *hold the button, say where, get guided there.*

**Format:** problem → solution → demo → how it works → call to action.
**Length:** about 210 words of voice-over (normal speaking pace, ~145 words a minute).
**What it shows:** only what Wayfinder does today: the chest camera, the button, the microphone and
spoken guidance in the earbuds.
**Make the video accessible too:** many viewers will be blind or low-vision. The voice-over
describes what's on screen, there are no "as you can see" lines, and every shot has captions.

---

## Script

| Time | Shot (what we see) | Voice-over | On-screen text |
|---|---|---|---|
| **0:00–0:07** HOOK | Close-up, eye level: a white cane taps across a busy room. Cut to the person standing still, head tilted, listening. | "You're in a room you've never been in. You need the way out. Where is it?" | — |
| **0:07–0:20** PROBLEM | Wide shot: chairs, tables, a glass door at the far side. The cane finds a chair leg; the person stops. | "For a blind person, every new room is a puzzle. A cane finds what's at your feet, not where the door is. GPS doesn't work indoors. Apps describe a photo, not the way there." | — |
| **0:20–0:28** SOLUTION | The person holds a small button on their chest strap. Close-up of the wearable: camera, button, earbuds. | "This is SENSE Wayfinder. Hold the button. Say where you want to go." | **SENSE Wayfinder** · Hold. Say. Go. |
| **0:28–0:40** DEMO 1: LOOK | Person says "Take me to the exit." A soft beep. Person turns right, slowly, and stops. | "It looks through a camera on your chest. If the door isn't in view, it asks you to turn, measures the turn, and tells you when to stop." | "Turn right about 90 degrees." · "OK, stop." |
| **0:40–0:52** DEMO 2: ROUTE | Person walks slowly; tables pass on their left. Someone walks toward them from the left. They press the button; new instruction. | "Then it gives the route, a few steps at a time, and warns you only when it matters: 'A person on your left, coming toward you.' Every two steps, it looks again." | "Walk about 3 steps." · "A person on your left, coming toward you." |
| **0:52–1:02** DEMO 3: BLOCKER | A chair blocks the walkway. The person reaches it and pushes it aside. | "A chair in the way? It walks you up to it, and tells you how to clear it: 'Push the chair to your left.'" | "Push the chair to your left." |
| **1:02–1:08** ARRIVED | Hand reaches the door handle. | "And when you're there, it tells you where the handle is." | "The handle is on your right." |
| **1:08–1:20** HOW IT WORKS | Simple animation: mic → JEV → Claude ← camera; Claude → earbuds. Picture-in-picture: the live view of what Wayfinder sees. | "Claude, an AI that understands images, sees and plans. JEV, a fast decision engine, checks what you said and what's worth a warning. All you need is one button and your earbuds." | Camera · Claude · JEV · Earbuds |
| **1:20–1:30** CLOSE + CTA | The person walks out through the door into daylight. End card. | "SENSE Wayfinder. We don't give you eyes. We give you another way to find your way. Help us test it with blind users." | **SENSE Wayfinder** · Built at Jugaad Junction · [contact / link] |

---

## Shot list

| # | Shot | Notes |
|---|---|---|
| 1 | Cane tapping, close-up, low angle | Natural room sound, no music for the first 3 s |
| 2 | Person standing, listening | Shallow focus on the face |
| 3 | Wide room: chairs, tables, glass door far side | Use the real test room |
| 4 | Close-up of the wearable on the chest | Camera, button and earbuds clearly visible |
| 5 | Thumb holding the button + beep | Record the real beep |
| 6 | Person turning right, slowly, then stopping | Over-the-shoulder; on-screen text "OK, stop." when they stop |
| 7 | Walking past tables; someone approaches from the left; button press | Steady, slow walk |
| 8 | Chair in the walkway; person pushes it left | On-screen text "Push the chair to your left." |
| 9 | Hand finds the door handle | Close-up |
| 10 | Animation: how it works | Mic, JEV, camera, Claude, earbuds; picture-in-picture of the live view |
| 11 | Walking out into daylight | Wide, from behind |
| 12 | End card | Name, tagline, link, hackathon logo |

## Production notes

- **Use real device audio** for the beeps and Wayfinder's own voice. The on-screen text shows the
  same sentences it speaks.
- **Record the live view at the same time.** Run `python main.py --stream` and screen-record
  `http://<PI_IP>:8000` on a laptop while filming. It shows exactly what the camera sees and the
  sentence spoken: picture-in-picture footage, and proof the demo is real.
- **Captions on every shot.** Add an audio-described version if it's used for blind audiences
  (the voice-over already covers most of it).
- **Music:** soft and low under the voice-over; quiet during device speech.
- **Be honest on screen.** Show a real run; if a sentence is re-recorded, keep its words the
  same as the device says. Film indoors: it's built for indoor wayfinding.
- **Cast:** if possible, a blind or low-vision person, with their consent and input on the script.
