from odoo.tests.common import TransactionCase

from odoo.addons.language_lessons.models.lesson_parser import parse_lesson_text


class TestLessonParser(TransactionCase):
    """Pure-function tests for the rule-based lesson parser (ADR-038 § 38a).

    No ORM/database interaction is exercised here on purpose — the parser
    itself has no Odoo dependency.
    """

    def test_topic_marker(self):
        result = parse_lesson_text('Topic: Travel & Airports\nVocab:\n- apple')
        self.assertEqual(result['topic'], 'Travel & Airports')

    def test_topic_marker_no_inline_value(self):
        result = parse_lesson_text('Topic:\nVocab:\n- apple')
        self.assertIsNone(result['topic'])

    def test_vocab_equals_separator(self):
        result = parse_lesson_text('Vocab:\n- boarding pass = посадковий талон')
        item = result['items'][0]
        self.assertEqual(item['item_type'], 'vocab')
        self.assertEqual(item['text'], 'boarding pass')
        self.assertEqual(item['translation_hint'], 'посадковий талон')

    def test_vocab_dash_separator(self):
        result = parse_lesson_text('Vocab:\n- to check in - реєструватися')
        item = result['items'][0]
        self.assertEqual(item['text'], 'to check in')
        self.assertEqual(item['translation_hint'], 'реєструватися')

    def test_hyphenated_word_not_split_on_bare_hyphen(self):
        result = parse_lesson_text('Vocab:\n- check-in')
        item = result['items'][0]
        self.assertEqual(item['text'], 'check-in')
        self.assertIsNone(item['translation_hint'])

    def test_vocab_no_translation(self):
        result = parse_lesson_text('Vocab:\n- layover')
        item = result['items'][0]
        self.assertEqual(item['text'], 'layover')
        self.assertIsNone(item['translation_hint'])

    def test_phrases_section(self):
        result = parse_lesson_text("Phrases:\n- I'm running late")
        item = result['items'][0]
        self.assertEqual(item['item_type'], 'phrase')
        self.assertEqual(item['text'], "I'm running late")

    def test_mistakes_arrow_unicode(self):
        result = parse_lesson_text(
            'Mistakes:\n- I go to the airport yesterday → I went to the airport yesterday'
        )
        item = result['items'][0]
        self.assertEqual(item['item_type'], 'correction')
        self.assertEqual(item['text'], 'I go to the airport yesterday')
        self.assertEqual(item['corrected_text'], 'I went to the airport yesterday')

    def test_mistakes_ascii_arrow(self):
        result = parse_lesson_text("Mistakes:\n- She don't like it -> She doesn't like it")
        item = result['items'][0]
        self.assertEqual(item['text'], "She don't like it")
        self.assertEqual(item['corrected_text'], "She doesn't like it")

    def test_grammar_section(self):
        result = parse_lesson_text('Grammar:\n- Past Simple vs Present Perfect')
        item = result['items'][0]
        self.assertEqual(item['item_type'], 'grammar')
        self.assertEqual(item['text'], 'Past Simple vs Present Perfect')

    def test_notes_section(self):
        result = parse_lesson_text('Notes:\n- Remember to review this next week')
        item = result['items'][0]
        self.assertEqual(item['item_type'], 'note')

    def test_case_insensitive_with_colon(self):
        result = parse_lesson_text('VOCAB:\n- apple\nvocabulary:\n- banana')
        self.assertEqual(len(result['items']), 2)
        self.assertTrue(all(i['item_type'] == 'vocab' for i in result['items']))
        self.assertTrue(result['markers_found'])

    def test_colon_is_required_for_a_marker(self):
        """ADR-038 § 38h: a keyword with NO colon is not a marker — it
        falls through to the no-section heuristic like any other line."""
        result = parse_lesson_text('Vocab\n- apple')
        self.assertFalse(result['markers_found'])
        # Both lines land via the heuristic (no active section was ever set).
        self.assertEqual([i['text'] for i in result['items']], ['Vocab', 'apple'])

    def test_lone_table_cell_word_is_not_treated_as_a_marker(self):
        """Regression test for a real production bug: a copy-pasted table
        header row ("Function | Phrase | Example") becomes three separate
        lines when pasted as plain text. Without a mandatory colon, the
        bare word "Phrase" false-positive-matched the marker regex,
        flipped the parser into the phrases section, and corrupted every
        line that followed (caught live on 2026-09-23 against a real
        user-supplied Preply lesson)."""
        result = parse_lesson_text('Function\nPhrase\nExample')
        self.assertFalse(result['markers_found'])
        self.assertEqual(len(result['items']), 3)
        # All three fall through the no-section heuristic (single tokens),
        # none of them silently opened a "phrases" section.
        self.assertTrue(all(i['item_type'] == 'vocab' for i in result['items']))

    def test_empty_section_produces_no_items(self):
        result = parse_lesson_text('Vocab:\nPhrases:\n- hello there')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['item_type'], 'phrase')

    def test_no_section_short_line_is_vocab(self):
        result = parse_lesson_text('apple')
        self.assertEqual(result['items'][0]['item_type'], 'vocab')

    def test_no_section_long_line_is_note(self):
        result = parse_lesson_text('This is a longer sentence with many words in it')
        self.assertEqual(result['items'][0]['item_type'], 'note')

    def test_blank_lines_ignored(self):
        result = parse_lesson_text('Vocab:\n\n- apple\n\n\n- banana\n')
        self.assertEqual(len(result['items']), 2)

    def test_cyrillic_and_polish_text_preserved(self):
        result = parse_lesson_text('Vocab:\n- яблуко = apple\n- książka = book')
        self.assertEqual(result['items'][0]['text'], 'яблуко')
        self.assertEqual(result['items'][1]['text'], 'książka')

    def test_full_spec_example(self):
        raw = (
            'Topic: Travel & Airports\n'
            'Vocab:\n'
            '- boarding pass = посадковий талон\n'
            '- to check in\n'
            '- layover\n'
            'Phrases:\n'
            "- I'm running late\n"
            'Mistakes:\n'
            '- I go to the airport yesterday → I went to the airport yesterday\n'
            "- She don't like it -> She doesn't like it\n"
            'Grammar:\n'
            '- Past Simple vs Present Perfect\n'
            'Notes:\n'
            '- Practice more with layovers\n'
        )
        result = parse_lesson_text(raw)
        self.assertEqual(result['topic'], 'Travel & Airports')
        types = [i['item_type'] for i in result['items']]
        self.assertEqual(
            types,
            ['vocab', 'vocab', 'vocab', 'phrase', 'correction', 'correction', 'grammar', 'note'],
        )

    def test_empty_input(self):
        result = parse_lesson_text('')
        self.assertIsNone(result['topic'])
        self.assertEqual(result['items'], [])

    def test_none_input(self):
        result = parse_lesson_text(None)
        self.assertEqual(result['items'], [])
