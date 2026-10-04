# SENSE Wayfinder: pitch deck content

**Format:** the standard pitch order (title, problem, solution, demo, how it works, proof,
market, competition, business model, roadmap, team, ask). 12 slides, about 5 minutes.
Each slide has: the **headline** (one message), **on the slide** (keep it short),
**speaker notes** (what you say) and a **visual** suggestion.

Every number comes from our own tests unless marked *(check)*. Placeholders are in [brackets].

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
2. **It looks around:** "Turn right about 90 degrees" (a vibration on your right until you face it)
3. **It plans the walkway:** "Walk about 3 steps. The tables will be on your left."
4. **It clears the way:** "The chair is right in front of you. Push it to your left."
5. **You arrive:** "The door is right in front of you. The handle is on the right."

**Speaker notes:** "Wayfinder works like a sighted friend: it looks around first, finds the
nearest door, works out how far the way is clear, and if a chair is blocking it, tells you how to
move it. Press the button for the next step. Every two steps, it looks again."

**Visual:** five numbered frames from the demo video.

---

## 5. Demo

**Headline:** Watch it find the door

**On the slide:** the 90-second explainer video, or a live demo.

**Speaker notes:** "In our test, Wayfinder started facing a cupboard. It said there was no exit
in view and asked the user to turn right. It found a glass door about 5 steps away, warned that
it's glass, and routed around the tables. 8 seconds, plus the time to turn."

**Visual:** the video, full screen. Keep a backup recording in case the live demo fails.

---

## 6. How it works

**Headline:** Claude sees. The body feels. Safety stays on the device.

**On the slide**

| Part | Job |
|---|---|
| Chest camera | Claude's eyes; also measures how far you've turned (to about 1°) |
| Claude (Anthropic) | Understands the room, picks the nearest door, plans the route |
| Distance sensor | Buzzes under 1 m, says "Stop" under 0.5 m. **No internet, no AI** |
| 4 vibration motors | Left / right = which way to turn; front = something close |
| Button + offline speech recognition | Hold to speak, press for the next step |
| Earbuds | A natural voice, recorded once and stored on the device |

**Speaker notes:** "The hard thinking happens in Claude, so the device itself is a Raspberry Pi
with no AI models on it. The safety part doesn't depend on the internet: the distance sensor
warns you even if Claude is unreachable."

**Visual:** a block diagram: camera → Claude → earbuds + motors; distance sensor → motors.

---

## 7. Design principles

**Headline:** Built around how blind people actually move

**On the slide**
- **Quiet by default:** ears stay free for the room; only instructions are spoken
- **Touch for direction:** vibration says which way to turn, so no extra words
- **Hands free:** one button, no phone in hand
- **Honest:** says when it's unsure; never says a path is "safe"
- **Respectful:** never asks you to move a person or someone's wheelchair

**Speaker notes:** "Research with white-cane users found sound feedback took far more mental
effort than vibration, so direction is felt, not spoken."

**Visual:** a body outline showing the 4 motor positions.

---

## 8. Where we are

**Headline:** Built, tested, and on the hardware

**On the slide**
- Live tests: found a glass door past tables; first answer in **4.5 s**, re-checks in **3.1 s**
- Survey with one turn: **8 s** plus turning time
- Running on a Raspberry Pi 5 with the camera, mic and button; first run done, fixes shipped
- 19 automated tests; device software is 73 MB, with no AI models on the device
- **Not yet tested with blind users:** that's our next step

**Speaker notes:** "We're honest about what's proven. The software works, the hardware runs it,
and we've measured the timing. What we haven't done yet is the most important part: testing with
blind users."

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
- Parts: about ₹11,000–13,000 *(check current prices)*: Raspberry Pi 5, Camera 3, mic, distance
  sensor, 4 phone vibration motors, button, battery
- Running cost: about $0.01–0.02 per Claude look; a typical trip is a few looks
- Model ideas: a device + low monthly plan; or institutions (colleges, hospitals, blind schools)
  buy units to lend

**Speaker notes:** "The parts cost about the same as a mid-range phone, and the AI costs a few
cents per trip. A dedicated device can get much cheaper at volume."

**Visual:** a parts photo with prices; a coin icon for per-trip cost.

---

## 11. Roadmap

**Headline:** From prototype to daily use

**On the slide**
1. **Now:** test with blind users; tune timing and instructions with them
2. **Next:** faster answers; better speech recognition in noisy rooms; a downward sensor for steps and drops
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
  the distance sensor only sees straight ahead (not drops or steps going down)
- **Privacy:** pictures go to Claude only during a request; nothing is stored on the device
- **Safety:** the distance warning works offline; Wayfinder never says a path is safe;
  it works with the cane, not instead of it
- **Wiring and parts list:** see the README
