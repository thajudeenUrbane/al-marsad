# Sound policy: options for the scholars

**Status:** draft for decision, 17 October 2026. Part of the aniconic design grammar (`GRAMMAR.md` §3.11).
**Decision needed:** the scholars' board chooses one of the three policies in §2 (or amends one). Until they decide, **Policy A applies**.

## 1. Fixed rules (apply under every policy)

1. **No musical instruments.** The relied-upon position in the four schools prohibits instruments, with the duff as the recognised exception. No synthesiser pads, drones built from tuned tones, strings, flutes, percussion loops or "cinematic" scores, including in trailers, loading screens and social media cuts.
2. **No voice for the Prophet ﷺ.** No actor, synthetic voice, or vocal effect ever speaks as him. His words are only ever *reported*: a narrator reads "He ﷺ said: …" in the third person, from a sourced text.
3. **No first-person voice for the Companions, his family, or the other prophets عليهم السلام.** Their words are reported by a narrator in the third person ("Abū Bakr رضي الله عنه said: …"). No dramatised dialogue, no sound of their breathing, footsteps, or movement as a character.
4. **No synthetic speech for sacred text.** Qurʾān recitation is always a credited human reciter with a recognised ijāza or an established public recording, under licence. Hadith and sīra passages, if voiced, are human-read (Policy B).
5. **No dramatised violence.** No clash of swords, screams, impacts or crowd panic at battles. A battle is marked by silence or a lowered ambience.
6. **Provenance.** Every sound file carries: what it is, who recorded or recited it, where and when, licence, and (for passages) the source and edition. Shown in the credits panel and reachable from the moment it plays.
7. **Respect.** Qurʾān audio never plays under other sound, never loops as background, never fades out mid-āya, and never plays while the reader is scrolling a game-like interaction. Playback starts only on the reader's action.
8. **Controls.** Every sound has a visible mute; there is a global "silence" switch; captions or a transcript exist for all speech.

## 2. The three policies

### Policy A: ambience only (default)

- Natural, recorded field sound: night desert wind, distant camels, a well rope, palm fronds, cicadas, a dawn call to prayer from a contemporary recording (credited) only at the point where the narrative reaches the institution of the adhān, if the scholars allow it.
- Human narration in the reader's language for orientation (third person, from the reviewed narrative text).
- **Pros:** least contestable; simplest to license.
- **Cons:** emotionally reserved; passages are read silently.

### Policy B: A + human recitation of source passages

- Adds: Qurʾānic āyāt relevant to the moment (recited, credited), and human readings of the Arabic of hadith and sīra passages the reader has opened, followed by the translation read by the narrator.
- Readers of hadith and sīra are not actors performing a role; they read the text as text, with the isnād.
- **Pros:** the sources speak; aids memory and Arabic learning.
- **Cons:** licensing and reader vetting; must avoid any sense of dramatisation.

### Policy C: B + nashīd without instruments

- Adds: voice-only nashīd (unaccompanied, or with duff only if the board explicitly allows it), used sparingly at thresholds (entering Madina, the end of a journey). Texts must be vetted for content (no exaggeration about the Prophet ﷺ, no claims not in the sources).
- Explicitly **excludes**: vocal processing that imitates instruments (vocoders, "voice-only" pads built to sound like strings), backing tracks, and beat-boxing.
- **Pros:** warmth, especially for children.
- **Cons:** most contested; the duff question, the content of lyrics, and the risk of music-like production need a ruling.

**Question for the board:** A, B or C? If C, is the duff allowed, and in which contexts (e.g. only where the sources record it, such as the welcome at Madina, itself a report with a disputed chain)?

## 3. Recording specifications

| Item | Spec |
|---|---|
| Capture | 48 kHz / 24-bit WAV, minimum |
| Ambience | spatial capture (first-order ambisonics or ORTF stereo) on location in the Ḥijāz where permitted; otherwise licensed libraries with location metadata (no "generic desert" from other continents presented as the Ḥijāz) |
| Binaural / spatial | ambisonic master, binaural render for headphones (the *Notes on Blindness* approach: people are present as sound of narration and place, never as bodies) |
| Voice | dry, close-mic (large diaphragm, 20–30 cm), treated room, no reverb baked in |
| Loudness | dialogue −23 LUFS integrated (EBU R128) on web, −16 LUFS for mobile podcast exports; ambience 12–18 dB under dialogue; true peak ≤ −1 dBTP |
| Qurʾān | supplied masters unprocessed except loudness normalisation; no EQ "sweetening", no added reverb, no time-stretching |
| Delivery | Opus 96 kb/s (web), AAC 192 kb/s (iOS), plus archival WAV |
| Metadata | per file: id, title (ar/en), performer, role (reciter/reader/narrator/field), source passage id, edition, licence, recording date, location |
| Captions | WebVTT, Arabic and English, timed to the āya or sentence |

## 4. Voice casting norms

- **Narrators:** one consistent narrator per language; calm, unhurried, not theatrical. Adults for the main narration; children's editions may use a gentle narrator, never child voices speaking as historical children.
- **Reciters:** credited reciters with recognised recitation (ijāza preferred); riwāya stated (e.g. Ḥafṣ ʿan ʿĀṣim).
- **Readers of Arabic passages:** readers with sound Arabic and tajwīd-informed pronunciation; they read, they do not act.
- **Women's voices:** whether women narrate for mixed audiences is a question for the board; the default is male narrators for mixed audiences and a female-narrated track available for women-and-children settings if the board allows it.
- **No celebrity casting** that pulls attention to the voice; no impersonation; no synthetic voice clones of real reciters.
- **Synthetic voice:** allowed only for interface feedback ("Opened: Badr, 2 AH") if the board permits; never for narration of sources, never for the Qurʾān.
- **Consent and contracts:** every performer signs a release naming the platform's rules (no re-use for dramatisation, no AI training).

## 5. What is never voiced

- The Prophet ﷺ, in any form.
- Any Companion, member of his family, or other prophet, in the first person.
- Angels, Jibrīl عليه السلام, or the unseen, in any form (no "voice from above").
- Opponents in the first person (to avoid a voiced villain against an unvoiced Prophet ﷺ).
- Any text not in the reviewed sources, including AI-written summaries presented as narration of the sources.

## 6. Precedents and how we differ

- *The Message* (1976): kept the Prophet ﷺ off screen and unheard, but voiced Companions as characters. We keep the first and not the second.
- *Notes on Blindness* (VR): people present through binaural sound and particles of light; our model for presence without figures.
- *Never Alone*: community voices tell their own tradition; our model for narration owned by scholars and reciters, not by actors.
