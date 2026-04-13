from odoo.tests.common import TransactionCase

from odoo.addons.language_words.models.normalize import normalize


class TestNormalize(TransactionCase):
    """Unit tests for the normalize() dedup-key function (SPEC §3.2)."""

    def test_unicode_nfc(self):
        """NFC normalization is applied."""
        # U+00E9 (precomposed é) vs U+0065 + U+0301 (decomposed)
        self.assertEqual(normalize('\u0065\u0301'), '\u00e9')

    def test_lowercase(self):
        self.assertEqual(normalize('APPLE'), 'apple')
        self.assertEqual(normalize('Hello World'), 'hello world')

    def test_strip_whitespace(self):
        self.assertEqual(normalize('  apple  '), 'apple')

    def test_collapse_internal_whitespace(self):
        self.assertEqual(normalize('how  are   you'), 'how are you')

    def test_smart_apostrophe(self):
        """Right single quotation mark → ASCII apostrophe."""
        self.assertEqual(normalize("it\u2019s"), "it's")

    def test_em_dash(self):
        self.assertEqual(normalize('well\u2014known'), 'well-known')

    def test_en_dash(self):
        self.assertEqual(normalize('2020\u20132021'), '2020-2021')

    def test_trailing_period_stripped(self):
        self.assertEqual(normalize('hello.'), 'hello')

    def test_trailing_question_mark_stripped(self):
        self.assertEqual(normalize('How are you?'), 'how are you')

    def test_trailing_exclamation_stripped(self):
        self.assertEqual(normalize('Hello!'), 'hello')

    def test_multiple_trailing_punct_stripped(self):
        self.assertEqual(normalize('Really?!'), 'really')

    def test_internal_punctuation_preserved(self):
        """Apostrophes and hyphens inside words are preserved."""
        self.assertEqual(normalize("don't"), "don't")
        self.assertEqual(normalize('well-known'), 'well-known')

    def test_empty_string(self):
        self.assertEqual(normalize(''), '')

    def test_none_equivalent(self):
        """None-like empty input returns empty string."""
        self.assertEqual(normalize(''), '')

    def test_dedup_equivalence_trailing_punct(self):
        """'How are you?' and 'How are you' map to the same key."""
        self.assertEqual(normalize('How are you?'), normalize('How are you'))

    def test_dedup_equivalence_case_space(self):
        """'Apple ' and 'apple' map to the same key."""
        self.assertEqual(normalize('Apple '), normalize('apple'))
