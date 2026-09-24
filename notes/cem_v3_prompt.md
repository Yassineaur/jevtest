# CEM v3 rewrite prompt (v1, 2026-09-24)

Distilled from the 216 hand-written seed rewrites in `data/cem_v3_seed/` (built by
`code/build_cem_v3_seed.py`). Status: NOT yet tested on a generator. The pilot compares a
generator's output with the seed set on the same pairs, in a blind audit (see bottom).

## How the prompt is used

The script sends one request per (paragraph, family, technique). The paragraph is given as
numbered units, with the gold technique list. The model returns JSON only:
`{"edits": {"<unit index>": "<new unit text>", ...}, "why": "<one line>"}`.
Each edit request is paired with a control request on the SAME units (same model, same
settings), so any style left by the generator appears in both edit and control.

## System prompt

You rewrite sentences from news paragraphs to build training data for a persuasion-technique
detector. The techniques are the 19 of SemEval-2023 Task 3; their definitions follow.
{DEFINITIONS: one line each, from the SemEval-2023 annotation guidelines}

Rules for every rewrite:
1. Rewrite whole units only. Return every unit you change, fully rewritten, as a complete
   grammatical sentence. Never leave a fragment, never merge or split units.
2. Change only what the task asks. Keep names, facts, quotes' speakers, numbers and every other
   technique of the paragraph exactly as they are, unless the task says otherwise.
3. Keep length within about 30% of the original unit.
4. Keep the register (news, opinion, homily, tweet); do not make the text sound more formal.
5. If the task cannot be done cleanly (for example the technique shares its words with another
   technique that must stay), return {"edits": {}, "why": "cannot: <reason>"}.

## Task templates

KILL (remove technique T):
  The paragraph contains T. Find EVERY unit where T appears (not only the most obvious one) and
  rewrite each of them so that T is no longer present anywhere in the paragraph, while every
  other listed technique stays present. Keep the factual content; replace the persuasive device
  with a plain statement.

KILL_C (control for KILL):
  Paraphrase exactly these units {UNITS} so that the wording changes but every technique,
  including T, stays present.

INJECT (add technique T):
  The paragraph does not contain T. Rewrite exactly one unit, {UNIT}, so that it clearly uses T,
  aimed at a person, group or claim that is already in the paragraph. Do not add any other
  technique. Techniques that need a target (Name_Calling, Straw_Man, Guilt_by_Association,
  Appeal_to_Hypocrisy, Whataboutism, Red_Herring, Doubt) must attach to something in the text.

INJECT_C (control for INJECT):
  Rewrite exactly unit {UNIT}, adding a neutral detail of similar length in the same position,
  so that no technique is added or removed.

## Worked examples (from the seed set)

KILL Loaded_Language (s022; 'smear' AND 'duped' must both go, 'fake news' label stays):
  U1 "That did not hinder other outlets to add to its smear." ->
     "That did not stop other outlets from repeating its claims."
  U2 "...that the Guardian has been duped - not by..." -> "...that the Guardian had been misled - not by..."
KILL_C: U1 -> "That did not stop other outlets from adding to its smear." ; U2 -> "...had been duped..."

KILL Flag_Waving (s080; keep the doubt in 'hidden'):
  "Keep in mind, this is all information that the police and the FBI has hidden from the American people." ->
  "Keep in mind, this is all information that the police and the FBI have hidden from the public."

INJECT Doubt (s019; attaches to the existing source):
  "A well-placed source has told the Guardian that Manafort went to see Assange around March 2016." ->
  "A well-placed source — whose account could not be verified and whose motives remain unclear — has told..."
INJECT_C: "A well-placed source, speaking on condition of anonymity, has told..."

INJECT Whataboutism (s033):
  "...has called Pope Francis’s handling of abuse into question as many Catholics look to him..." ->
  "...into question — though critics said little about how his predecessors handled the very same cases — as many..."
INJECT_C: "...into question — especially cases dating from before his election — as many..."

INJECT Guilt_by_Association (s005):
  "Dina Powell is everything..." -> "Dina Powell, a longtime ally of Huma Abedin, is everything..."
INJECT_C: "Dina Powell, a former Goldman Sachs executive, is everything..."

## Lessons from writing the seed set (what the prompt must prevent)

- KILL is only valid if EVERY instance goes: in s022 and s028 the first draft removed the
  marked span but left 'duped' / a quoted 'wicked and filth-ridden', exactly the v2 failure.
- 16 of 100 paragraphs could not be edited cleanly because several techniques share the same
  words (for example the same insult is both Loaded_Language and Name_Calling). The generator
  must be allowed to refuse (rule 5); forcing it produces wrong labels.
- Injected insults must hit a target in the text; a floating label is not Name_Calling.

## Pilot to choose the generator (pre-registered)

1. Run this prompt with Qwen3-4B (local) and, optionally, one API model on the same 108 pairs.
2. Mix the generator outputs and the seed rewrites, shuffle, hide the source, audit blind with
   the same questions as `audit_v3_seed_sheet.csv`.
3. Choose the generator whose validity is highest; accept it only if every family is >= 0.8
   valid (same bar as MVP_PLAN) and controls are >= 0.9.
