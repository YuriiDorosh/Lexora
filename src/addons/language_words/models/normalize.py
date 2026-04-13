"""Text normalization for dedup key computation.

See SPEC §3.2 for the full normalization pipeline.
This module is a pure-Python utility — no Odoo ORM imports.
"""

import re
import unicodedata

# Punctuation pairs: (unicode_char, ascii_replacement)
_PUNCTUATION_MAP = str.maketrans({
    '\u2018': "'",   # left single quotation mark
    '\u2019': "'",   # right single quotation mark  (also apostrophe)
    '\u02bc': "'",   # modifier letter apostrophe
    '\u201c': '"',   # left double quotation mark
    '\u201d': '"',   # right double quotation mark
    '\u2013': '-',   # en dash
    '\u2014': '-',   # em dash
    '\u2026': '...',  # horizontal ellipsis (handled separately; translate gives single char)
})

_TRAILING_PUNCT_RE = re.compile(r'[.!?]+$')
_WHITESPACE_RE = re.compile(r'\s+')


def normalize(text: str) -> str:
    """Return the normalized form of *text* used as the dedup key.

    Pipeline (SPEC §3.2):
    1. Unicode NFC normalization
    2. Lowercase
    3. Strip leading/trailing whitespace
    4. Collapse repeated internal whitespace to single space
    5. Normalize smart quotes / apostrophes / dashes to ASCII equivalents
    6. Strip trailing sentence-ending punctuation (. ! ?) — for dedup only
    7. Do NOT strip internal meaningful punctuation
    """
    if not text:
        return ''

    # 1. NFC
    text = unicodedata.normalize('NFC', text)

    # 2. Lowercase
    text = text.lower()

    # 3. Strip leading/trailing whitespace
    text = text.strip()

    # 4. Collapse internal whitespace
    text = _WHITESPACE_RE.sub(' ', text)

    # 5. Smart punctuation → ASCII  (handle ellipsis char separately)
    text = text.replace('\u2026', '...')
    text = text.translate(_PUNCTUATION_MAP)

    # 6. Strip trailing sentence-ending punctuation
    text = _TRAILING_PUNCT_RE.sub('', text)

    return text
