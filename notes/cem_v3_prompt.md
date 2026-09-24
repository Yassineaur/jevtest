# CEM v3 rewrite prompts (v2, 2026-09-24)

v1 was written before the self-audit (`notes/cem_v3_selfaudit.md`); v2 adds what the audit
showed. Still UNTESTED on any generator: the pilot at the bottom decides whether it works.

## What changed from v1 and why

| Problem found in the self-audit | Fix in v2 |
|---|---|
| 8/74 KILL failed because a SECOND instance of the technique survived (s022, s060, s035) | KILL is two-step: first list every instance with quotes, then rewrite, then re-scan (fields `instances`, `edits`, `recheck`) |
| Techniques carried by STRUCTURE, not words, were missed: paired questions = dilemma (s004), juxtaposed facts = doubt (s020), 'not X, nor Y... just Z' list = minimisation (s035), idioms = hyperbole ('ate grass', s060) | a "hidden carriers" checklist in the KILL template |
| Overlapping techniques (one insult = Loaded + Name_Calling) made 16/100 paragraphs impossible | explicit refusal rule with the overlap reason; refusals are logged, never forced |
| A control drifted into a technique ('As our pastors have preached' = authority, s001) | controls may only add neutral detail types from a fixed list |
| Injected techniques can bring collateral ones ('partisan hacks' = Name_Calling + Loaded) | INJECT asks for the plainest wording that still carries T; the verifier checks all 19 |
| Placeholder definitions in v1 | working definitions below, with the confusable pairs spelled out |
| A 4B model needs examples per technique, not five generic ones | the few-shot block is filled per request with 2 seed examples OF THE SAME technique and family |
| Self-grading bias | a separate VERIFIER prompt, run by a different model than the generator |

## Working definitions (paraphrased from the SemEval-2023 Task 3 guidelines, Piskorski et al.
2023; replace with the official text before the paper)

- Loaded_Language: words or phrases with strong emotional connotation used to influence.
- Name_Calling-Labeling: a label (insult or praise) attached to a person or group that the
  audience fears, hates or likes. NEEDS A TARGET. Overlaps Loaded_Language when the label itself is emotive.
- Repetition: the same word, phrase or idea repeated to persuade.
- Exaggeration-Minimisation: representing something as much larger/better/worse or much
  smaller/less important than it is (includes 'nothing but', 'just', dismissive lists).
- Doubt: questioning the credibility of someone or something (including by insinuation or
  scare quotes). NEEDS A TARGET.
- Appeal_to_Fear-Prejudice: promoting or rejecting an idea by exploiting fear or prejudice.
- Flag_Waving: justifying an idea by appeal to a group's pride or identity (nation, 'the American people').
- Causal_Oversimplification: assuming a single cause when there are several.
- False_Dilemma-No_Choice: presenting two options (or one) as the only ones.
- Slogans: short, striking phrases, often labels or stereotypes, used as a rallying cry.
- Conversation_Killer: phrases that discourage discussion ('and that's that', 'rightly so').
- Appeal_to_Authority: a claim is true because an authority/expert says so.
- Appeal_to_Popularity: a claim is true because 'everyone'/'most people' believe it.
- Appeal_to_Hypocrisy: attacking the target by charging inconsistency between words and deeds. NEEDS A TARGET.
- Whataboutism: deflecting a criticism by pointing to the opponent's or someone else's other wrongs.
- Red_Herring: introducing an irrelevant issue to divert attention from the point.
- Straw_Man: replacing an opponent's position with a distorted one and attacking that. NEEDS A TARGET.
- Guilt_by_Association: attacking a target by linking it to a disliked person or group. NEEDS A TARGET.
- Obfuscation-Vagueness-Confusion: deliberately unclear wording that allows several readings.

Confusable pairs to keep apart: Loaded vs Name_Calling (a label vs an emotive word);
Whataboutism vs Appeal_to_Hypocrisy vs Red_Herring ('what about their X' vs 'they do not practise
what they preach' vs 'let us talk about something else'); Doubt vs Loaded ('so-called experts'
can be both); Conversation_Killer vs Slogans.

## Generator system prompt

You rewrite sentences from news paragraphs to build training data for a persuasion-technique
detector. Use the definitions above. Answer with JSON only, in the schema of the task.
Rules for every rewrite:
1. Rewrite whole numbered units only; each changed unit must be a complete grammatical sentence
   (same number of units, no merging, no fragments).
2. Change only what the task asks. Keep names, facts, numbers, quoted speakers, the register,
   and every other listed technique.
3. Keep each unit within about 30% of its original length.
4. If the task cannot be done cleanly, return {"refuse": "<reason>"}. Refusing is correct when
   the words carrying T also carry another listed technique that must stay.

## Task templates

KILL (remove T; other techniques listed: {OTHERS}):
Step 1 `instances`: quote EVERY place in the paragraph where T appears. Check the hidden carriers
too: paired or listed alternatives (dilemma), juxtaposed facts that insinuate (doubt), 'not X,
nor Y... just Z' lists (minimisation), idioms and metaphors (exaggeration), scare quotes (doubt),
labels inside quotations (they count).
Step 2 `edits`: rewrite every unit that contains an instance so T disappears, keeping {OTHERS}.
Step 3 `recheck`: read the full edited paragraph and list any remaining T; if any, fix or refuse.
Schema: {"instances": [...], "edits": {"<i>": "..."}, "recheck": "none" | [...], "why": "..."}

KILL_C (control): paraphrase exactly units {UNITS}; every technique, including T, stays.
Schema: {"edits": {"<i>": "..."}}

INJECT (add T, which is absent): rewrite exactly unit {UNIT} so it clearly uses T, aimed at a
person, group or claim already in the paragraph. Use the plainest wording that still carries T,
so no other technique is added.
Schema: {"target": "<who/what T is aimed at>", "edits": {"<i>": "..."}, "why": "..."}

INJECT_C (control): rewrite exactly unit {UNIT}, adding one neutral detail of similar length at
the same position. Allowed detail types: a date, a place, a job title, a number, a procedural
fact. Not allowed: sources, attributions, majorities, evaluations.
Schema: {"edits": {"<i>": "..."}}

Few-shot block (filled per request): 2 examples from `data/cem_v3_seed/seed_views.jsonl` with
the same family and technique, each shown as original unit -> rewritten unit + `why`.

## Verifier prompt (a DIFFERENT model from the generator)

Given the edited paragraph and the definitions, answer for EACH of the 19 techniques: present /
absent, with the quoted evidence if present. The view is kept only if the verifier's answer
matches the view's label on the target technique AND no technique other than the target changed
between the original and the edited paragraph. Disagreements go to the human audit pool.

## Pilot (pre-registered)

1. Generator candidates: Qwen3-4B (local) and one stronger model; same prompts, temperature 0.3.
2. Run on the 103 seed pairs' paragraphs, same families and techniques.
3. Blind audit of a mixed sample (generator outputs + seed rewrites, source hidden).
4. Accept a generator only if every family is >= 0.8 valid, controls >= 0.9, refusals < 25%, and
   the verifier agrees with the human audit on >= 85% of items (so the verifier can be trusted
   to filter the full pool).
