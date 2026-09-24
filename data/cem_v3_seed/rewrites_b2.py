# CEM v3 seed rewrites, batch 2 (s029-s054). Written by Claude (AI), 2026-09-24.
# Skipped (techniques share the same words, or gold location too uncertain for a clean edit):
#   s030, s031, s041, s043, s049, s053
R = [
("s029","KILL","Name_Calling-Labeling",{4:"That error threatens to overwhelm the Church while they do little more than fret about a situation whose cause—in my view, the Pope’s own theological choices—they seem incapable of identifying."},
 "labels 'reckless Pope... filled with contempt for Tradition' replaced by a plain attribution"),
("s029","KILL_C","Name_Calling-Labeling",{4:"That error threatens to overwhelm the Church while they merely fret about a situation whose self-evident cause—a reckless Pope in love with his own ideas and full of contempt for Tradition—they seem unable to identify."},"kept"),

("s032","KILL","False_Dilemma-No_Choice",{0:"Do we accept that outcome, pack up and go home, or look for other options?",1:"One of them is to leave our forces in Syria and Iraq and defy any demand from Assad to vacate his country."},
 "exclusive two-option framing opened up; NOTE: if the gold fear span is 'pack up and go home' it is kept"),
("s032","KILL_C","False_Dilemma-No_Choice",{0:"Do we accept that outcome, pack up and head home?",1:"Or do we keep our forces in Syria and Iraq and defy any demand from Assad to leave his country?"},"kept"),

("s033","KILL","Name_Calling-Labeling",{1:"The pope’s track record has been mixed, something some outsiders attribute to his learning curve or shortcomings and others chalk up to resistance within the institution."},"'notoriously change-averse institution' label removed"),
("s033","KILL_C","Name_Calling-Labeling",{1:"The pope’s record has been mixed, which some outsiders attribute to his learning curve or shortcomings and others blame on resistance from a notoriously change-averse institution."},"kept"),
("s033","INJECT","Whataboutism",{0:"The new wave of allegations has called Pope Francis’s handling of abuse into question — though critics said little about how his predecessors handled the very same cases — as many Catholics look to him to help the church regain its credibility."},
 "deflects criticism by pointing at others' conduct"),
("s033","INJECT_C","Whataboutism",{0:"The new wave of allegations has called Pope Francis’s handling of abuse into question — especially cases dating from before his election — as many Catholics look to him to help the church regain its credibility."},"same slot, neutral"),

("s034","KILL","Slogans",{0:"Hungarian Prime Minister says Christianity plays an important role in Europe"},"catchphrase headline replaced by a plain report"),
("s034","KILL_C","Slogans",{0:"Hungary’s Prime Minister: ‘Christianity is Europe’s last hope’"},"kept"),

("s035","KILL","Exaggeration-Minimisation",{1:"And only, apparently, a single “interpretation” of it, if we are to judge by the soap and oil Braz de Aviz poured on the ruffled feathers of the Leadership Conference of Women Religious – an organisation strongly critical of Church teaching – and by his treatment of the Franciscans of the Immaculate."},
 "'most virulently anti-Catholic organisation... in the world' and 'vicious persecution' toned down; NOTE: the 'not X, nor Y... just Vatican II' list in U0 may also be annotated as minimisation"),
("s035","KILL_C","Exaggeration-Minimisation",{1:"And only, it seems, a single “interpretation” of it, judging by the soap and oil Braz de Aviz poured on the ruffled feathers of the Leadership Conference of Women Religious – the most virulently anti-Catholic organisation of “Catholic” religious anywhere in the world – and by his vicious persecution of the Franciscans of the Immaculate."},"kept"),

("s036","KILL","Name_Calling-Labeling",{4:"So, they find a woman from Kavanaugh’s past and convince her to say that he assaulted her, thinking that such an allegation will surely delay the vote long enough for them to regain control of Congress."},
 "'Trump-hating woman' label removed; single-motive causal story kept"),
("s036","KILL_C","Name_Calling-Labeling",{4:"So they dig up some Trump-hating woman from Kavanaugh’s past and persuade her to say he assaulted her, thinking such an allegation will surely delay the vote long enough for them to regain control of Congress."},"kept"),
("s036","INJECT","Conversation_Killer",{1:"There's an election 2 months away, and that's all there is to it."},"phrase that shuts down further discussion"),
("s036","INJECT_C","Conversation_Killer",{1:"There's an election two months from now."},"neutral paraphrase"),

("s037","KILL","Appeal_to_Authority",{1:"And the number of cases is growing by the day, as the nation put all hospitals on high alert."},"attribution to the IFRC secretary general removed"),
("s037","KILL_C","Appeal_to_Authority",{1:"And the number of cases grows by the day, said Elhadj As Sy, secretary general of the International Federation of Red Cross and Red Crescent Societies (IFRC), as the nation put all hospitals on high alert."},"kept"),
("s037","INJECT","Doubt",{0:"Officials claim to have reported infections in 17 of the island nation’s 22 regions since the outbreak started in August, though their figures have been questioned before."},"questions the officials' credibility"),
("s037","INJECT_C","Doubt",{0:"Officials have reported infections in 17 of the island nation’s 22 regions since the outbreak began in August, according to the latest bulletin."},"same slot, neutral"),

("s038","KILL","Name_Calling-Labeling",{0:"Speaking of Mastercard, the David Horowitz Freedom Center just recently won a major battle with the credit card, defeating well-financed groups that are trying to run the Center out of business and suffocate free speech in America.",1:"The Freedom Center emerged victorious, but it is clear that groups such as the SPLC and Color of Change.org are preparing new attacks against the Freedom Center and other conservative groups and individuals 24/7."},
 "'leftwing groups' and 'leftist hate groups' labels removed; 'suffocate free speech in America', '24/7' kept"),
("s038","KILL_C","Name_Calling-Labeling",{0:"Speaking of Mastercard, the David Horowitz Freedom Center recently won a major battle with the credit card company, defeating well-financed leftwing groups that are trying to drive the Center out of business and suffocate free speech in America.",1:"The Freedom Center won, but clearly leftist hate groups such as the SPLC and Color of Change.org are preparing new attacks on the Freedom Center and other conservative groups and individuals 24/7."},"kept"),

("s039","KILL","Exaggeration-Minimisation",{0:"“When the Parkland shooting happened, our phone calls and emails increased sharply,” said coalition president Tim Lambert."},"'exploded' hyperbole removed"),
("s039","KILL_C","Exaggeration-Minimisation",{0:"“When the Parkland shooting happened, our phone calls and emails just exploded,” said coalition president Tim Lambert."},"kept"),
("s039","INJECT","Flag_Waving",{1:"“In the last couple of months, as patriotic Americans stood up for their Second Amendment rights, our numbers have doubled."},"appeal to patriotism"),
("s039","INJECT_C","Flag_Waving",{1:"“In the last couple of months, according to our office records, our numbers have doubled."},"same slot, neutral"),

("s040","KILL","Loaded_Language",{1:"Prudence now risks becoming inaction.",3:"The members of a hierarchy seemingly reluctant to challenge the current papacy must rise immediately and give an answer to the challenge posed long ago by Monsignor Klaus Gamber, when an already serious ecclesial crisis was still in what can now can be seen as merely a preliminary stage:"},
 "'pusillanimity', 'cowed by a papal tyranny', 'courageous', 'monumental' neutralised"),
("s040","KILL_C","Loaded_Language",{1:"Prudence has now given way to mere pusillanimity.",3:"The members of a hierarchy apparently cowed by a papal tyranny unlike any the Church has seen must rise at once and give a courageous answer to the challenge Monsignor Klaus Gamber posed long ago, when an already monumental ecclesial crisis was still in what can now be seen as merely a preliminary stage:"},"kept"),

("s042","KILL","Appeal_to_Authority",{2:"Lyndon Johnson telephones Dallas District Attorney Henry Wade on the night of the assassination and orders him to shut down any investigation of a conspiracy because it might lead to nuclear war."},"self-citation '(See my book...)' removed"),
("s042","KILL_C","Appeal_to_Authority",{2:"(See my book, The Kennedy Autopsy.) On the night of the assassination, Lyndon Johnson telephones Dallas District Attorney Henry Wade and orders him to shut down any investigation of a conspiracy because it might lead to nuclear war."},"kept"),

("s044","KILL","Flag_Waving",{1:"Those long-secret records undoubtedly include small bits of important circumstantial evidence that fill out even further the mosaic of a regime-change operation that took place in Dallas in November 1963, the same types of regime-change operation that took place in Iran in 1953, Guatemala in 1954, Cuba in 1960-1963, Congo in 1961, and Chile in 1973, all of which the CIA steadfastly kept secret."},
 "'from the American people' removed"),
("s044","KILL_C","Flag_Waving",{1:"Those long-secret records surely contain small bits of important circumstantial evidence that further fill out the mosaic of a regime-change operation in Dallas in November 1963, the same kind of regime-change operation that took place in Iran in 1953, Guatemala in 1954, Cuba in 1960-1963, Congo in 1961, and Chile in 1973, all of which the CIA steadfastly hid from the American people."},"kept"),
("s044","INJECT","Doubt",{0:"But there has to be a reason why the CIA, whose explanations have never held up, chose to keep this particular batch of records secret for more than 50 years."},"undermines the CIA's credibility"),
("s044","INJECT_C","Doubt",{0:"But there has to be a reason why the CIA, which holds the records, chose to keep this particular batch of records secret for more than 50 years."},"same slot, neutral"),

("s045","KILL","Doubt",{0:"When Prime Minister Theresa May, who was the head of the Home Office when she banned us and was thus directly responsible for the ban, threw us under the bus in order to satiate savages who threatened violence, she made a decision about everyone’s safety."},
 "rhetorical question questioning her judgement removed; 'savages' kept"),
("s045","KILL_C","Doubt",{0:"When Prime Minister Theresa May, who headed the Home Office when she banned us and was therefore directly responsible for the ban, threw us under the bus to satiate savages who threatened violence, did she honestly believe that she or anyone else would be safe?"},"kept"),

("s046","KILL","Loaded_Language",{2:"But we worked for large bureaucracies that were slow to act."},"'ossified bureaucracies incapable of acting' neutralised"),
("s046","KILL_C","Loaded_Language",{2:"But we worked for ossified bureaucracies that were incapable of acting quickly and decisively."},"kept"),
("s046","INJECT","Appeal_to_Authority",{1:"11 who had seen warning signs — as the 9/11 Commission itself later confirmed — that something devastating might be in the planning stages."},"claim backed by an authority"),
("s046","INJECT_C","Appeal_to_Authority",{1:"11 who had seen warning signs — in several different agencies — that something devastating might be in the planning stages."},"same slot, neutral"),

("s047","KILL","Causal_Oversimplification",{6:"No. It is a long and complicated history.”"},"single divine cause for persecution removed from the quote"),
("s047","KILL_C","Causal_Oversimplification",{6:"No. It's because they're under the curse of God for having rejected the Lord Jesus Christ.”"},"kept"),

("s048","KILL","Loaded_Language",{0:"Finally, I ask you all to join me and the entire clergy of the Diocese of Madison in making public and private acts of reparation to the Most Sacred Heart of Jesus and to the Immaculate Heart of Mary for all the sins of sexual abuse committed by members of the clergy and episcopacy.",3:"19, 21, and 22) as days of fasting and abstinence in reparation for the sins committed by members of the clergy and episcopacy and I invite all the faithful to do the same.",4:"Prayer and fasting are traditional means of penance."},
 "'sexual depravity', 'outrages', 'like some demons' neutralised; NOTE: if the gold Appeal_to_Popularity span is 'join me and the entire clergy', it is kept"),
("s048","KILL_C","Loaded_Language",{0:"Finally, I ask all of you to join me and the entire clergy of the Diocese of Madison in public and private acts of reparation to the Most Sacred Heart of Jesus and the Immaculate Heart of Mary for all the sins of sexual depravity committed by members of the clergy and episcopacy.",3:"19, 21, and 22) as days of fasting and abstinence in reparation for the sins and outrages committed by clergy and bishops, and I invite all the faithful to do the same.",4:"Some sins, like some demons, can be driven out only by prayer and fasting."},"kept"),

("s050","KILL","Flag_Waving",{5:"We support the rights of the Iranian protesters.”"},"'America stands with... courageous struggle for freedom' removed"),
("s050","KILL_C","Flag_Waving",{5:"America stands with the Iranian people in their courageous struggle for freedom.”"},"kept"),

("s051","INJECT","Name_Calling-Labeling",{0:"William Jacobson explains the latest “revise” by the authorities, a pack of clueless bureaucrats, is the now infamously botched Vegas investigation:"},"labels the authorities"),
("s051","INJECT_C","Name_Calling-Labeling",{0:"William Jacobson explains the latest “revise” by the authorities, the local and federal agencies, is the now infamously botched Vegas investigation:"},"same slot, neutral"),

("s052","KILL","Exaggeration-Minimisation",{2:"Jean by claiming they found a small amount of marijuana in his house."},"'tiny bit' minimisation and 'as if this justifies... murdering them' removed"),
("s052","KILL_C","Exaggeration-Minimisation",{2:"Jean by claiming they had found a tiny bit of marijuana in his home—as if that justifies entering someone’s home and murdering them."},"kept"),
("s052","INJECT","Doubt",{0:"Dallas, TX — The Dallas Police on Thursday announced what they say are the findings of a search warrant they executed on the home of Botham Jean after he was gunned down in his apartment by one of their own."},"distancing 'what they say are' questions credibility"),
("s052","INJECT_C","Doubt",{0:"Dallas, TX — On Thursday the Dallas Police announced the results of a search warrant they executed on the home of Botham Jean after he was gunned down in his apartment by one of their own."},"same slot, neutral"),

("s054","KILL","Name_Calling-Labeling",{0:"From the mainstream Catholic perspective, the events of recent days present a terrifying prospect: the final collapse of the Novus Ordo establishment, an end to the conciliar aggiornamento and a revival of integral Tradition, which growing numbers of young people are seeking.",1:"Hence even before Archbishop Viganò had come forward, commentators like Faggioli were already sounding the air raid siren.",3:"Accordingly, he rushed to the defense of Bergoglio and his administration against “a radicalization of religious conservatism in the neo-traditionalism sense...”"},
 "'neo-Catholic' labels and 'his corrupt regime' removed; the quoted phrase is Faggioli's own"),
("s054","KILL_C","Name_Calling-Labeling",{0:"From the neo-Catholic point of view, recent events present a terrifying prospect: the final collapse of the Novus Ordo establishment, an end to the conciliar aggiornamento and a revival of integral Tradition, which growing numbers of young people are seeking.",1:"So even before Archbishop Viganò came forward, commentators such as Faggioli were already sounding the neo-Catholic air raid siren.",3:"Accordingly, he rushed to defend Bergoglio and his corrupt regime against “a radicalization of religious conservatism in the neo-traditionalism sense...”"},"kept"),
]
