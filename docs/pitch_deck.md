# SENSE Wayfinder: pitch deck content

**Format:** the standard pitch order (title, problem, solution, demo, how it works, proof,
market, competition, business model, roadmap, team, ask). 12 slides, about 5 minutes.
Each slide has: the **headline** (one message), **on the slide** (keep it short),
**speaker notes** (what you say) and a **visual** suggestion.

Every number comes from our own tests unless marked *(check)*. Placeholders are in [brackets].
**Last updated:** 4 October 2026: adds JEV, the live camera view and the first Raspberry Pi run.
**Current build:** Raspberry Pi 5, camera, microphone, button, Bluetooth earbuds. **Vibration motors
and the distance sensor are planned** (software written, hardware not fitted yet).

---

## 1. Title

**Headline:** SENSE Wayfinder

**On the slide**
- Hold the button. Say where you want to go. Get guided there.
- A wearable indoor guide for blind people
- [Team name] · Jugaad Junction hackathon (Tinkerhub × Superhuman Lab)

**Speaker notes:** "We built a wearable that guides a blind person to a place they can't see
(a door, the exit, a seat) one step at a time."

**Visual:** the wearable on a person's chest; one clean product photo.

---

## 2. The problem

**Headline:** Every new room is a puzzle

**On the slide**
- A cane finds what's at your feet, not where the door is
- GPS doesn't work indoors
- Description apps say "there's a door", not how to reach it
- A phone needs a free hand, and the cane already has one

**Speaker notes:** "Imagine walking into a classroom you've never seen and needing the way out.
A white cane tells you about the chair leg in front of you. It can't tell you the door is
behind you on the right, past three tables. Today, the answer is: ask someone."

**Visual:** a top-down sketch of a room: a person, tables, chairs, a door, and a question mark.

---

## 3. Who it's for

**Headline:** Blind and low-vision people who get around on their own

**On the slide**
- About 43 million blind people worldwide *(check: WHO / Lancet 2020)*
- About 5 million blind people in India *(check: National Blindness & Visual Impairment Survey 2019)*
- Indoors: offices, colleges, hospitals, stations, shops: places that change and have few signs

**Speaker notes:** "Our users already move independently with a cane. They don't need a device
that talks all the time. They need help at the moment of 'where is it?'"

**Visual:** three icons: college, hospital, office.

---

## 4. The solution

**Headline:** A guide that looks, plans and walks you there

**On the slide**
1. **Hold** the button: "Take me to the exit"
2. **It looks around:** "Turn right about 90 degrees" (it measures your turn from the camera)
3. **It plans the walkway:** "Walk about 3 steps. The tables will be on your left."
4. **It warns only when it matters:** "A person on your left, coming toward you." Minor things are left out
5. **It clears the way:** "The chair is right in front of you. Push it to your left."
6. **You arrive:** "The door is right in front of you. The handle is on the right."

**Speaker notes:** "Wayfinder works like a sighted friend: it looks around first, finds the
nearest door, works out how far the way is clear, and if a chair is blocking it, tells you how to
move it. Press the button for the next step. Every two steps, it looks again. Along the way it
doesn't talk about everything it sees: only what you need, like someone walking toward you."

**Visual:** six numbered frames from the demo video.

---

## 5. Demo

**Headline:** Watch it find the door

**On the slide:** the 90-second explainer video, or a live demo with the **live view** on the
projector: the audience sees what the camera sees and the sentence it speaks.

**Speaker notes:** "In our test, Wayfinder started facing a cupboard. It said there was no exit
in view and asked the user to turn right. It found a glass door about 5 steps away, warned that
it's glass, and routed around the tables. 8 seconds, plus the time to turn. On the Raspberry
Pi, in a real classroom, it found an open glass door to a balcony, with chairs in front of it."

**Visual:** the video, full screen, or the live view (`python main.py --stream`, then open
`http://<PI_IP>:8000`). Keep a backup recording in case the live demo fails.

---

## 6. How it works

**Headline:** Claude sees. JEV decides fast. You hear only what matters.

**On the slide**

| Part | Job |
|---|---|
| Chest camera | Claude's eyes; also measures how far you've turned (to about 1°) |
| Claude (Anthropic) | Understands the room, picks the nearest door, plans the route |
| JEV (TypeSafe) | In 0.3 s: was that a request, a command, or misheard words? Which things Claude saw need a spoken warning, or nothing? |
| Button + offline speech recognition | Hold to speak, press for the next step |
| Earbuds | Every instruction, in a natural voice recorded once and stored on the device |
| *Next:* 4 vibration motors | *Left / right = which way to turn; front = something close (software ready)* |
| *Next:* distance sensor | *Buzz under 1 m, "Stop" under 0.5 m, with no internet and no AI (software ready)* |
| Live view | A helper, trainer or judge sees what Wayfinder sees, in any browser |

**Speaker notes:** "Two AIs, each doing what it's best at. Claude does the slow, hard thinking:
understanding the room and planning. JEV makes quick decisions in a third of a second: if the
microphone misheard you, it says so at once instead of wasting a 5-second look; and it decides
which things are worth a warning, so the device stays quiet. The device itself is a Raspberry
Pi with no AI models on it. Next we're fitting vibration motors, so direction is felt instead of
spoken, and a distance sensor, so there's an obstacle warning that works without the internet.
The software for both is already written."

**Visual:** a block diagram: mic → JEV → Claude; camera → Claude → JEV → earbuds; motors and
distance sensor shown faded, labelled "next".

---

## 7. Design principles

**Headline:** Built around how blind people actually move

**On the slide**
- **Quiet by default:** ears stay free for the room; only instructions and real warnings are
  spoken (JEV leaves minor things out)
- **Touch for direction (next):** with the motors fitted, vibration will say which way to turn,
  so fewer words
- **Hands free:** one button, no phone in hand
- **Honest:** says when it's unsure; never says a path is "safe"
- **Respectful:** never asks you to move a person or someone's wheelchair

**Speaker notes:** "Research with white-cane users found sound feedback took far more mental
effort than vibration. That's why our next hardware step is vibration motors, so direction is
felt, not spoken."

**Visual:** a body outline showing the 4 planned motor positions.

---

## 8. Where we are

**Headline:** Built, tested, and on the hardware

**On the slide**
- Live tests: found a glass door past tables; first answer in **4.5 s**, re-checks in **3.1 s**
- Survey with one turn: **8 s** plus turning time
- JEV decisions: **0.3 s**; catches misheard speech and commands said another way
  ("what do I do now" = next step, "cancel that" = stop)
- **On the Raspberry Pi 5** with the camera, mic, button and earbuds, in a real classroom:
  understood "go to the bathroom" and found an open glass door. The first run showed what to fix
  (the voice, slow answers); fixes shipped, second run next
- **Vibration motors and distance sensor:** software written and tested; hardware not fitted yet
- 27 automated tests; device software is 73 MB, with no AI models on the device
- **Not yet tested with blind users:** that's our next step

**Speaker notes:** "We're honest about what's proven. The software works, it runs on the
hardware, and we've measured the timing. On the Pi's first run, answers were slower than on the
laptop (6 to 29 seconds), so we made the pictures smaller and added a 'Still looking' message:
we're measuring that again now. What we haven't done yet is the most important part: testing
with blind users."

**Visual:** a photo of the Pi build and a short checklist with ticks and one open box.

---

## 9. Competition

**Headline:** Others describe. Wayfinder guides.

**On the slide**

| | Describes what's there | Guides you step by step | Hands-free | Needs a person |
|---|---|---|---|---|
| White cane | At your feet | — | — | No |
| Phone apps (e.g. Seeing AI, Be My AI) | Yes | — | No | No |
| Video call to a volunteer (e.g. Be My Eyes) | Yes | Yes | No | **Yes** |
| Smart glasses (e.g. Envision, OrCam) | Yes | Limited | Yes | No |
| **SENSE Wayfinder** | Yes | **Yes** | **Yes** | **No** |

*(check each product's current features before presenting)*

**Speaker notes:** "Apps and glasses tell you what's in a photo. A volunteer can guide you, but
that needs a person on a call. Wayfinder plans and guides, hands-free, without another person."

**Visual:** the table, with the Wayfinder row highlighted.

---

## 10. Cost and business model

**Headline:** Affordable hardware, pennies per trip

**On the slide**
- Parts now: Raspberry Pi 5, Camera 3, mic, button, power bank (earbuds already owned)
- Planned parts: 4 phone vibration motors with transistors, a LiPo and charger, a distance sensor
- Total with the planned parts: about ₹11,000–13,000 *(check current prices)*
- Running cost: about $0.01–0.02 per Claude look; a typical trip is a few looks; JEV checks
  are small text-only calls *(check JEV pricing)*
- Model ideas: a device + low monthly plan; or institutions (colleges, hospitals, blind schools)
  buy units to lend

**Speaker notes:** "The parts cost about the same as a mid-range phone, and the AI costs a few
cents per trip. A dedicated device can get much cheaper at volume."

**Visual:** a parts photo with prices; a coin icon for per-trip cost.

---

## 11. Roadmap

**Headline:** From prototype to daily use

**On the slide**
1. **Now:** fit the vibration motors and the distance sensor (software ready); test with blind
   users and tune timing and instructions with them
2. **Next:** faster answers on the Pi; better speech recognition in noisy rooms; an alert when the
   internet drops; a downward sensor for steps and drops
3. **Then:** a smaller, wearable case and battery; pilots with a blind school or college
4. **Later:** remember familiar buildings, so the second visit is faster and works with less internet

**Speaker notes:** "Our first step isn't more features. It's putting this in the hands of blind
users and building it with them."

**Visual:** a timeline with four steps.

---

## 12. Team and ask

**Headline:** Help us test it

**On the slide**
- Team: [name, role] · [name, role] · [name, role]
- We're looking for:
  - **Blind and low-vision testers** and organisations to pilot with
  - **Mentors** in assistive technology and hardware
  - **Support** to build 10 test units *(set your number)*
- [Contact] · [Link to the video]

**Speaker notes:** "We don't give you eyes. We give you another way to find your way. We're
looking for people to test it with, and partners to take it further. Thank you."

**Visual:** team photos; a QR code to the video or contact.

---

## Appendix slides (for questions)

- **Limits:** needs internet for planning; indoor only; not for traffic; distances are estimates;
  no offline obstacle warning until the distance sensor is fitted, and even then it will only
  see straight ahead (not drops or steps going down)
- **Privacy:** pictures go to Claude only during a request; nothing is stored on the device.
  JEV only gets short text (what was said, a list of things seen), never pictures. The live view
  is off unless started, and only reachable on the local network
- **If the cloud fails:** without JEV, speech goes straight to Claude; without Claude, Wayfinder
  says it can't plan right now (the cane remains the safety tool until the distance sensor is
  fitted)
- **Safety:** Wayfinder never says a path is safe; it works with the cane, not instead of it.
  There's no offline obstacle warning yet: that comes with the distance sensor (software ready)
- **Wiring and parts list:** see the README
