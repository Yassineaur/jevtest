# COPIED 2026-09-23 from ../../sftgrpo/finalsftgrpo/prompts/inference_prompt.py (read-only original, unchanged).
"""v4 inference prompt — COMPACT full taxonomy (all six families).

Used by:
  - The trained student model at deployment
  - SFT loss masking (loss computed only on the response portion)
  - GRPO rollouts (same prompt — no extra content during RL)

Design note (why compact, not identical to the annotation prompt):
  The student never sees the annotation prompt — that is teacher-only. Only three
  things must hold at inference: (1) the FULL taxonomy is available (all 23 labels
  / six families — no restricted menu, no oracle leak), (2) the OUTPUT format is
  identical to what the teacher produced (so the parser and learned behavior
  transfer), (3) exact label names. The verbose TASK/CHECKS/STYLE scaffolding the
  teacher used is internalized during SFT and does NOT need restating here — so we
  keep this prompt short (~400 tokens) to minimise the per-rollout token tax in
  GRPO and preserve generation headroom.

  Labels are grouped by family for presentation parity with the annotation
  template, but the model still classifies over the whole taxonomy.

NO family hint, no gold labels — at inference the model sees only the paragraph
and the full six-family taxonomy reference.
"""
from __future__ import annotations


_TEMPLATE = r"""Identify the persuasion techniques in the paragraph below. Reason briefly from the wording inside <think>, then commit to the techniques present (or none).

TECHNIQUES (use these exact full names):
Attack on Reputation:
- Name Calling or Labelling: demeaning/glorifying label on a specific target
- Guilt by Association: target tainted via link to a disliked group/concept
- Casting Doubt: credibility/competence/honesty specifically undermined
- Appeal to Hypocrisy: target attacked for inconsistency / double standards
- Questioning the Reputation: broad moral/character condemnation without argument
Justification:
- Flag Waving: group identity/pride IS the justification
- Appeal to Authority: a NAMED authority/expert/study cited as reason to believe
- Appeal to Popularity: "everyone agrees" / "most people" as proof
- Appeal to Values: positive values (freedom, fairness, family) as justification
- Appeal to Fear, Prejudice: a feared CONSEQUENCE IS the argument
Distraction:
- Strawman: opponent's STATED position distorted then attacked
- Red Herring: an IRRELEVANT topic displaces the main issue
- Whataboutism: a COUNTER-ACCUSATION deflects criticism
Simplification:
- Causal Oversimplification: one single cause for a complex outcome
- False Dilemma, No Choice: only two options when more exist
- Consequential Oversimplification: improbable domino-chain of consequences
Call:
- Slogans: brief emotional phrase designed to persuade, not argue
- Conversation Killer: phrase that forecloses debate or critical thought
- Appeal to Time: urgency / "now is the moment" as the argument
Manipulative Wording:
- Loaded Language: emotionally charged wording itself carries the persuasion
- Obfuscation, Intentional Vagueness, Confusion: deliberately unclear/euphemistic language
- Exaggeration or Minimisation: scale/magnitude distorted upward or downward
- Repetition: same phrase repeated, recurrence is the engine

OUTPUT (concise reasoning in <think>, ~120-300 words — longer only if several distinct mechanisms genuinely apply):
<think>[concise reasoning anchored to specific quoted phrases]</think>
<techniques>Technique x | Technique y</techniques>
<spans>verbatim span x | verbatim span y</spans>

Each span must be the SHORTEST verbatim substring of the paragraph that carries the technique — a word or short phrase, not a whole sentence.

If no technique applies: <techniques></techniques><spans></spans>

If multiple spans support one technique, repeat the technique name for each span:
in the following example, the technique z is supported by two spans, and the technique w is supported by one span.
<techniques>Technique z | Technique z | Technique w</techniques>
<spans>verbatim span z | verbatim span z | verbatim span w</spans>
This will allow us to correctly attribute the spans to the correct technique.

Paragraph:
{paragraph}
"""


def render(paragraph: str) -> str:
    return _TEMPLATE.format(paragraph=paragraph)


def render_chat(paragraph: str) -> list:
    """Chat-template form (preferred for the student model)."""
    return [{"role": "user", "content": render(paragraph)}]
