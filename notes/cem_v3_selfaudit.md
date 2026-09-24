# CEM v3 seed set: adversarial SELF-audit (2026-09-24)

Auditor = the same AI model that wrote the rewrites. Biased by construction; this is a quality
pass, NOT the independent audit. Rules as in the v2 audit (whole edited text against the
SemEval definitions; KILL fails if the technique survives anywhere; a floating label is not
Name_Calling).

Before fixes (108 pairs):
| Family | Pass | Notes |
|---|---|---|
| KILL | 66/74 (0.89) | fails: s004 (paired questions still frame submit-vs-resist), s022 ('fake news' still loaded), s035 ('not X, nor Y... just Vatican II' minimisation left), s060 ('ate grass' hyperbole left), s071 (other double-standard charges left, unclosed quote), borderline: s020 (juxtaposition still insinuates), s073 (paragraph still questions Ganesh), s086 (still alarmist) |
| INJECT | 34/34 (weak: s004 'tyrants', s036 'that's all there is to it', s052 'what they say are') | |
| controls | 107/108 | s001 INJECT_C 'As our pastors have preached' could read as appeal to authority |

Actions: fixed s004, s035, s060 and the s001 control; dropped s020, s022, s071, s073, s086
KILL pairs. Result: 103 pairs (69 KILL, 34 INJECT), 206 views, 79 paragraphs.
Uncertain gold location (kept, flagged in `why`): s016, s058, s091.
