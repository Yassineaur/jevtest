# CEM v3 seed rewrites, batch 3 (s055-s076). Written by Claude (AI), 2026-09-24.
# Skipped (techniques share the same words, or gold location too uncertain): s064, s065, s067, s069, s076
R = [
("s055","KILL","Slogans",{0:"Iran has tested several ballistic missiles during the last two years, including two Qadr H missiles with anti-Israel messages emblazoned on the sides."},"slogan 'Israel must be wiped out' removed"),
("s055","KILL_C","Slogans",{0:"Over the last two years Iran has tested several ballistic missiles, including two Qadr H missiles with the words “Israel must be wiped out” painted on the sides."},"kept"),

("s056","KILL","Loaded_Language",{1:"His existence appears to have been fabricated by the authorities, who are giving an inaccurate account of this shooting for political reasons."},"'cramming lies down our throats', 'massacre', 'mere' neutralised; doubt kept"),
("s056","KILL_C","Loaded_Language",{1:"His very existence seems to have been fabricated by the same authorities who are cramming lies down our throats about this massacre for political ends."},"kept"),

("s057","INJECT","Straw_Man",{0:"Civil-liberties activists apparently think anyone should be free to cheer for terrorists, and simply expressing support for a terrorist organization or attack is not against the law."},"distorts the activists' position"),
("s057","INJECT_C","Straw_Man",{0:"Under current federal law, simply expressing support for a terrorist organization or attack is not against the law."},"same slot, neutral"),

("s058","KILL","Red_Herring",{2:"More outlets are now starting to report on it."},"diversion to the 'national dialogue about racism' removed; NOTE: gold location of Red_Herring uncertain"),
("s058","KILL_C","Red_Herring",{2:"We're beginning to have that \"national dialogue\" about racism that the left keeps asking us to have."},"kept"),

("s059","KILL","Loaded_Language",{0:"“You get accused of treasonous activity and treasonous speech because telling the truth is now treated as disloyal,”"},"'empire of lies' removed (same judgement as audit row 76)"),
("s059","KILL_C","Loaded_Language",{0:"“You get accused of treasonous activity and treasonous speech because in an empire of lies, truth is treason,”"},"kept"),

("s060","KILL","Exaggeration-Minimisation",{0:"Because North Korea has spent heavily for decades to build nuclear weapons, largely to deter a major US attack, including the use by the US of tactical nuclear weapons."},
 "'for the sole reason' and 'scraped and skimped' toned down; NOTE: if the gold Loaded span is 'scraped and skimped' it is removed too"),
("s060","KILL_C","Exaggeration-Minimisation",{0:"Because North Korea has scraped and skimped for decades to build nuclear weapons for the sole purpose of deterring a major US attack, including the US use of tactical nuclear weapons."},"kept"),

("s061","KILL","Obfuscation-Vagueness-Confusion",{2:"Officials have not given the attacker’s motive, although witnesses reported that he shouted “Allahu Akbar.”"},"deliberately vague sarcastic line replaced by a plain statement"),
("s061","KILL_C","Obfuscation-Vagueness-Confusion",{2:"“Allahu Akbar” usually means “motive unknown.”"},"kept"),

("s062","KILL","Flag_Waving",{1:"The San Antonio CBS affiliate reported that Spittler wrote: “His friend was wearing a hat, and this happened!"},"'patriotic' removed"),
("s062","KILL_C","Flag_Waving",{1:"The San Antonio CBS affiliate reported that Spittler wrote: “His friend was wearing a patriotic hat, and look what happened!"},"kept"),

("s063","INJECT","Loaded_Language",{1:"Kemp has declared victory and said it is “mathematically impossible” for her desperate campaign to force a runoff."},"emotive 'desperate'"),
("s063","INJECT_C","Loaded_Language",{1:"Kemp has declared victory and said it is “mathematically impossible” for her campaign to force a runoff election."},"same unit, neutral"),

("s066","KILL","False_Dilemma-No_Choice",{3:"The World Health Organization has been warning about the “Ebola situation” in Congo, and it appears an experimental vaccine is one of the options."},"'only solution' removed"),
("s066","KILL_C","False_Dilemma-No_Choice",{3:"The World Health Organization has been warning about the “Ebola situation” in Congo, and it appears their only option is an experimental vaccine."},"kept"),
("s066","INJECT","Appeal_to_Fear-Prejudice",{2:"“It will target, first, the health staff, the contacts of the sick and the contacts of the contacts, before this deadly virus reaches every city in the country.”"},"fear appeal"),
("s066","INJECT_C","Appeal_to_Fear-Prejudice",{2:"“It will first target the health staff, then the contacts of the sick and the contacts of those contacts.”"},"neutral paraphrase"),

("s068","INJECT","Loaded_Language",{0:"Now in the United States a chorus of voices is rising especially from the lay faithful, and has recently been joined by several bishops and priests, asking that all those who, by their cowardly silence, covered up McCarrick’s depraved behavior, or who used him to advance their career or promote their intentions, ambitions and power in the Church, should resign."},
 "emotive 'cowardly', 'depraved'"),
("s068","INJECT_C","Loaded_Language",{0:"Now in the United States a chorus of voices is rising, especially from the lay faithful, recently joined by several bishops and priests, asking that all those who, by their silence, concealed McCarrick’s criminal behavior, or who used him to advance their career or promote their intentions, ambitions and power in the Church, should resign."},"neutral paraphrase"),

("s070","KILL","Slogans",{0:"Nation of Islam leader and prominent antisemite Louis Farrakhan led anti-American chants and claimed that “America has never been a democracy” on Sunday during a solidarity trip to Iran, ahead of the re-implementation of US sanctions on the country this week."},"'Death to America' slogan removed"),
("s070","KILL_C","Slogans",{0:"Nation of Islam leader and prominent antisemite Louis Farrakhan chanted “Death to America” and said that “America has never been a democracy” on Sunday, during a solidarity trip to Iran ahead of the re-imposition of US sanctions this week."},"kept"),

("s071","KILL","Appeal_to_Hypocrisy",{0:"“We must also investigate and speak openly about the deliberate, ideology-driven murder of British children,"},
 "Grenfell double-standard charge removed; NOTE: U2 ('while the rest of us...') also contrasts treatment, check whether it was annotated as hypocrisy"),
("s071","KILL_C","Appeal_to_Hypocrisy",{0:"“Why do we discuss, investigate and get angry about an accidental fire at Grenfell, yet are expected to instantly forget — or ‘not look back in anger’ — the deliberate, ideology-driven murder of British children?"},"kept"),

("s072","KILL","Guilt_by_Association",{3:"Such measures are unusual in Britain."},"comparison with North Korea and Saudi Arabia removed"),
("s072","KILL_C","Guilt_by_Association",{3:"Measures like these are common practice in North Korea and Saudi Arabia."},"kept"),

("s073","KILL","Doubt",{1:"Ganesh draws several inferences.",7:"The British counter-jihad movement is thus swept into the same group of violent extremists as Osborne, because Ganesh argues they encouraged him."},"'wild leaps' and scare-quoted 'knows' removed"),
("s073","KILL_C","Doubt",{1:"Ganesh makes wild leaps and inferences.",7:"The British counter-jihad movement is thereby lumped in with violent extremists like Osborne, because Ganesh “knows” they encouraged him."},"kept"),

("s074","KILL","Straw_Man",{2:"Allen does not say whether he finds the testimony credible overall."},"misrepresentation 'his way of saying: Don't believe it' removed"),
("s074","KILL_C","Straw_Man",{2:"Which is simply Allen’s subtler way of saying: “Don’t believe it.”"},"kept"),

("s075","INJECT","Name_Calling-Labeling",{1:"The New Yorker has just published an article written by partisan hacks Ronan Farrow and Jane Mayer, based on information that was reportedly sent to at least four Democratic senators."},"labels the authors"),
("s075","INJECT_C","Name_Calling-Labeling",{1:"The New Yorker has just published an article written by staff writers Ronan Farrow and Jane Mayer, based on information that was reportedly sent to at least four Democratic senators."},"same slot, neutral"),
]
