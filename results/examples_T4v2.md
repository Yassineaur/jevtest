# Example outputs: T4 + CEM v2 (seed 0) on dev paragraphs

Randomly sampled (seed 4) dev paragraphs with at least one gold technique. Decision threshold 0.23 (holdout). `p` = technique probability; each cited span shows its evidence probability after the holdout-fitted Platt recalibration (a=0.354, b=-0.800). Cited spans are exact substrings of the paragraph by construction.

## 830359136:16

> And so there is no widespread outrage over the fact that a former British PM is meeting with a tinpot Jupiterian who has subjected his own people to months of extreme violence.

**Gold:** Loaded_Language ("outrage | extreme"); Name_Calling-Labeling ("tinpot Jupiterian")

- **Name_Calling-Labeling** p=0.98 (correct); cites "a tinpot Jupiterian" (evidence prob 0.55)
- **Loaded_Language** p=0.46 (correct); cites "extreme violence" (evidence prob 0.34)

## 824658990:3

> A group of Labour MPs have announced that they are quitting the party and will sit as Independent MPs in the house of commons, hitting out at leader Jeremy Corbyn for presiding over an "institutionally anti-Semitic" party.

**Gold:** Loaded_Language ("hitting out"); Repetition ("institutionally anti-Semitic")

- **Name_Calling-Labeling** p=0.49 (false positive); cites "institutionally anti-Semitic" party" (evidence prob 0.25)
- missed: Loaded_Language, Repetition

## 813714967:43

> So really, no one knows what is going to happen out of this mess, but my bet would be that they will find some way to “fudge,” or to kick the can down the road.

**Gold:** Loaded_Language ("mess | to “fudge,” or to kick the can down the road"); Repetition ("kick the can down the road")

- **Loaded_Language** p=0.96 (correct); cites "kick the can down the road" (evidence prob 0.44)
- missed: Repetition

## 832984694:7

> Hemingway began by noting that the “Russia narrative” predates the Mueller probe, having begun circulating during the 2016 election after the creation of the infamous Clinton campaign-funded Steele dossier, which pushed the theory that then-Republican candidate Donald Trump was a “Russian agent.”

**Gold:** Loaded_Language ("predates"); Name_Calling-Labeling ("Russian agent")

- **Name_Calling-Labeling** p=0.79 (correct); cites "the infamous Clinton campaign-funded Steele dossier" (evidence prob 0.34)
- missed: Loaded_Language

## 816460196:6

> May has been criticized by both sides of the debate for her handling of the implementation of the 2016 referendum, with Remain supporters accusing her of presiding over chaos, with pro-Brexit factions in her own Conservative Party claiming that she has kowtowed to Brussels and that her deal does not actually lead to Brexit being delivered.

**Gold:** Doubt ("May has been criticized by both sides of the debate for her handling of the implementation of the 2016 referendum, with "); Loaded_Language ("accusing her of presiding over chaos | she has kowtowed")

- **Loaded_Language** p=0.73 (correct); cites "kowtowed" (evidence prob 0.32)
- missed: Doubt

## 820791520:55

> It needed a team that combined a complete command of administrative detail, a shrewd sense of the national interest, an equally shrewd assessment of the opposing interests, and an ability to understand the difference between bottom-line economic interests and the EU’s loftier moral values as an alliance committed to protecting constitutional democracy in a continent with an unhappy history of autocracies.

**Gold:** Flag_Waving ("national interest"); Loaded_Language ("shrewd | equally shrewd | loftier")

- **Loaded_Language** p=0.30 (correct); cites "unhappy history" (evidence prob 0.18)
- missed: Flag_Waving

## 833052347:5

> PHILADELPHIA — With the long-awaited special counsel’s investigation finished but its contents still shrouded in mystery, Americans waited for details, yawned with boredom or stayed fixed to their long-cemented positions on President Donald Trump, the man at the probe’s center.

**Gold:** Flag_Waving ("Americans waited for details"); Loaded_Language ("shrouded in mystery | yawned with boredom"); Name_Calling-Labeling ("the man at the probe’s center")

- **Loaded_Language** p=0.80 (correct); cites "yawned with boredom" (evidence prob 0.33)
- missed: Flag_Waving, Name_Calling-Labeling

## 833039623:11

> Too bad that President Trump won’t likely get to say, “MY TURN!” being far too busy having to bear the slings and arrows aimed at him, his family and surrogates all because the witch hunt tearing a nation apart, will, in one way or the other, continue to carry on.

**Gold:** Causal_Oversimplification ("being far too busy having to bear the slings and arrows aimed at him"); Exaggeration-Minimisation ("being far too busy having to bear the slings and arrows aimed at him | tearing a nation apart"); Flag_Waving ("tearing a nation apart"); Loaded_Language ("MY TURN"); Name_Calling-Labeling ("witch hunt"); Repetition ("Too bad that President Trump won’t likely get to say, “MY TURN!”")

- **Name_Calling-Labeling** p=0.96 (correct); cites "the witch hunt" (evidence prob 0.50)
- **Loaded_Language** p=0.56 (correct); cites "slings and arrows" (evidence prob 0.27)
- missed: Causal_Oversimplification, Exaggeration-Minimisation, Flag_Waving, Repetition

