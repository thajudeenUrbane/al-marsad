# Moments trial: Ibn Hishām, Hijrah sections S0678–S0703

**Status: proposed, unreviewed.** An AI extraction trial. Nothing here is asserted; every row waits for a scholar.

## Proposed schema (for `ontology/marsad.ttl`, epistemic layer)
```turtle
mrs:Moment a owl:Class ; rdfs:subClassOf mrs:Assertion ;
    rdfs:comment "Reified narrative beat: what the source says happened, in its order. The claim is that the passage narrates it, never that it happened."@en .
mrs:momentSeq      a owl:DatatypeProperty ; rdfs:domain mrs:Moment ; rdfs:range xsd:positiveInteger .
mrs:momentAction   a owl:DatatypeProperty ; rdfs:domain mrs:Moment ; rdfs:range xsd:string .    # English gloss, not a translation
mrs:momentKind     a owl:ObjectProperty   ; rdfs:domain mrs:Moment ; rdfs:range mrs:MomentKind . # event|speech|state|quran_citation|poem
mrs:momentActor    a owl:ObjectProperty   ; rdfs:domain mrs:Moment ; rdfs:range mrs:Participation . # n-ary: speaker, addressee, agent
mrs:momentPlace    a owl:ObjectProperty   ; rdfs:domain mrs:Moment ; rdfs:range mrs:Place .
mrs:momentTimeCue  a owl:DatatypeProperty ; rdfs:domain mrs:Moment ; rdfs:range xsd:string .    # as the text gives it; dating is a separate claim
mrs:momentHedge    a owl:DatatypeProperty ; rdfs:domain mrs:Moment ; rdfs:range xsd:string .    # yuqāl, fīmā yadhkurūn, yazʿumūn
mrs:followsMoment  a owl:ObjectProperty   ; rdfs:domain mrs:Moment ; rdfs:range mrs:Moment .     # cross-passage narrative order
mrs:MomentKind a owl:Class ; rdfs:subClassOf skos:Concept .
```
Each Moment carries `mrs:locatedIn` (passage), a span [start,end) relative to the passage, `span_sha256`, a Voice (Ibn Isḥāq / Ibn Hishām), `mrs:assertionStatus mrs:as_proposed`, and provenance to the extraction activity. Only a ReviewDecision may change its status (RD4).

## Counts
- 21 sections have passages (S0682, S0684, S0687, S0689, S0690 are absent from the passages file). All 21 passage hashes and the source sha256 were verified.
- **80 moments** in 20 sections (S0695 is a one-line lineage note: 0). event 38, speech 26, state 11, qurʾān-citation 3, poem 2; 6 hedged; 12 with a chain note.
- Every quote is an exact, unique substring of its section (script check).
- Actors: 30 distinct; 21 reuse claim-file names verbatim; 9 have no entity (Jibrīl, Iblīs, collectives such as Quraysh, the watchers, the Anṣār, and four unnamed people).

## What moments recover that the claims missed
The same sections hold 134 claims; 81 (60%) are genealogy, isnād or kinship.
- **S0680 (the night)**: 3 claims; 11 moments (Jibrīl's warning; the watch at ʿatama; ʿAlī in the bed in the green Ḥaḍramī cloak; Abū Jahl's taunt; the handful of dust; the blinding; Yā Sīn 36:9; the passer-by; ʿAlī mistaken for the Prophet; ʿAlī rising at dawn).
- **S0679 (Dār al-Nadwa)**: 14 `present_at` rows but no debate; moments give the three proposals, the elder's rejections and the consensus.
- **S0683–S0688**: the midday visit; "al-ṣuḥba"; Abū Bakr weeping for joy; hiring the guide; the back door; the cave logistics; Asmāʾ's waistband; the Prophet paying for the camel.
- **S0692–S0694**: Abū Quḥāfa and the stones; Surāqa's lots, stumbling horse and written token; his Islam at al-Jiʿrāna.
- **S0700–S0703**: ʿAlī returning the deposits; Sahl's broken idols; founding the Qubāʾ mosque; the first Friday at Rānūnāʾ.
- **Time cues** the claims lack: ʿatama, al-hājira, three days, 12 Rabīʿ I Monday at forenoon, Monday–Thursday, Friday.

## Difficulties
- The raw text has `~~` line continuations, `#` marks, `msNNN` milestones and `PageVxxPyyy` markers inside sentences; a normalised view with an offset map is needed.
- Granularity: Surāqa's cycle is told three times and recorded once; the S0696 stations are one beat.
- S0691 opens mid-story; Umm Maʿbad and the jinnī's verses are in the missing S0689–S0690.
- The guide is split in the claims: ʿAbd Allāh b. Urayqiṭ (S0683, S0691) vs ʿAbdullāh b. Arqaṭ (S0696).
- Unnamed speakers, collectives and non-human agents have no entity type.
- Voice: Ibn Hishām's additions must not be credited to Ibn Isḥāq.

## Error risks
- Paraphrase drift: "green cloak" is in the text; "spider's web" is not and must never appear as from this source.
- Hedged variants must stay "the source narrates"; never collapse two reports into one fact.
- `seq` is narrative order, not chronology.
- Nested speech can swap speaker and addressee.
- A short anchor span proves location, not that the gloss is faithful.

## Scholar review cost
About 1.5–2 minutes per moment: about 2–2.5 hours for this trial. The full book would yield roughly 4,000–6,000 moments, or 100–200 review hours.

## Recommendation
1. Add `mrs:Moment` (status proposed), plus entity types for collectives, unnamed persons and non-human agents.
2. Build a normalised reading view with an offset map before extraction; keep quotes in the uncommitted cache.
3. Run by episode (maghāzī and Hijrah first); skip genealogy-only and poetry-only sections; prompt for hedges and voice.
4. Review in episode batches with a second reader on 10%; resolve entity splits in the same sitting.
