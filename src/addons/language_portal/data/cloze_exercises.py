"""Static cloze exercise dataset for Grammar Pro (/my/grammar-practice).

Each entry is a dict with:
  - sentence: str  — full sentence with ___ placeholder
  - answer: str    — the correct word/phrase
  - choices: list  — 4 options (answer is one of them)
  - language: str  — 'en' or 'el'
  - category: str  — grammar category
  - level: str     — CEFR level
  - hint: str      — optional grammar tip shown on wrong answer
"""

CLOZE_EXERCISES = [

    # ================================================================
    # ENGLISH — TENSES
    # ================================================================

    # Present Simple
    {"sentence": "She ___ to work every day by bus.", "answer": "goes",
     "choices": ["go", "goes", "going", "gone"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Third person singular (he/she/it) adds -s or -es in Present Simple."},

    {"sentence": "Water ___ at 100 degrees Celsius.", "answer": "boils",
     "choices": ["boil", "boils", "boiling", "boiled"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Use Present Simple for scientific facts and general truths."},

    {"sentence": "They ___ French at school twice a week.", "answer": "study",
     "choices": ["studies", "study", "studied", "are studying"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "They/we/you/I use the base form in Present Simple."},

    {"sentence": "He ___ not like spicy food.", "answer": "does",
     "choices": ["do", "does", "did", "is"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Use does/doesn't with he/she/it in Present Simple negatives."},

    # Present Continuous
    {"sentence": "Look! The children ___ in the garden.", "answer": "are playing",
     "choices": ["play", "played", "are playing", "have played"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Use Present Continuous (am/is/are + -ing) for actions happening right now."},

    {"sentence": "I ___ a book about space exploration at the moment.", "answer": "am reading",
     "choices": ["read", "reads", "am reading", "have read"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Use Present Continuous for temporary activities in progress."},

    {"sentence": "She ___ her report right now, so don't disturb her.", "answer": "is writing",
     "choices": ["writes", "wrote", "is writing", "has written"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "'Right now' signals Present Continuous."},

    # Past Simple
    {"sentence": "Yesterday, I ___ a delicious pizza for dinner.", "answer": "ate",
     "choices": ["eat", "eats", "ate", "have eaten"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Past Simple for completed actions at a specific past time (yesterday)."},

    {"sentence": "She ___ her keys and had to call a locksmith.", "answer": "lost",
     "choices": ["loses", "lose", "lost", "has lost"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "'Lost' is the irregular past simple of 'lose'."},

    {"sentence": "They ___ a new house in the countryside last year.", "answer": "bought",
     "choices": ["buy", "buys", "bought", "have bought"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "'Bought' is the irregular past simple of 'buy'."},

    {"sentence": "The meeting ___ for three hours and everyone was exhausted.", "answer": "lasted",
     "choices": ["last", "lasts", "lasted", "was lasting"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "Past Simple for completed events with a clear duration."},

    # Past Continuous
    {"sentence": "When I called her, she ___ a bath.", "answer": "was having",
     "choices": ["had", "was having", "has had", "is having"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "Past Continuous (was/were + -ing) for an action in progress when another occurred."},

    {"sentence": "They ___ television when the power went out.", "answer": "were watching",
     "choices": ["watched", "were watching", "have watched", "watch"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "Use Past Continuous for the background action interrupted by Past Simple."},

    # Present Perfect
    {"sentence": "I ___ never seen such a beautiful sunset.", "answer": "have",
     "choices": ["had", "have", "am", "was"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "Present Perfect: have/has + past participle. 'Never' often signals Present Perfect."},

    {"sentence": "She ___ already finished her homework.", "answer": "has",
     "choices": ["is", "was", "has", "had"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "'Already' often appears with Present Perfect."},

    {"sentence": "We ___ lived in this city for ten years.", "answer": "have",
     "choices": ["are", "were", "have", "had"],
     "language": "en", "category": "tenses", "level": "B1",
     "hint": "Use Present Perfect with 'for' to describe a period continuing to the present."},

    {"sentence": "Have you ever ___ to Japan?", "answer": "been",
     "choices": ["go", "went", "been", "going"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "'Ever' signals Present Perfect. 'Been to' = visited."},

    # Past Perfect
    {"sentence": "By the time she arrived, the party ___ already ended.", "answer": "had",
     "choices": ["has", "have", "had", "was"],
     "language": "en", "category": "tenses", "level": "B1",
     "hint": "Past Perfect (had + past participle) for an action completed before another past event."},

    {"sentence": "He realized he ___ left his passport at home.", "answer": "had",
     "choices": ["has", "have", "had", "was"],
     "language": "en", "category": "tenses", "level": "B1",
     "hint": "Past Perfect shows an earlier past action."},

    # Future
    {"sentence": "I ___ call you as soon as I arrive.", "answer": "will",
     "choices": ["would", "will", "am going to", "shall"],
     "language": "en", "category": "tenses", "level": "A1",
     "hint": "Use 'will' for spontaneous decisions and promises."},

    {"sentence": "Look at those clouds! It ___ rain.", "answer": "is going to",
     "choices": ["will", "is going to", "rains", "would"],
     "language": "en", "category": "tenses", "level": "A2",
     "hint": "Use 'going to' for predictions based on present evidence."},

    {"sentence": "This time tomorrow, she ___ on a beach in Greece.", "answer": "will be lying",
     "choices": ["will lie", "will be lying", "is lying", "lies"],
     "language": "en", "category": "tenses", "level": "B1",
     "hint": "Future Continuous (will be + -ing) for actions in progress at a future moment."},

    # ================================================================
    # ENGLISH — CONDITIONALS
    # ================================================================

    {"sentence": "If it rains, we ___ the picnic.", "answer": "will cancel",
     "choices": ["cancel", "would cancel", "will cancel", "cancelled"],
     "language": "en", "category": "conditionals", "level": "A2",
     "hint": "First conditional (real future): If + Present Simple → will + base verb."},

    {"sentence": "If I ___ a million dollars, I would travel the world.", "answer": "had",
     "choices": ["have", "had", "would have", "will have"],
     "language": "en", "category": "conditionals", "level": "B1",
     "hint": "Second conditional (hypothetical): If + Past Simple → would + base verb."},

    {"sentence": "If she had studied harder, she ___ the exam.", "answer": "would have passed",
     "choices": ["would pass", "would have passed", "will pass", "had passed"],
     "language": "en", "category": "conditionals", "level": "B1",
     "hint": "Third conditional (past regret): If + Past Perfect → would have + past participle."},

    {"sentence": "If you heat ice, it ___.", "answer": "melts",
     "choices": ["would melt", "melted", "melts", "will melt"],
     "language": "en", "category": "conditionals", "level": "A1",
     "hint": "Zero conditional (facts/laws): If + Present Simple → Present Simple."},

    {"sentence": "If I ___ you, I'd apologize immediately.", "answer": "were",
     "choices": ["am", "was", "were", "be"],
     "language": "en", "category": "conditionals", "level": "B1",
     "hint": "In second conditionals, use 'were' (not 'was') for all persons (formal/correct)."},

    {"sentence": "She would feel better if she ___ more exercise.", "answer": "did",
     "choices": ["does", "do", "did", "would do"],
     "language": "en", "category": "conditionals", "level": "B1",
     "hint": "Second conditional: the if-clause uses Past Simple."},

    # ================================================================
    # ENGLISH — MODAL VERBS
    # ================================================================

    {"sentence": "You ___ smoke inside the building — it's against the rules.", "answer": "must not",
     "choices": ["should not", "must not", "do not have to", "need not"],
     "language": "en", "category": "modals", "level": "A2",
     "hint": "'Must not' = prohibition (not allowed). 'Don't have to' = not necessary."},

    {"sentence": "You ___ bring a gift — it's not a formal party.", "answer": "don't have to",
     "choices": ["must not", "cannot", "don't have to", "shouldn't"],
     "language": "en", "category": "modals", "level": "A2",
     "hint": "'Don't have to' means it's not necessary (but not forbidden)."},

    {"sentence": "She ___ speak four languages fluently.", "answer": "can",
     "choices": ["may", "must", "can", "should"],
     "language": "en", "category": "modals", "level": "A1",
     "hint": "'Can' expresses ability."},

    {"sentence": "___ I use your phone? Mine is out of battery.", "answer": "Could",
     "choices": ["Shall", "Will", "Could", "Must"],
     "language": "en", "category": "modals", "level": "A1",
     "hint": "'Could' is a polite way to ask for permission."},

    {"sentence": "You look tired. You ___ get some rest.", "answer": "should",
     "choices": ["must", "shall", "should", "may"],
     "language": "en", "category": "modals", "level": "A2",
     "hint": "'Should' gives advice or recommendation."},

    {"sentence": "That ___ be Maria at the door — she said she'd come at six.", "answer": "must",
     "choices": ["may", "might", "must", "should"],
     "language": "en", "category": "modals", "level": "B1",
     "hint": "'Must' expresses near-certainty based on evidence."},

    {"sentence": "It ___ rain later — take an umbrella just in case.", "answer": "might",
     "choices": ["must", "will", "might", "shall"],
     "language": "en", "category": "modals", "level": "A2",
     "hint": "'Might' expresses possibility (less certain than 'may')."},

    # ================================================================
    # ENGLISH — ARTICLES
    # ================================================================

    {"sentence": "I saw ___ interesting film last night.", "answer": "an",
     "choices": ["a", "an", "the", "—"],
     "language": "en", "category": "articles", "level": "A1",
     "hint": "Use 'an' before words starting with a vowel sound."},

    {"sentence": "___ sun rises in the east.", "answer": "The",
     "choices": ["A", "An", "The", "—"],
     "language": "en", "category": "articles", "level": "A1",
     "hint": "Use 'the' for unique things (there is only one sun)."},

    {"sentence": "She is ___ doctor and her husband is ___ engineer.", "answer": "a / an",
     "choices": ["a / an", "the / the", "an / a", "— / —"],
     "language": "en", "category": "articles", "level": "A1",
     "hint": "'A' before consonant sounds, 'an' before vowel sounds. Use indefinite for jobs."},

    {"sentence": "He plays ___ guitar beautifully.", "answer": "the",
     "choices": ["a", "an", "the", "—"],
     "language": "en", "category": "articles", "level": "A2",
     "hint": "Use 'the' with musical instruments."},

    {"sentence": "We had ___ dinner at a lovely restaurant.", "answer": "—",
     "choices": ["a", "an", "the", "—"],
     "language": "en", "category": "articles", "level": "A2",
     "hint": "No article with meals (breakfast, lunch, dinner) in general."},

    {"sentence": "I love ___ music, especially jazz.", "answer": "—",
     "choices": ["a", "an", "the", "—"],
     "language": "en", "category": "articles", "level": "A2",
     "hint": "No article with uncountable nouns used in a general sense."},

    # ================================================================
    # ENGLISH — PASSIVE VOICE
    # ================================================================

    {"sentence": "The Eiffel Tower ___ in 1889.", "answer": "was built",
     "choices": ["built", "was built", "has built", "is built"],
     "language": "en", "category": "passive", "level": "A2",
     "hint": "Passive voice: was/were + past participle. Use for past events."},

    {"sentence": "English ___ as an official language in over 50 countries.", "answer": "is spoken",
     "choices": ["speaks", "is spoken", "was spoken", "has spoken"],
     "language": "en", "category": "passive", "level": "A2",
     "hint": "Passive Present Simple: am/is/are + past participle."},

    {"sentence": "The report ___ by the team before Friday.", "answer": "will be submitted",
     "choices": ["will submit", "will be submitted", "submits", "is submitted"],
     "language": "en", "category": "passive", "level": "B1",
     "hint": "Future passive: will be + past participle."},

    {"sentence": "Several mistakes ___ in the document by the editor.", "answer": "were found",
     "choices": ["found", "have found", "were found", "are finding"],
     "language": "en", "category": "passive", "level": "B1",
     "hint": "Past passive: was/were + past participle."},

    # ================================================================
    # ENGLISH — REPORTED SPEECH
    # ================================================================

    {"sentence": "She said she ___ tired.", "answer": "was",
     "choices": ["is", "was", "has been", "will be"],
     "language": "en", "category": "reported_speech", "level": "A2",
     "hint": "In reported speech, Present Simple → Past Simple (backshift)."},

    {"sentence": "He told me he ___ go to the party.", "answer": "would",
     "choices": ["will", "would", "shall", "is going to"],
     "language": "en", "category": "reported_speech", "level": "A2",
     "hint": "In reported speech, 'will' → 'would' (backshift)."},

    {"sentence": "She asked me where I ___.", "answer": "lived",
     "choices": ["live", "lived", "had lived", "am living"],
     "language": "en", "category": "reported_speech", "level": "B1",
     "hint": "In reported questions, Present Simple → Past Simple. No inversion."},

    {"sentence": "He said that he ___ never been to Paris.", "answer": "had",
     "choices": ["has", "have", "had", "was"],
     "language": "en", "category": "reported_speech", "level": "B1",
     "hint": "In reported speech, Present Perfect → Past Perfect."},

    # ================================================================
    # ENGLISH — IRREGULAR VERBS
    # ================================================================

    {"sentence": "I ___ a lot of money on clothes last month.", "answer": "spent",
     "choices": ["spend", "spended", "spent", "has spent"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: spend → spent → spent."},

    {"sentence": "She ___ the letter and put it in her bag.", "answer": "wrote",
     "choices": ["writed", "write", "wrote", "written"],
     "language": "en", "category": "irregular_verbs", "level": "A1",
     "hint": "Irregular: write → wrote → written."},

    {"sentence": "They ___ swimming in the lake yesterday.", "answer": "went",
     "choices": ["goed", "go", "gone", "went"],
     "language": "en", "category": "irregular_verbs", "level": "A1",
     "hint": "Irregular: go → went → gone."},

    {"sentence": "He ___ the window by mistake.", "answer": "broke",
     "choices": ["breaked", "brake", "broke", "broken"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: break → broke → broken."},

    {"sentence": "I have ___ all my vegetables.", "answer": "eaten",
     "choices": ["ate", "eating", "eat", "eaten"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: eat → ate → eaten. Use 'eaten' (past participle) with 'have'."},

    {"sentence": "She ___ the news and immediately called her mother.", "answer": "heard",
     "choices": ["heared", "hear", "herd", "heard"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: hear → heard → heard."},

    {"sentence": "The children have ___ all the cookies.", "answer": "taken",
     "choices": ["took", "take", "taken", "taking"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: take → took → taken."},

    {"sentence": "He ___ his car to the mechanic this morning.", "answer": "brought",
     "choices": ["bringed", "bring", "brought", "brung"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: bring → brought → brought."},

    {"sentence": "They ___ a great idea during the meeting.", "answer": "had",
     "choices": ["haved", "have", "had", "has"],
     "language": "en", "category": "irregular_verbs", "level": "A1",
     "hint": "Irregular: have → had → had."},

    {"sentence": "I ___ my wallet on the bus last week.", "answer": "left",
     "choices": ["leaved", "leave", "left", "lefted"],
     "language": "en", "category": "irregular_verbs", "level": "A2",
     "hint": "Irregular: leave → left → left."},

    # ================================================================
    # ENGLISH — PREPOSITIONS
    # ================================================================

    {"sentence": "She has been working here ___ 2018.", "answer": "since",
     "choices": ["for", "since", "from", "during"],
     "language": "en", "category": "prepositions", "level": "A2",
     "hint": "Use 'since' with a specific point in time; 'for' with a duration."},

    {"sentence": "I've been waiting ___ two hours!", "answer": "for",
     "choices": ["since", "from", "for", "during"],
     "language": "en", "category": "prepositions", "level": "A2",
     "hint": "Use 'for' with a duration (two hours = a period of time)."},

    {"sentence": "The concert is ___ Saturday evening.", "answer": "on",
     "choices": ["in", "at", "on", "by"],
     "language": "en", "category": "prepositions", "level": "A1",
     "hint": "Use 'on' with days (on Monday, on Saturday)."},

    {"sentence": "She was born ___ July.", "answer": "in",
     "choices": ["on", "at", "in", "by"],
     "language": "en", "category": "prepositions", "level": "A1",
     "hint": "Use 'in' with months and years."},

    {"sentence": "The shop closes ___ midnight.", "answer": "at",
     "choices": ["in", "on", "at", "by"],
     "language": "en", "category": "prepositions", "level": "A1",
     "hint": "Use 'at' with clock times and specific points (at noon, at midnight)."},

    {"sentence": "He is interested ___ learning new languages.", "answer": "in",
     "choices": ["at", "about", "in", "on"],
     "language": "en", "category": "prepositions", "level": "A2",
     "hint": "'Interested in' is a fixed phrase."},

    {"sentence": "She is very good ___ playing chess.", "answer": "at",
     "choices": ["in", "at", "on", "with"],
     "language": "en", "category": "prepositions", "level": "A2",
     "hint": "'Good at' is the correct collocation for skills."},

    # ================================================================
    # ENGLISH — WORD CHOICE / VOCABULARY
    # ================================================================

    {"sentence": "Could you please ___ me how to get to the station?", "answer": "tell",
     "choices": ["say", "speak", "tell", "talk"],
     "language": "en", "category": "vocabulary", "level": "A1",
     "hint": "'Tell' is followed by a person: tell me, tell her. 'Say' is followed by words."},

    {"sentence": "He ___ a decision without consulting anyone.", "answer": "made",
     "choices": ["did", "made", "had", "took"],
     "language": "en", "category": "vocabulary", "level": "A2",
     "hint": "'Make a decision' is the correct collocation."},

    {"sentence": "She ___ a mistake in her calculations.", "answer": "made",
     "choices": ["did", "made", "had", "took"],
     "language": "en", "category": "vocabulary", "level": "A1",
     "hint": "'Make a mistake' (not 'do a mistake') is the correct collocation."},

    {"sentence": "Please ___ a seat — the doctor will see you shortly.", "answer": "take",
     "choices": ["make", "do", "take", "have"],
     "language": "en", "category": "vocabulary", "level": "A2",
     "hint": "'Take a seat' is the standard invitation to sit down."},

    {"sentence": "I need to ___ some research before I write the essay.", "answer": "do",
     "choices": ["make", "do", "have", "take"],
     "language": "en", "category": "vocabulary", "level": "A2",
     "hint": "'Do research' is the correct collocation. 'Do homework/exercise/business'."},

    # ================================================================
    # ENGLISH — ADVANCED (B2)
    # ================================================================

    {"sentence": "Had I known about the traffic, I ___ earlier.", "answer": "would have left",
     "choices": ["would leave", "would have left", "had left", "left"],
     "language": "en", "category": "conditionals", "level": "B2",
     "hint": "Inverted third conditional: Had I known... = If I had known..."},

    {"sentence": "By next month, she ___ here for exactly two years.", "answer": "will have been working",
     "choices": ["will work", "will have worked", "will be working", "will have been working"],
     "language": "en", "category": "tenses", "level": "B2",
     "hint": "Future Perfect Continuous: will have been + -ing, for duration up to a future point."},

    {"sentence": "The project ___ by the time the investors arrive tomorrow.", "answer": "will have been completed",
     "choices": ["will complete", "will have completed", "will have been completed", "is completed"],
     "language": "en", "category": "passive", "level": "B2",
     "hint": "Future Perfect Passive: will have been + past participle."},

    {"sentence": "She suggested ___ to a different approach.", "answer": "switching",
     "choices": ["to switch", "switch", "switched", "switching"],
     "language": "en", "category": "vocabulary", "level": "B1",
     "hint": "'Suggest' is followed by a gerund (-ing form), not an infinitive."},

    {"sentence": "He denied ___ the money from the safe.", "answer": "taking",
     "choices": ["to take", "take", "taken", "taking"],
     "language": "en", "category": "vocabulary", "level": "B1",
     "hint": "'Deny' is followed by a gerund (-ing form)."},

    {"sentence": "I'd rather you ___ wait outside.", "answer": "didn't",
     "choices": ["don't", "didn't", "won't", "wouldn't"],
     "language": "en", "category": "vocabulary", "level": "B2",
     "hint": "'Would rather + subject + Past Simple' for preferences about others' actions."},

    # ================================================================
    # GREEK — PRESENT TENSE
    # ================================================================

    {"sentence": "Εγώ ___ στην Αθήνα.", "answer": "μένω",
     "choices": ["μένω", "μένεις", "μένει", "μένουμε"],
     "language": "el", "category": "tenses", "level": "A1",
     "hint": "Πρώτο πρόσωπο ενικός: εγώ μένω (I live/stay)."},

    {"sentence": "Αυτός ___ καφέ κάθε πρωί.", "answer": "πίνει",
     "choices": ["πίνω", "πίνεις", "πίνει", "πίνουν"],
     "language": "el", "category": "tenses", "level": "A1",
     "hint": "Τρίτο πρόσωπο ενικός: αυτός πίνει (he drinks)."},

    {"sentence": "Εμείς ___ ελληνικά στο σχολείο.", "answer": "μαθαίνουμε",
     "choices": ["μαθαίνω", "μαθαίνεις", "μαθαίνει", "μαθαίνουμε"],
     "language": "el", "category": "tenses", "level": "A1",
     "hint": "Πρώτο πρόσωπο πληθυντικός: εμείς μαθαίνουμε (we learn)."},

    {"sentence": "Τα παιδιά ___ στο πάρκο.", "answer": "παίζουν",
     "choices": ["παίζω", "παίζει", "παίζουν", "παίζεις"],
     "language": "el", "category": "tenses", "level": "A1",
     "hint": "Τρίτο πρόσωπο πληθυντικός: αυτοί παίζουν (they play)."},

    {"sentence": "Εσύ ___ σε ένα εστιατόριο;", "answer": "δουλεύεις",
     "choices": ["δουλεύω", "δουλεύεις", "δουλεύει", "δουλεύουν"],
     "language": "el", "category": "tenses", "level": "A1",
     "hint": "Δεύτερο πρόσωπο ενικός: εσύ δουλεύεις (you work)."},

    # ================================================================
    # GREEK — ARTICLES
    # ================================================================

    {"sentence": "___ γυναίκα διαβάζει ένα βιβλίο.", "answer": "Η",
     "choices": ["Ο", "Η", "Το", "Ένας"],
     "language": "el", "category": "articles", "level": "A1",
     "hint": "Η γυναίκα — θηλυκό ουσιαστικό (feminine noun). Ο for masculine, Το for neuter."},

    {"sentence": "___ άνδρας μιλάει τηλέφωνο.", "answer": "Ο",
     "choices": ["Ο", "Η", "Το", "Ένα"],
     "language": "el", "category": "articles", "level": "A1",
     "hint": "Ο άνδρας — αρσενικό ουσιαστικό (masculine noun)."},

    {"sentence": "___ παιδί παίζει στον κήπο.", "answer": "Το",
     "choices": ["Ο", "Η", "Το", "Ένας"],
     "language": "el", "category": "articles", "level": "A1",
     "hint": "Το παιδί — ουδέτερο ουσιαστικό (neuter noun)."},

    {"sentence": "Θέλω ___ καφέ, παρακαλώ.", "answer": "έναν",
     "choices": ["ένα", "μια", "έναν", "τον"],
     "language": "el", "category": "articles", "level": "A1",
     "hint": "Έναν/ένα — αόριστο άρθρο (indefinite article). Καφές is masculine → έναν."},

    # ================================================================
    # GREEK — PAST TENSE (Αόριστος)
    # ================================================================

    {"sentence": "Χθες ___ στη θάλασσα.", "answer": "πήγαμε",
     "choices": ["πάμε", "πήγαμε", "πηγαίνουμε", "πήγαν"],
     "language": "el", "category": "tenses", "level": "A2",
     "hint": "Αόριστος, πρώτο πρόσωπο πληθυντικός: εμείς πήγαμε (we went). Χθες = yesterday."},

    {"sentence": "Η Μαρία ___ ένα ωραίο φόρεμα χθες.", "answer": "φόρεσε",
     "choices": ["φοράει", "φόρεσε", "φορούσε", "θα φορέσει"],
     "language": "el", "category": "tenses", "level": "A2",
     "hint": "Αόριστος για ολοκληρωμένη πράξη στο παρελθόν: φόρεσε (she wore)."},

    {"sentence": "Οι φοιτητές ___ σκληρά για τις εξετάσεις.", "answer": "μελέτησαν",
     "choices": ["μελετούν", "μελέτησαν", "μελετούσαν", "μελέτησε"],
     "language": "el", "category": "tenses", "level": "A2",
     "hint": "Αόριστος τρίτου πληθυντικού: αυτοί μελέτησαν (they studied)."},

    # ================================================================
    # GREEK — FUTURE TENSE
    # ================================================================

    {"sentence": "Αύριο ___ στην Αθήνα.", "answer": "θα πάω",
     "choices": ["πάω", "θα πάω", "πήγα", "θα πήγα"],
     "language": "el", "category": "tenses", "level": "A2",
     "hint": "Μέλλοντας: θα + ρήμα (θα πάω = I will go). Αύριο = tomorrow."},

    {"sentence": "Το εστιατόριο ___ στις 10 το βράδυ.", "answer": "θα κλείσει",
     "choices": ["κλείνει", "έκλεισε", "θα κλείσει", "κλείσει"],
     "language": "el", "category": "tenses", "level": "A2",
     "hint": "Μέλλοντας (Future): θα + αόριστος/υποτακτική — θα κλείσει (it will close)."},

    # ================================================================
    # GREEK — VOCABULARY
    # ================================================================

    {"sentence": "Πού είναι το ___; Θέλω να κάνω ντους.", "answer": "μπάνιο",
     "choices": ["κρεβατοκάμαρα", "κουζίνα", "σαλόνι", "μπάνιο"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Μπάνιο = bathroom. Κρεβατοκάμαρα = bedroom. Κουζίνα = kitchen. Σαλόνι = living room."},

    {"sentence": "Πόσο ___ αυτό το παπούτσι;", "answer": "κάνει",
     "choices": ["είναι", "κάνει", "έχει", "στοιχίζει"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Πόσο κάνει; = How much does it cost? (Κάνει = it costs/it is worth)."},

    {"sentence": "Η Ελλάδα είναι μια ___ χώρα.", "answer": "όμορφη",
     "choices": ["ωραία", "όμορφη", "καλή", "μεγάλη"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Όμορφη = beautiful. Ωραία = nice/fine. Καλή = good. Μεγάλη = big/large."},

    {"sentence": "Θέλω να ___ νερό.", "answer": "πιω",
     "choices": ["πίνω", "πιω", "ήπια", "πιει"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Θέλω να πιω = I want to drink. 'Να πιω' is the subjunctive form."},

    {"sentence": "Η ___ του τρένου είναι στις 14:30.", "answer": "αναχώρηση",
     "choices": ["άφιξη", "αναχώρηση", "εισιτήριο", "σταθμός"],
     "language": "el", "category": "vocabulary", "level": "A2",
     "hint": "Αναχώρηση = departure. Άφιξη = arrival. Εισιτήριο = ticket. Σταθμός = station."},

    {"sentence": "___ νιώθεις σήμερα;", "answer": "Πώς",
     "choices": ["Πού", "Πώς", "Πότε", "Γιατί"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Πώς νιώθεις; = How do you feel? Πού = where, Πότε = when, Γιατί = why."},

    {"sentence": "Μου αρέσει ___ να διαβάζω βιβλία.", "answer": "πολύ",
     "choices": ["λίγο", "πολύ", "ποτέ", "πάντα"],
     "language": "el", "category": "vocabulary", "level": "A1",
     "hint": "Μου αρέσει πολύ = I like it very much. Πολύ = very/a lot."},

    # ================================================================
    # GREEK — ADJECTIVE AGREEMENT
    # ================================================================

    {"sentence": "Έχω έναν ___ φίλο.", "answer": "καλό",
     "choices": ["καλός", "καλή", "καλό", "καλά"],
     "language": "el", "category": "grammar", "level": "A2",
     "hint": "Φίλος is masculine. Αιτιατική αρσενικού: καλό (accusative masculine)."},

    {"sentence": "Αυτό είναι ένα ___ βιβλίο.", "answer": "ενδιαφέρον",
     "choices": ["ενδιαφέρων", "ενδιαφέρουσα", "ενδιαφέρον", "ενδιαφέροντα"],
     "language": "el", "category": "grammar", "level": "A2",
     "hint": "Βιβλίο is neuter. Nominative neuter: ενδιαφέρον (interesting)."},

    # ================================================================
    # ENGLISH — MIXED ADVANCED
    # ================================================================

    {"sentence": "Despite ___ hard all day, she didn't finish the project.", "answer": "working",
     "choices": ["work", "worked", "working", "to work"],
     "language": "en", "category": "vocabulary", "level": "B1",
     "hint": "'Despite' is followed by a noun or gerund (-ing form), not a clause."},

    {"sentence": "Neither the manager nor the employees ___ aware of the problem.", "answer": "were",
     "choices": ["was", "were", "are", "is"],
     "language": "en", "category": "grammar", "level": "B1",
     "hint": "With 'neither...nor', the verb agrees with the noun closest to it (employees → were)."},

    {"sentence": "It's high time we ___ this issue seriously.", "answer": "took",
     "choices": ["take", "took", "have taken", "taking"],
     "language": "en", "category": "grammar", "level": "B2",
     "hint": "'It's high time + subject + Past Simple' (subjunctive mood)."},

    {"sentence": "Hardly ___ she arrived when the meeting started.", "answer": "had",
     "choices": ["did", "had", "has", "was"],
     "language": "en", "category": "grammar", "level": "B2",
     "hint": "'Hardly had + subject + past participle when...' — inverted past perfect."},

    {"sentence": "The more you practice, ___ you become.", "answer": "the better",
     "choices": ["better", "the better", "more better", "the best"],
     "language": "en", "category": "grammar", "level": "B1",
     "hint": "'The more... the more/better/faster...' is a fixed comparative structure."},

    {"sentence": "She's used to ___ early — she does it every day.", "answer": "getting up",
     "choices": ["get up", "getting up", "got up", "have got up"],
     "language": "en", "category": "vocabulary", "level": "B1",
     "hint": "'Be used to' + gerund (-ing) = be accustomed to. Compare: 'used to + base verb' for past habits."},

    {"sentence": "I wish I ___ fly — I'd visit every country!", "answer": "could",
     "choices": ["can", "could", "would", "should"],
     "language": "en", "category": "grammar", "level": "B1",
     "hint": "'Wish + could' for regret about present inability."},

    {"sentence": "If only he ___ told me the truth from the beginning.", "answer": "had",
     "choices": ["has", "have", "had", "was"],
     "language": "en", "category": "grammar", "level": "B2",
     "hint": "'If only + Past Perfect' expresses regret about past events."},

    {"sentence": "Not until she opened the door ___ the surprise waiting for her.", "answer": "did she see",
     "choices": ["she saw", "did she see", "she had seen", "had she seen"],
     "language": "en", "category": "grammar", "level": "B2",
     "hint": "Fronted negative adverbial 'Not until...' requires subject-auxiliary inversion."},

    {"sentence": "He was ___ tired that he fell asleep at the table.", "answer": "so",
     "choices": ["such", "so", "very", "too"],
     "language": "en", "category": "grammar", "level": "A2",
     "hint": "'So + adjective + that'. 'Such + (a/an) + noun + that'."},

    {"sentence": "It was ___ a long film that we missed the last train.", "answer": "such",
     "choices": ["so", "such", "too", "very"],
     "language": "en", "category": "grammar", "level": "A2",
     "hint": "'Such + a/an + adjective + noun + that'. Compare: 'so + adjective + that'."},

]


CATEGORIES = {
    "tenses": "Verb Tenses",
    "conditionals": "Conditionals",
    "modals": "Modal Verbs",
    "articles": "Articles",
    "passive": "Passive Voice",
    "reported_speech": "Reported Speech",
    "irregular_verbs": "Irregular Verbs",
    "prepositions": "Prepositions",
    "vocabulary": "Vocabulary & Collocations",
    "grammar": "Grammar",
}

LEVELS = ["A1", "A2", "B1", "B2"]
LANGUAGES = {"en": "English", "el": "Greek"}
