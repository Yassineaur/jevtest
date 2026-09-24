# CEM v3 seed rewrites, batch 4 (s077-s099). Written by Claude (AI), 2026-09-24.
# Skipped (techniques share the same words, or gold location too uncertain): s087, s090, s094, s097, s098
R = [
("s077","INJECT","Red_Herring",{3:"Democrats would prefer to drag the confirmation process into the next Congress where they stand a good chance of taking control from Republicans — but the real question voters should ask is why the Senate still hasn’t passed a budget."},
 "diverts attention to an unrelated issue"),
("s077","INJECT_C","Red_Herring",{3:"Democrats would prefer to drag the confirmation process into the next Congress where they stand a good chance of taking control from Republicans — a strategy that depends on the November results."},"same slot, neutral"),

("s078","KILL","Appeal_to_Authority",{1:"One could readily point to the evidence that a faction that included Bergoglio himself had agreed upon his election before the conclave, which some canonists argue would carry consequences for all involved, including Bergoglio:"},
 "reliance on Article 81 of John Paul II's constitution removed"),
("s078","KILL_C","Appeal_to_Authority",{1:"One could easily point to evidence that a faction including Bergoglio himself had agreed on his election before the conclave, and that everyone involved, Bergoglio included, was thereby excommunicated latae sententiae under Article 81 of John Paul II’s Universi Dominici Gregis, which provides:"},"kept"),

("s079","KILL","Doubt",{0:"There are two conflicting timelines of Campos’s injury, but the current account is that Campos was walking down the Mandalay Bay Hotel & Casino’s 32nd floor hallway, when Stephen Paddock spotted him on a camera he’d allegedly set up in a room service cart, just outside his suite."},
 "'what the media... want the public to believe' removed"),
("s079","KILL_C","Doubt",{0:"There are two conflicting timelines of Campos’s injury, but what the media has made clear so far is that they want the public to believe Campos was walking down the Mandalay Bay Hotel & Casino’s 32nd floor hallway when Stephen Paddock spotted him on a camera he had allegedly set up in a room service cart just outside his suite."},"kept"),

("s080","KILL","Flag_Waving",{1:"Keep in mind, this is all information that the police and the FBI have hidden from the public."},"'the American people' replaced; 'hidden' (doubt) kept"),
("s080","KILL_C","Flag_Waving",{1:"Remember, this is all information the police and the FBI have hidden from the American people."},"kept"),

("s081","KILL","Conversation_Killer",{0:"The faces of the criminal Democrat Party, at least two of them, have now had an ethics complaint filed against them in the US Senate."},"closer 'and rightly so' removed"),
("s081","KILL_C","Conversation_Killer",{0:"At least two of the faces of the criminal Democrat Party have now had an ethics complaint filed against them in the US Senate, and rightly so."},"kept"),

("s082","KILL","Name_Calling-Labeling",{2:"They are in Europe to conquer and Islamize it, with help from parts of Europe’s intelligentsia.\""},"'short-sighted, self-serving, internationalist intelligentsia' labels removed"),
("s082","KILL_C","Name_Calling-Labeling",{2:"They are in Europe to conquer and Islamize it, with the willing and eager help of Europe’s short-sighted, self-serving, internationalist intelligentsia.\""},"kept"),

("s083","KILL","Name_Calling-Labeling",{0:"The Guardian has published several stories critical of Russia that rely on British government sources."},"'main outlet for British government disinformation' label removed"),
("s083","KILL_C","Name_Calling-Labeling",{0:"The Guardian has become a main outlet for British government disinformation operations meant to defame Russia."},"kept"),

("s084","KILL","False_Dilemma-No_Choice",{0:"That notion read more like a warning, and the Correspondents’ Association seemed unmoved."},"'behave or else' removed"),
("s084","KILL_C","False_Dilemma-No_Choice",{0:"That notion sounded more like a warning — behave or else — and the Correspondents’ Association seemed unmoved."},"kept"),

("s085","INJECT","Exaggeration-Minimisation",{0:"Given that Pope Francis has, since that interview took place, attempted to make the Argentine bishops’ interpretation of AL 'magisterial'--an interpretation that allows public adulterers to receive Holy Communion and overturns two thousand years of Catholic teaching--Cardinal Burke’s reply to my question on January 9th of this year would seem to take on new relevancy."},
 "hyperbolic 'overturns two thousand years'"),
("s085","INJECT_C","Exaggeration-Minimisation",{0:"Given that Pope Francis has, since that interview took place, attempted to make the Argentine bishops’ interpretation of AL 'magisterial'--an interpretation that allows public adulterers to receive Holy Communion, a point debated among canonists--Cardinal Burke’s reply to my question on January 9th of this year would seem to take on new relevancy."},
 "same slot, neutral"),


("s088","KILL","Causal_Oversimplification",{1:"Ford’s supporters are invoking the “Me Too” movement in declaring Judge Kavanaugh guilty, pointing to Ms.",2:"Ford’s account, which they call a “credible” charge, although it has not so far been corroborated."},
 "'simply because Ms. Ford is a woman' single-cause claim removed; 'Kavanaugh Derangement Syndrome' kept"),
("s088","KILL_C","Causal_Oversimplification",{1:"Ford’s supporters are exploiting the “Me Too” movement to declare Judge Kavanaugh guilty merely because Ms.",2:"Ford is a woman who has made what they call a “credible” charge, without any corroborating evidence so far."},"kept"),

("s089","KILL","Flag_Waving",{0:"“When the Trump Administration inexplicably gave the green light to distribute on the internet blueprints of 3D-printed, untraceable ghost guns, it needlessly endangered public safety,”"},
 "'our children, our loved ones and our men and women in law enforcement' removed"),
("s089","KILL_C","Flag_Waving",{0:"“When the Trump Administration inexplicably gave the green light to posting blueprints of 3D-printed, untraceable ghost guns online, it needlessly put our children, our loved ones and our men and women in law enforcement in danger,”"},"kept"),

("s091","KILL","Straw_Man",{2:"Under an obscure set of US regulations known as the International Trade in Arms Regulations (ITAR), Wilson was accused of exporting weapons without a license by putting a digital version of his gun on the internet."},
 "caricature of the government's position ('just as if he'd shipped his plastic gun to Mexico') removed; NOTE: gold Straw_Man location uncertain"),
("s091","KILL_C","Straw_Man",{2:"Under an obscure set of US regulations called the International Trade in Arms Regulations (ITAR), Wilson was accused of exporting weapons without a license, just as if he had shipped his plastic gun to Mexico instead of putting a digital version of it online."},"kept"),

("s092","KILL","Causal_Oversimplification",{2:"“I believe my case was handled more harshly than it should have been,” he continued, saying the case had ruined his life."},"single political cause removed"),
("s092","KILL_C","Causal_Oversimplification",{2:"“They made an example of me because of [the backlash over] Hillary Clinton,” he went on, alleging his life was ruined for political reasons."},"kept"),

("s093","INJECT","Loaded_Language",{0:"Top Florida County Election Official Brazenly Let People Vote Over Fax & Email"},"emotive 'Brazenly'"),
("s093","INJECT_C","Loaded_Language",{0:"Top Florida County Election Official Illegally Allowed People To Vote By Fax & Email"},"neutral paraphrase"),

("s095","KILL","Name_Calling-Labeling",{0:"The newest warning about the outbreak of the airborne pneumonic plague in Madagascar has been released."},"'black death' label removed"),
("s095","KILL_C","Name_Calling-Labeling",{0:"The newest warning about the outbreak of the airborne pneumonic plague, or black death, in Madagascar has now been released."},"kept"),

("s096","KILL","Flag_Waving",{0:"Ever since the assassination, the CIA has argued against releasing its JFK records."},"'national security' appeal removed"),
("s096","KILL_C","Flag_Waving",{0:"Since the assassination, the CIA has maintained that releasing any of its JFK records would threaten “national security.”"},"kept"),

("s099","KILL","Loaded_Language",{0:"As an aside, one of the more vocal proponents of BDS at McGill is a student named Igor Sadikov, who in February posted a comment on twitter advocating violence against “Zionists.”",2:"Sadikov later described his “punch a Zionist” tweet as a mistake."},
 "'rancid character' and 'made light of... misguided joke' neutralised; 'punch a Zionist' kept"),
("s099","KILL_C","Loaded_Language",{0:"As an aside, one of the more vocal BDS proponents at McGill is a rancid character called Igor Sadikov, who in February posted a comment on twitter advocating violence against “Zionists.”",2:"Sadikov made light of his “punch a Zionist” tweet, calling it a “misguided joke.”"},"kept"),
]
