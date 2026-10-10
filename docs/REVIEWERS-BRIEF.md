# Where is this wrong?

**A one-page brief for historians. September 2026.**

---

## What this is

We are designing a database for Islamic history. It is not built yet.

This page explains the one idea behind it. Then it asks you whether that idea is sound.

We are not asking you to approve a finished thing. We are asking you to find the mistakes while they are still cheap to fix.

---

## The problem we are trying to solve

Almost every digital history project stores **facts**, and adds sources as footnotes:

> The Hijrah took place in Rabīʿ al-Awwal, year 1. *(Source: Ibn Hishām)*

This looks fine. But four things are lost, and they cannot be recovered later:

1. **When two reports disagree, somebody has to choose one.** The database never records that a choice was made, or who made it.
2. **A grading has nowhere to live.** You do not grade a fact. You grade a report. If the report is not stored as an object, the grading has nothing to attach to.
3. **The time gap disappears.** A claim about year 1, first written down in year 220, is not the same kind of claim as one written down in year 90. The flat model cannot show the difference.
4. **Correcting it means rewriting history.** Not re-deriving it.

---

## What we propose instead

Store the **report** — the *khabar*, with its chain. Build everything else from it.

```
Report (khabar)  →  chain  →  narrators (with dates and places)
     ↓
  claim  →  about a person, event, place or relationship
     ↓
  graded by  →  a named authority, in a named book, at a named page
     ↓
  the history the reader sees  ←  a RESULT, not an entry
```

The reader still sees "the Hijrah took place in Rabīʿ al-Awwal, year 1." But that sentence is now a **result**. The reports are still underneath it. Change a grading, and the result changes. Nobody rewrites the history, because the history was never typed in.

---

## What this means for your work

**Your grading stays yours.** There is no "grade" field on a report anywhere in this system. There is only: *this scholar, in this book, at this page, gave this grade, for this reason.* Another scholar's different grading sits next to it. Neither one erases the other.

**Disagreement is kept, not settled.** Three reports name three different people who brought food to the cave. All three stay, with their evidence. The system does not choose, and it does not assume the three answers rule each other out.

**Sīra is not forced into ḥadīth categories.** Much of the sīra-maghāzī material was never meant to meet ḥadīth criteria. It has its own category. It is neither dismissed nor promoted.

**Different traditions keep different scales.** Sunni, Twelver Shia, Ibadi and academic assessments each use their own vocabulary. The system is *forbidden* from converting between them or averaging them into one number.

---

## What the system refuses to do

This is the part most worth checking, because refusals are where a system's honesty actually lives.

| It will not | Why |
|---|---|
| Decide whether a chain is connected | *Muttaṣil* or *munqaṭiʿ* is your call, not a machine's |
| Grade anything | It records gradings made by people |
| Guess a date, place or route | An unknown stretch of the Hijrah route is drawn as a gap, not a smooth line |
| Merge two similar names into one person | Automatic matching may only *suggest*. A person decides, and signs it |
| Rank Companions by any calculation | Not offered as a feature, in any form |
| Let AI publish | AI reads texts and proposes. A qualified person must accept it, and their name stays on it permanently |

Here is the clearest example, taken from our worked file. A chain of five links. For each link, the system checks whether those two men could actually have met — their dates, their cities. All five come back **plausible**.

And then the field for "is this chain connected?" is left **empty**, marked *awaiting a scholar*.

The machine gathered everything you would want. Then it stopped. That is the whole design in one picture.

---

## Where you would come in

The specification marks **twenty decisions it refuses to make on its own**. For example:

- Is this chain connected?
- Is this man's companionship established, or disputed?
- Are these two names one narrator, or two?
- Which calendar conversion applies to this region and century?
- Does including a report in a *Ṣaḥīḥ* collection count as an explicit grading?
- In this *mawlā* tie, who is the patron and who is the client? The sources often do not say, and it must never be guessed from the order of names.

What you decide is recorded under your name, permanently. It stays open to revision by whoever comes after you. It can be cited.

---

## What is actually finished

Being plain about this matters more than impressing you.

- **The data model:** written, and machine-checkable. 1,804 statements. It validates.
- **The historical data:** almost none. One example event, and it is clearly marked as unverified.

That order is deliberate. If we gathered data first and designed the model afterwards, the model would be shaped by whatever we happened to collect — and every mistake above would already be baked in.

---

## What we are asking

**Tell us where this is wrong.**

Section 14 of the specification already lists eight places *we* think it is wrong — including whether we have picked the right standard class for a report, and whether a single report can really be given one ascription when its text mixes prophetic material with a narrator's own comment.

If you would rather look at one file than read a specification, read [the worked example](../ontology/examples/thawr.ttl). It is one event, modelled all the way down: the chain, the grading, an unresolved dispute, and a route segment that admits it is guessing.

---

*Full specification: [docs/02](02-knowledge-architecture.md). Ontology, constraints and validator: [`ontology/`](../ontology/). Nothing here is fixed. All naming, and every scholarly policy, is provisional until a review board exists.*
