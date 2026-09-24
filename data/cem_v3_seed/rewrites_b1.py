# CEM v3 seed rewrites, batch 1 (s000-s028). Written by Claude (AI), 2026-09-24.
# Each entry: (pid, family, tech, {unit_index: new_unit_text}, why)
# family: KILL / KILL_C (same units, technique kept) / INJECT / INJECT_C (same unit, neutral).
# Labels are derived in build_seed.py: KILL -> gold minus tech; INJECT -> gold plus tech; *_C -> gold.
R = [
("s000","KILL","Flag_Waving",{1:"This is what led me to write my new New York Times best-selling book, “Trump’s America,” about the first two years of his presidency."},
 "national-greatness subtitle ('Our Nation's Great Comeback') removed; slogan title kept"),
("s000","KILL_C","Flag_Waving",{1:"That is why I wrote my new New York Times best-seller, “Trump’s America: The Truth About Our Nation’s Great Comeback.”"},"paraphrase, subtitle kept"),
("s000","INJECT","Straw_Man",{2:"Democrats now claim that anyone who wants a secure border simply hates immigrants, and with each passing month the radical-extremist wing of the party dominates the progressive wing more and more."},
 "attributes a distorted position to Democrats in order to attack them"),
("s000","INJECT_C","Straw_Man",{2:"Month after month, the radical-extremist wing of the Democratic Party increasingly dominates its progressive wing."},"neutral paraphrase of the same unit"),

("s001","KILL","Slogans",{0:"We have taught that Scripture forbids homosexual acts, and how it is a felony in every state in our union (Leviticus 18:22; 20:13; Jude 1:7)."},
 "the catchphrase 'homosexuality is an abomination' replaced by a plain statement"),
("s001","KILL_C","Slogans",{0:"We have long taught that homosexuality is an abomination, and how it is a felony in every state in our union (Leviticus 18:22; 20:13; Jude 1:7)."},"catchphrase kept"),
("s001","INJECT","Appeal_to_Popularity",{0:"Like the vast majority of Americans, we have taught that homosexuality is an abomination, and how it is a felony in every state in our union (Leviticus 18:22; 20:13; Jude 1:7)."},
 "claim justified by what most people supposedly believe"),
("s001","INJECT_C","Appeal_to_Popularity",{0:"As our pastors have preached for years, we have taught that homosexuality is an abomination, and how it is a felony in every state in our union (Leviticus 18:22; 20:13; Jude 1:7)."},
 "same slot, neutral attribution (no appeal to the majority)"),

("s002","INJECT","Doubt",{0:"According to the Hungarian Government's website, whose claims have repeatedly proven unreliable, posted about the ultimatum that was given over the weekend."},
 "questions the credibility of the source"),
("s002","INJECT_C","Doubt",{0:"According to the website of the Hungarian Government, posted about the ultimatum that was issued over the weekend."},"neutral paraphrase"),

("s003","KILL","Conversation_Killer",{2:"“We are still reviewing each case individually.”"},"closing 'That's my concern' (shuts down discussion) replaced by an open, informative statement"),
("s003","KILL_C","Conversation_Killer",{2:"“That’s what concerns me.”"},"same dismissive closer, paraphrased"),
("s003","INJECT","Appeal_to_Authority",{0:"“As the UN refugee agency has told us, we don’t want to put them on a ship back unless someone has had chance to look at if there’s a really bad situation for them,”"},
 "position backed by citing an authority"),
("s003","INJECT_C","Appeal_to_Authority",{0:"“We don’t want to send them back on a ship unless someone has had a chance to check whether they face a really bad situation,”"},"neutral paraphrase"),

("s004","KILL","False_Dilemma-No_Choice",{1:"Each of you will have to decide how to respond."},"'either submit or resist' removed; the questions that follow still frame a choice, but no longer an exclusive two-option claim"),
("s004","KILL_C","False_Dilemma-No_Choice",{1:"Either you submit, or you resist."},"paraphrase, dilemma kept"),
("s004","INJECT","Name_Calling-Labeling",{2:"Are you going to submit to these tyrants?” he asked the crowds."},"labels the target group as 'tyrants'"),
("s004","INJECT_C","Name_Calling-Labeling",{2:"Will you submit?” he asked the crowds."},"neutral paraphrase"),

("s005","KILL","Exaggeration-Minimisation",{0:"Dina Powell represents several policies I criticised in the Bush administration."},"'everything that was wrong' hyperbole removed"),
("s005","KILL_C","Exaggeration-Minimisation",{0:"Dina Powell embodies everything that was wrong with the Bush administration."},"hyperbole kept"),
("s005","INJECT","Guilt_by_Association",{0:"Dina Powell, a longtime ally of Huma Abedin, is everything that was wrong with the Bush administration."},"discredits Powell by linking her to a figure the audience dislikes"),
("s005","INJECT_C","Guilt_by_Association",{0:"Dina Powell, a former Goldman Sachs executive, is everything that was wrong with the Bush administration."},"same slot, neutral descriptor"),

("s006","KILL","Name_Calling-Labeling",{2:"Donald"},"mocking nickname 'Art of the Deal' removed"),
("s006","KILL_C","Name_Calling-Labeling",{2:"Donald “The Art of the Deal”"},"nickname kept"),
("s006","INJECT","Causal_Oversimplification",{4:"On Thursday, the deadline established by law for releasing the records, the CIA undoubtedly blinked, and the only reason it did is that Trump had it cornered, so he presumably got what he wanted in return for granting the CIA request for continued secrecy."},
 "single-cause explanation for the CIA's decision"),
("s006","INJECT_C","Causal_Oversimplification",{4:"On Thursday, the legal deadline for releasing the records, the CIA undoubtedly blinked, and Trump presumably got what he wanted in exchange for granting the CIA's request for continued secrecy."},"neutral paraphrase"),

("s007","KILL","Doubt",{1:"It is under this context that the (general assembly) occurred, and the report addresses this context in its later sections.”"},"attack on the report's credibility removed"),
("s007","KILL_C","Doubt",{1:"It is in this context that the (general assembly) took place, and the report fundamentally misunderstands this, which changes all of the report’s findings.”"},"credibility attack kept"),
("s007","INJECT","Loaded_Language",{0:"The Jewish groups said this vile anti-Semitic rhetoric “was used to encourage students to vote specifically against Noah Lew."},"emotive 'vile' added"),
("s007","INJECT_C","Loaded_Language",{0:"The Jewish groups said the anti-Semitic rhetoric “was used to encourage students to vote specifically against Noah Lew."},"neutral paraphrase"),

("s008","INJECT","Appeal_to_Hypocrisy",{1:"Obama has given a tremendous boost to these initiatives, as well as to Iran’s nuclear program, with his nuclear deal that has given the Iranians hundreds of billions of dollars and essentially a green light to manufacture nuclear weapons, in exchange for absolutely nothing — the same Obama who lectured the world about nuclear nonproliferation."},
 "attacks Obama by charging inconsistency"),
("s008","INJECT_C","Appeal_to_Hypocrisy",{1:"Obama has given a tremendous boost to these initiatives, as well as to Iran’s nuclear program, with his nuclear deal that has given the Iranians hundreds of billions of dollars and essentially a green light to manufacture nuclear weapons, in exchange for absolutely nothing — a deal his administration finalised in July 2015."},
 "same appended slot, neutral fact"),

("s009","KILL","Repetition",{0:"Election Strategy: “You motivate them."},"second 'whip them up' no longer repeats the first"),
("s009","KILL_C","Repetition",{0:"Election Strategy: “You whip them up."},"repetition kept"),
("s009","INJECT","Slogans",{1:"The poor, the middle income — power to the people!"},"adds a rallying slogan"),
("s009","INJECT_C","Slogans",{1:"The poor, and the middle income."},"neutral paraphrase"),

("s010","KILL","Name_Calling-Labeling",{2:"Meanwhile, Britain has a steadily lengthening record of admitting controversial Islamic preachers without a moment of hesitation."},"label 'jihad preachers' replaced by a description"),
("s010","KILL_C","Name_Calling-Labeling",{2:"Meanwhile, Britain has a steadily growing record of admitting jihad preachers without a moment's hesitation."},"label kept"),
("s010","INJECT","Appeal_to_Popularity",{0:"Even worse, as millions of Britons now recognise, the bannings of Sellner, Pettibone, Southern, and Bachmann were just part of a long pattern."},"claim backed by what 'millions' supposedly recognise"),
("s010","INJECT_C","Appeal_to_Popularity",{0:"Even worse, as I noted at the time, the bannings of Sellner, Pettibone, Southern, and Bachmann were just part of a long pattern."},"same slot, neutral"),

("s011","KILL","Slogans",{0:"Ms Geller, of the Atlas Shrugs blog, and Mr Spencer, of Jihad Watch, are also co-founders of the American Freedom Defense Initiative, best known for a pro-Israel poster campaign on the New York subway."},"slogan 'Defeat Jihad' removed"),
("s011","KILL_C","Slogans",{0:"Ms Geller, of the Atlas Shrugs blog, and Mr Spencer, of Jihad Watch, also co-founded the American Freedom Defense Initiative, best known for its pro-Israel \"Defeat Jihad\" poster campaign on the New York subway."},"slogan kept"),
("s011","INJECT","Name_Calling-Labeling",{0:"Ms Geller, the notorious Islamophobe of the Atlas Shrugs blog, and Mr Spencer, of Jihad Watch, are also co-founders of the American Freedom Defense Initiative, best known for a pro-Israel \"Defeat Jihad\" poster campaign on the New York subway."},"labels Geller"),
("s011","INJECT_C","Name_Calling-Labeling",{0:"Ms Geller, the author of the Atlas Shrugs blog, and Mr Spencer, of Jihad Watch, are also co-founders of the American Freedom Defense Initiative, best known for a pro-Israel \"Defeat Jihad\" poster campaign on the New York subway."},"same slot, neutral"),

("s012","KILL","Doubt",{0:"And finally, in a bizarre tweet, Greenwald opined, “I hope the story [maligning Assange] turns out true” – noting that the Guardian’s reputation, Assange’s fate and the right of journalists to dig up embarrassing secrets without fear of being imprisoned were all at stake."},
 "insinuation about the Guardian's motives removed; 'bizarre' kept"),
("s012","KILL_C","Doubt",{0:"And finally, in a bizarre tweet, Greenwald wrote, “I hope the story [maligning Assange] turns out true” – apparently because keeping the Guardian’s reputation intact matters more than Assange’s fate and the right of journalists to dig up embarrassing secrets without fear of prison."},"insinuation kept"),

("s013","KILL","Conversation_Killer",{7:"I don’t want to paint with a broad brush every immigrant is this, every African-American is that, every, you know, other person with different religious beliefs or whatever – that’s not accurate, and it’s not fair to them.”"},
 "dismissive closer 'that's childish' replaced by a reason"),
("s013","KILL_C","Conversation_Killer",{7:"I don’t want to paint with a broad brush that every immigrant is this, every African-American is that, every, you know, person with different religious beliefs or whatever – that’s just childish.”"},"closer kept"),
("s013","INJECT","Straw_Man",{4:"“Republicans seem to think diversity means letting anyone do whatever they want, but the Democratic Party is a much more diverse political party, attracting people who are African-American, Latino, LGBT, whatever the reason why people feel more comfortable where they are taken in, where they are included as part of a political movement or party.”"},
 "misrepresents the opponents' view of diversity"),
("s013","INJECT_C","Straw_Man",{4:"“As our convention showed, the Democratic Party is a much more diverse political party, attracting people who are African-American, Latino, LGBT, whatever the reason why people feel more comfortable where they are taken in, where they are included as part of a political movement or party.”"},
 "same slot, neutral"),

("s014","KILL","Causal_Oversimplification",{0:"In our reading, these groups of people reject the message of the cross of Christ (Philippians 3:18)."},"'simply enemies... know not the power of God' reduction removed"),
("s014","KILL_C","Causal_Oversimplification",{0:"These groups of people are simply enemies of the cross of Christ and do not know the power of God unto salvation (Philippians 3:18)."},"kept"),

("s015","KILL","Flag_Waving",{1:"Not surprisingly, the CIA’s Mexico City operations regarding Oswald are among the 98 percent of the records that Trump and the CIA have chosen to continue keeping secret, on grounds of “national security” of course."},
 "'from the American people' appeal removed"),
("s015","KILL_C","Flag_Waving",{1:"Not surprisingly, the CIA’s Mexico City operations regarding Oswald are among the 98 percent of the records that Trump and the CIA have chosen to keep secret from the American people, citing “national security,” of course."},"kept"),
("s015","INJECT","Appeal_to_Popularity",{0:"As most Americans have long suspected, things obviously went dreadfully wrong in Mexico City, which is why the CIA had to shut down that part of the post-assassination investigation."},"appeal to what most people believe"),
("s015","INJECT_C","Appeal_to_Popularity",{0:"As I have written before, things obviously went dreadfully wrong in Mexico City, which is why the CIA had to shut down that part of the post-assassination investigation."},"same slot, neutral"),

("s016","KILL","Guilt_by_Association",{8:"The mosque has operated in New York for more than two decades."},
 "link to the 1993 bomber removed; NOTE: if the gold Name_Calling span was 'radicals', it is removed too (label may need checking)"),
("s016","KILL_C","Guilt_by_Association",{8:"Over the years the mosque has attracted radicals, among them a man who later helped bomb the World Trade Center in 1993…."},"kept"),

("s017","KILL","Appeal_to_Authority",{2:"Moreover, there needs to be legislation that will bar all such groups and affiliated individuals from advising the government or receiving any grants from it."},"'as Robert Spencer advises' removed"),
("s017","KILL_C","Appeal_to_Authority",{2:"Moreover, as Robert Spencer recommends, legislation is needed that will bar all such groups and affiliated individuals from advising the government or receiving any grants from it."},"kept"),
("s017","INJECT","False_Dilemma-No_Choice",{0:"The government must either stop cooperating with Muslim Brotherhood front groups such as CAIR and ISNA immediately, or admit that it is helping them."},"two-option framing"),
("s017","INJECT_C","False_Dilemma-No_Choice",{0:"The government needs to stop cooperating with, and taking advice from, Muslim Brotherhood front groups such as CAIR and ISNA without delay."},"neutral paraphrase"),

("s018","KILL","Flag_Waving",{0:"Former San Antonio, Texas mayor and former Housing and Urban Development Secretary Julian Castro tweeted that there should be “a full public account of Russia’s interference in the 2016 election."},
 "'American people deserve... our democracy' appeal removed"),
("s018","KILL_C","Flag_Waving",{0:"Julian Castro, former mayor of San Antonio, Texas and former Housing and Urban Development Secretary, tweeted that the “American people deserve to know the whole truth about Russia’s interference in our democracy."},"kept"),

("s019","KILL","Exaggeration-Minimisation",{6:"Manafort, 69, denies involvement in the hack and says the claim is false."},"'100% false' intensifier removed"),
("s019","KILL_C","Exaggeration-Minimisation",{6:"Manafort, 69, denies any role in the hack and calls the claim “100% false”."},"kept"),
("s019","INJECT","Doubt",{4:"A well-placed source — whose account could not be verified and whose motives remain unclear — has told the Guardian that Manafort went to see Assange around March 2016."},"casts doubt on the source"),
("s019","INJECT_C","Doubt",{4:"A well-placed source, speaking on condition of anonymity, has told the Guardian that Manafort went to see Assange around March 2016."},"same slot, neutral"),

("s020","KILL","Doubt",{0:"“Well, ISIS did claim responsibility for the attack four times.",1:"Local law enforcement investigative services have found no terrorist connection, just a lone gunman,”"},
 "insinuation that the official account does not add up removed from both units"),
("s020","KILL_C","Doubt",{0:"“Well, they could be–let’s face it, ISIS warned the United States twice before the attack that they would strike Las Vegas, in June and August, and after the attack claimed responsibility four times.",1:"Meanwhile, local law enforcement investigators are telling us there is no terrorist connection–lone gunman, again, something doesn’t add up,”"},"kept"),

("s021","KILL","Flag_Waving",{2:"Despite Hezbollah’s record of attacks on coalition forces, the U.S.-led coalition has chosen not to do anything about Hezbollah’s presence in Syria, bought and paid for by Iran."},"'American blood on its hands' removed"),
("s021","KILL_C","Flag_Waving",{2:"Even though Hezbollah has American blood on its hands, the U.S.-led coalition has chosen to do nothing about Hezbollah’s presence in Syria, bought and paid for by Iran."},"kept"),
("s021","INJECT","Causal_Oversimplification",{1:"And because Iran has used Syria as a transit point for sophisticated rockets to Hezbollah, every attack on Israeli population centers can be traced to Tehran alone."},"single-cause claim"),
("s021","INJECT_C","Causal_Oversimplification",{1:"And Iran has used Syria as a transit point for shipments of sophisticated rockets to Hezbollah in Lebanon, intended for future use against Israeli population centers."},"neutral paraphrase"),

("s022","KILL","Loaded_Language",{1:"That did not stop other outlets from repeating its claims.",2:"Politico allowed \"a former CIA officer,\" writing under a pen name, to suggest - without any evidence - that the Guardian had been misled - not by its MI5/6 and Ecuadorian spy sources, but by Russian disinformation:"},"'smear' and 'duped' removed; 'fake news' label (Name_Calling) kept"),
("s022","KILL_C","Loaded_Language",{1:"That did not stop other outlets from adding to its smear.",2:"Politico let \"a former CIA officer,\" writing under a pen name, suggest - without any evidence - that the Guardian had been duped - not by its MI5/6 and Ecuadorian spy sources, but by Russian disinformation:"},"kept"),

("s023","KILL","False_Dilemma-No_Choice",{5:"The headquarters of my archdiocese and my apostolate have been occupied by radical Islamists."},"'convert or die' removed"),
("s023","KILL_C","False_Dilemma-No_Choice",{5:"Radical Islamists who want us to convert or die have occupied the headquarters of my archdiocese and my apostolate."},"kept"),

("s024","KILL","Doubt",{0:"The reasons for these statements have not been explained."},"insinuation of lies and speculation removed"),
("s024","KILL_C","Doubt",{0:"One can only guess at what the real reasons for these lies are?"},"kept"),

("s025","KILL","Appeal_to_Authority",{0:"An outbreak of the contagious and deadly Marburg virus disease began in the Kween district of eastern Uganda in October.",2:"This news comes amid a surge in cases of plague in Madagascar."},
 "Ministry of Health attribution and quoted expert verdicts removed"),
("s025","KILL_C","Appeal_to_Authority",{0:"The nation’s Ministry of Health declared the outbreak of the contagious and deadly Marburg virus disease in the Kween district of eastern Uganda back on October 19.",2:"This news comes amid a surge of plague cases in Madagascar, considered the “worst outbreak in 50 years” and now at “crisis” point."},"kept"),
("s025","INJECT","Appeal_to_Fear-Prejudice",{1:"Since then, five cases have been identified — and no family in the region can consider itself safe — as international aid agencies, stretched thin by Madagascar’s black death outbreak, have rushed to deploy teams on the ground to control the recent outbreak."},"fear appeal"),
("s025","INJECT_C","Appeal_to_Fear-Prejudice",{1:"Since then, five cases have been identified — all of them in the same district — as international aid agencies, stretched thin by Madagascar’s black death outbreak, have rushed to deploy teams on the ground to control the recent outbreak."},"same slot, neutral"),

("s026","KILL","Repetition",{0:"Evidently, they do think we are naive, or willing to play along in exchange for the benefits of respectable conformity in the midst of an unparalleled debacle for the Church."},"'fools... play the fool' repetition removed"),
("s026","KILL_C","Repetition",{0:"Evidently, they think we are fools, or willing to play the fool in return for the benefits of respectable conformity amid an unparalleled debacle for the Church."},"kept"),

("s027","KILL","Exaggeration-Minimisation",{1:"The successors of the Apostles, the only ones in a position to end his rampage, must demand his resignation and, should he refuse as expected, act to declare his removal from the office he has criminally abused and whose credibility he threatens to damage.",2:"May God give them the grace to do what must be done and what history will vindicate as a rescue of the Church during a serious crisis."},
 "'unprecedented emergency', 'very credibility... destroy', 'worst crisis in her history' toned down; 'rampage' (loaded) kept"),
("s027","KILL_C","Exaggeration-Minimisation",{1:"The successors of the Apostles, the only ones able to end his rampage, must demand his resignation and, should he refuse as expected, act in this unprecedented emergency to declare his removal from the office he has criminally abused and whose very credibility he threatens to destroy.",2:"May God grant them the grace to do what must be done, which history will vindicate as a rescue of the Church at the height of the worst crisis in her history."},"kept"),

("s028","KILL","Loaded_Language",{0:"In April 2016, Zakkout promoted a report discussing the notion of Jewish involvement in the September 11th attacks on the World Trade Center and the Pentagon.",4:"The website which published the report and which Zakkout linked to is Mouqawamah Music, a site that openly calls for “Death to Israel” and disparages the Jewish religion."},"'absurd' and quoted 'wicked and filth-ridden' removed; slogan kept"),
("s028","KILL_C","Loaded_Language",{0:"In April 2016, Zakkout promoted a report discussing the absurd idea of Jewish involvement in the September 11th attacks on the World Trade Center and the Pentagon.",4:"The website that published the report, and to which Zakkout linked, is Mouqawamah Music, a site that openly calls for “Death to Israel” and calls the Jewish religion “wicked and filth-ridden.”"},"kept"),
]
