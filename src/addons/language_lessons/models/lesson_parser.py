"""Rule-based lesson text parser — no ORM, no LLM (ADR-038 § 38a).

``parse_lesson_text(raw_text)`` is a pure function so it can be unit
tested without a database. It recognises explicit section markers and
splits bulleted lines deterministically. Lines outside any recognised
section fall back to a token-count heuristic. This module must never
import anything from ``odoo``.
"""

import re

# Section keyword -> canonical section name.
_SECTION_ALIASES = {
    'topic': 'topic',
    'vocab': 'vocab',
    'vocabulary': 'vocab',
    'phrase': 'phrases',
    'phrases': 'phrases',
    'mistake': 'mistakes',
    'mistakes': 'mistakes',
    'correction': 'mistakes',
    'corrections': 'mistakes',
    'grammar': 'grammar',
    'note': 'notes',
    'notes': 'notes',
}

# One of the keywords above, optionally followed by ':' and trailing text.
_HEADER_RE = re.compile(
    r'^\s*(' + '|'.join(sorted(_SECTION_ALIASES, key=len, reverse=True)) + r')\s*:?\s*(.*)$',
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r'^\s*[-*•]\s*')
_TRANSLATION_SEP_RE = re.compile(r'\s-\s')
_ARROW_RE = re.compile(r'\s*(?:→|->)\s*')

# item_type for each section that carries vocab/phrase-shaped items.
_SECTION_ITEM_TYPE = {
    'vocab': 'vocab',
    'phrases': 'phrase',
    'mistakes': 'correction',
    'grammar': 'grammar',
    'notes': 'note',
}


def _strip_bullet(line):
    return _BULLET_RE.sub('', line, count=1).strip()


def _split_translation(text):
    """Split "term = translation" or "term - translation" into a pair.

    Prefers '=' (unambiguous). Falls back to a space-padded '-' so
    hyphenated compounds like "check-in" are never mis-split.
    Returns (term, translation_or_None).
    """
    if '=' in text:
        left, _, right = text.partition('=')
        left, right = left.strip(), right.strip()
        return left, (right or None)
    match = _TRANSLATION_SEP_RE.search(text)
    if match:
        left, right = text[:match.start()].strip(), text[match.end():].strip()
        if left and right:
            return left, right
    return text.strip(), None


def _split_correction(text):
    """Split "wrong -> corrected" (also '→') into (wrong, corrected_or_None)."""
    parts = _ARROW_RE.split(text, maxsplit=1)
    if len(parts) == 2:
        wrong, corrected = parts[0].strip(), parts[1].strip()
        return wrong, (corrected or None)
    return text.strip(), None


def parse_lesson_text(raw_text):
    """Parse raw lesson text into a topic + a flat list of item dicts.

    Returns:
        {
            "topic": str | None,
            "items": [
                {
                    "item_type": "vocab" | "phrase" | "correction" | "grammar" | "note",
                    "text": str,
                    "translation_hint": str | None,
                    "corrected_text": str | None,
                    "context": str | None,
                },
                ...
            ],
            "markers_found": bool,  # True iff at least one section header
                                    # (Topic:/Vocab:/...) was recognised.
                                    # False signals freeform/unstructured
                                    # canvas text — the caller (language.
                                    # lesson.action_parse) falls back to
                                    # the LLM extraction endpoint in that
                                    # case (ADR-038 § 38g).
        }
    """
    topic = None
    items = []
    current_section = None
    markers_found = False

    for raw_line in (raw_text or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = _HEADER_RE.match(line)
        if header_match:
            markers_found = True
            keyword = header_match.group(1).lower()
            remainder = header_match.group(2).strip()
            section = _SECTION_ALIASES[keyword]
            if section == 'topic':
                if remainder:
                    topic = remainder
                # "Topic:" with no inline value just marks intent;
                # the next non-empty line is *not* auto-consumed —
                # tutors write the title inline in practice.
                current_section = None
                continue
            current_section = section
            if remainder:
                # A marker with trailing content on the same line is
                # treated as the first bulleted item of that section.
                items.append(_build_item(section, remainder))
            continue

        content = _strip_bullet(line)
        if not content:
            continue

        if current_section is None:
            # No section header seen yet (or we're between headers) —
            # apply the token-count heuristic from the spec.
            token_count = len(content.split())
            section = 'vocab' if token_count <= 3 else 'notes'
        else:
            section = current_section

        items.append(_build_item(section, content))

    return {'topic': topic, 'items': items, 'markers_found': markers_found}


def _build_item(section, content):
    item_type = _SECTION_ITEM_TYPE[section]

    if item_type in ('vocab', 'phrase'):
        text, translation_hint = _split_translation(content)
        return {
            'item_type': item_type,
            'text': text,
            'translation_hint': translation_hint,
            'corrected_text': None,
            'context': None,
        }

    if item_type == 'correction':
        wrong, corrected = _split_correction(content)
        return {
            'item_type': 'correction',
            'text': wrong,
            'translation_hint': None,
            'corrected_text': corrected,
            'context': None,
        }

    # grammar / note — whole line stored verbatim.
    return {
        'item_type': item_type,
        'text': content,
        'translation_hint': None,
        'corrected_text': None,
        'context': None,
    }
