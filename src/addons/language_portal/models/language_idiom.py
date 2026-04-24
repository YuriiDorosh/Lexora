from odoo import models, fields


IDIOM_SEED_DATA = [
    # ── English phrasal verbs ──────────────────────────────────────────────
    {
        'expression': 'break up',
        'literal_meaning': 'to physically break something into pieces',
        'idiomatic_meaning': 'to end a romantic relationship',
        'example': 'She broke up with her boyfriend after two years together.',
        'language': 'en',
        'category': 'relationships',
        'level': 'A2',
        'origin_note': 'Phrasal verb; figurative sense of splitting apart.',
    },
    {
        'expression': 'give up',
        'literal_meaning': 'to hand something over',
        'idiomatic_meaning': 'to stop trying; to quit',
        'example': "Don't give up — you're almost there!",
        'language': 'en',
        'category': 'work',
        'level': 'A2',
        'origin_note': '',
    },
    {
        'expression': 'run out of',
        'literal_meaning': 'to run outside of a container',
        'idiomatic_meaning': 'to have no more of something left',
        'example': 'We ran out of coffee, so I went to the shop.',
        'language': 'en',
        'category': 'daily_life',
        'level': 'A2',
        'origin_note': '',
    },
    {
        'expression': 'look up',
        'literal_meaning': 'to raise your eyes toward the ceiling',
        'idiomatic_meaning': 'to search for information in a book or online',
        'example': 'If you do not know the word, look it up in a dictionary.',
        'language': 'en',
        'category': 'learning',
        'level': 'A2',
        'origin_note': '',
    },
    {
        'expression': 'come across',
        'literal_meaning': 'to cross from one side to another',
        'idiomatic_meaning': 'to find or meet by chance',
        'example': 'I came across an old photo while cleaning my room.',
        'language': 'en',
        'category': 'daily_life',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'turn down',
        'literal_meaning': 'to rotate something downward',
        'idiomatic_meaning': 'to refuse or reject an offer',
        'example': 'She turned down the job offer because the salary was too low.',
        'language': 'en',
        'category': 'work',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'put off',
        'literal_meaning': 'to remove an object from a surface',
        'idiomatic_meaning': 'to postpone; to delay doing something',
        'example': 'Stop putting off your homework — do it now.',
        'language': 'en',
        'category': 'work',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'get along with',
        'literal_meaning': 'to move forward together',
        'idiomatic_meaning': 'to have a friendly relationship with someone',
        'example': 'I get along well with my colleagues at work.',
        'language': 'en',
        'category': 'relationships',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'bring up',
        'literal_meaning': 'to carry something to a higher place',
        'idiomatic_meaning': 'to raise a child; or to mention a topic in conversation',
        'example': 'She brought up an interesting point during the meeting.',
        'language': 'en',
        'category': 'communication',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'let down',
        'literal_meaning': 'to lower something on a rope',
        'idiomatic_meaning': 'to disappoint someone',
        'example': 'He let me down by not showing up to the event.',
        'language': 'en',
        'category': 'emotions',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'figure out',
        'literal_meaning': 'to draw a figure or shape',
        'idiomatic_meaning': 'to understand something after thinking about it',
        'example': 'I finally figured out how to solve the puzzle.',
        'language': 'en',
        'category': 'learning',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'stand out',
        'literal_meaning': 'to physically stand outside',
        'idiomatic_meaning': 'to be noticeably different or better than others',
        'example': 'Her red coat made her stand out in the crowd.',
        'language': 'en',
        'category': 'daily_life',
        'level': 'B2',
        'origin_note': '',
    },
    {
        'expression': 'kick the bucket',
        'literal_meaning': 'to kick a bucket with your foot',
        'idiomatic_meaning': 'to die (informal, humorous)',
        'example': 'He kicked the bucket at the grand age of 102.',
        'language': 'en',
        'category': 'emotions',
        'level': 'C1',
        'origin_note': 'Possible origin: a beam called a bucket used in executions.',
    },
    {
        'expression': 'bite the bullet',
        'literal_meaning': 'to bite on a bullet',
        'idiomatic_meaning': 'to endure a painful situation with courage',
        'example': 'I had to bite the bullet and apologize even though I was angry.',
        'language': 'en',
        'category': 'emotions',
        'level': 'B2',
        'origin_note': 'From pre-anaesthetic surgery where patients bit a bullet to endure pain.',
    },
    {
        'expression': 'spill the beans',
        'literal_meaning': 'to knock over a container of beans',
        'idiomatic_meaning': 'to reveal a secret accidentally',
        'example': 'Who spilled the beans about the surprise party?',
        'language': 'en',
        'category': 'communication',
        'level': 'B2',
        'origin_note': 'Origin unclear; possibly from ancient Greek voting using beans.',
    },
    # ── Greek idioms ───────────────────────────────────────────────────────
    {
        'expression': 'τρώω κόσμο',
        'literal_meaning': 'to eat the world',
        'idiomatic_meaning': 'to travel extensively; to see a lot of the world',
        'example': 'Ταξιδεύει συνέχεια — έχει φάει κόσμο.',
        'language': 'el',
        'category': 'daily_life',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'μου κόστισε ακριβά',
        'literal_meaning': 'it cost me dearly',
        'idiomatic_meaning': 'to pay a heavy price — financially or emotionally',
        'example': 'Η απόφασή μου μου κόστισε ακριβά.',
        'language': 'el',
        'category': 'emotions',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'πάω με τον νου μου',
        'literal_meaning': 'I go with my mind',
        'idiomatic_meaning': 'to daydream; to be lost in thought',
        'example': 'Συγγνώμη, έφυγα με τον νου μου. Τι είπες;',
        'language': 'el',
        'category': 'emotions',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'κόβω το μάτι μου',
        'literal_meaning': 'to cut my eye',
        'idiomatic_meaning': 'to have a strong desire for something you see',
        'example': 'Μου κόβει το μάτι αυτό το φόρεμα στη βιτρίνα.',
        'language': 'el',
        'category': 'daily_life',
        'level': 'B2',
        'origin_note': '',
    },
    {
        'expression': 'βάζω τα δυνατά μου',
        'literal_meaning': 'to put my strong things in',
        'idiomatic_meaning': 'to do one\'s best; to try as hard as possible',
        'example': 'Θα βάλω τα δυνατά μου για να περάσω τις εξετάσεις.',
        'language': 'el',
        'category': 'work',
        'level': 'A2',
        'origin_note': '',
    },
    {
        'expression': 'τρώω τον κόσμο στο ξύλο',
        'literal_meaning': 'to eat the world with a stick',
        'idiomatic_meaning': 'to claim one can do impossible things (all talk, no action)',
        'example': 'Λέει ότι τρώει τον κόσμο στο ξύλο, αλλά δεν κάνει τίποτα.',
        'language': 'el',
        'category': 'communication',
        'level': 'B2',
        'origin_note': '',
    },
    {
        'expression': 'δεν πάει ο νους μου',
        'literal_meaning': 'my mind does not go there',
        'idiomatic_meaning': 'I cannot imagine it; it is inconceivable to me',
        'example': 'Δεν πάει ο νους μου πώς άλλαξε τόσο πολύ.',
        'language': 'el',
        'category': 'emotions',
        'level': 'B2',
        'origin_note': '',
    },
    {
        'expression': 'παίζω στα δάχτυλά μου',
        'literal_meaning': 'I play it on my fingers',
        'idiomatic_meaning': 'to know something perfectly; to have it mastered',
        'example': 'Το τραγούδι το παίζω στα δάχτυλά μου.',
        'language': 'el',
        'category': 'learning',
        'level': 'B1',
        'origin_note': '',
    },
    {
        'expression': 'ρίχνω νερό στο μύλο',
        'literal_meaning': 'to pour water into the mill',
        'idiomatic_meaning': 'to benefit someone (often unintentionally); to play into someone\'s hands',
        'example': 'Η δήλωσή σου ρίχνει νερό στο μύλο των αντιπάλων μας.',
        'language': 'el',
        'category': 'communication',
        'level': 'C1',
        'origin_note': '',
    },
    {
        'expression': 'βλέπω τα άστρα μεσημέρι',
        'literal_meaning': 'to see stars at noon',
        'idiomatic_meaning': 'to be in great pain; to see stars (from pain or shock)',
        'example': 'Χτύπησα το κεφάλι μου και είδα τα άστρα μεσημέρι.',
        'language': 'el',
        'category': 'emotions',
        'level': 'B2',
        'origin_note': '',
    },
]


class LanguageIdiom(models.Model):
    _name = 'language.idiom'
    _description = 'Idiom / Phrasal Verb'
    _order = 'language, level, expression'
    _rec_name = 'expression'

    expression = fields.Char(string='Expression', required=True, index=True)
    literal_meaning = fields.Char(string='Literal Meaning')
    idiomatic_meaning = fields.Text(string='Idiomatic Meaning', required=True)
    example = fields.Text(string='Example Sentence')
    language = fields.Selection(
        [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek')],
        string='Language', required=True, index=True,
    )
    category = fields.Selection(
        [
            ('daily_life', 'Daily Life'),
            ('emotions', 'Emotions'),
            ('work', 'Work & Career'),
            ('relationships', 'Relationships'),
            ('communication', 'Communication'),
            ('learning', 'Learning'),
            ('money', 'Money'),
            ('other', 'Other'),
        ],
        string='Category', required=True, default='other',
    )
    level = fields.Selection(
        [('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')],
        string='CEFR Level', required=True, default='B1',
    )
    origin_note = fields.Text(string='Origin / Etymology Note')

    _sql_constraints = [
        ('expression_lang_uniq', 'UNIQUE(expression, language)',
         'This expression already exists for this language.'),
    ]

    def _seed(self):
        existing = set(
            self.sudo().search([]).mapped(lambda r: (r.expression, r.language))
        )
        to_create = [
            d for d in IDIOM_SEED_DATA
            if (d['expression'], d['language']) not in existing
        ]
        if to_create:
            self.sudo().create(to_create)
        return len(to_create)
