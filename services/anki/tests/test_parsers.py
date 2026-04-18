"""Unit tests for the Anki parser functions (no RabbitMQ required).

Run inside the container:
  docker exec anki_service python -m pytest tests/ -v
Or from the project root:
  docker exec anki_service python -m pytest /app/tests/ -v
"""

import base64
import io
import json
import os
import sqlite3
import sys
import tempfile
import zipfile

# Allow importing from parent directory when running directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import _parse_txt, _parse_apkg, _clean_field, _process_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anki2_db(notes: list[str]) -> bytes:
    """Create a minimal collection.anki2 SQLite database in memory.

    notes: list of flds strings (fields joined by \\x1f).
    Returns bytes of the SQLite file.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    cur = conn.cursor()
    # Minimal Anki schema — only the tables/columns the parser reads.
    cur.execute(
        "CREATE TABLE col (id INTEGER PRIMARY KEY, models TEXT)"
    )
    models_json = json.dumps({
        '1': {
            'flds': [{'name': 'Front'}, {'name': 'Back'}],
        }
    })
    cur.execute("INSERT INTO col (id, models) VALUES (1, ?)", (models_json,))
    cur.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    for i, flds in enumerate(notes, 1):
        cur.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (i, flds))
    conn.commit()
    conn.close()

    with open(tmp_path, 'rb') as f:
        data = f.read()
    os.unlink(tmp_path)
    return data


def _make_apkg(notes: list[str], media: dict | None = None, audio_files: dict | None = None) -> bytes:
    """Build a minimal .apkg zip from a list of note flds strings.

    media:       {"0": "audio.mp3", ...}  (zip numeric key → filename)
    audio_files: {"0": b"<mp3 bytes>"}    (zip key → raw bytes)
    """
    db_bytes = _make_anki2_db(notes)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('collection.anki2', db_bytes)
        zf.writestr('media', json.dumps(media or {}))
        for key, data in (audio_files or {}).items():
            zf.writestr(key, data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _clean_field
# ---------------------------------------------------------------------------

class TestCleanField:
    def test_strips_html(self):
        text, audio = _clean_field('<div>hello</div>')
        assert text == 'hello'
        assert audio == []

    def test_extracts_sound(self):
        text, audio = _clean_field('word [sound:word.mp3]')
        assert 'word.mp3' in audio
        assert '[sound:' not in text

    def test_ignores_image_refs(self):
        # [sound:...] with non-audio extension should not appear in audio list
        text, audio = _clean_field('word [sound:img.jpg]')
        assert audio == []

    def test_empty_input(self):
        text, audio = _clean_field('')
        assert text == ''
        assert audio == []


# ---------------------------------------------------------------------------
# _parse_txt
# ---------------------------------------------------------------------------

class TestParseTxt:
    def test_basic_two_column(self):
        data = b'apple\t\xd1\x8f\xd0\xb1\xd0\xbb\xd1\x83\xd0\xba\xd0\xbe\nbanana\t\xd0\xb1\xd0\xb0\xd0\xbd\xd0\xb0\xd0\xbd'
        entries, errors = _parse_txt(data)
        assert len(entries) == 2
        assert entries[0]['source_text'] == 'apple'
        assert entries[0]['translation'] == 'яблуко'
        assert errors == []

    def test_single_column_no_translation(self):
        entries, errors = _parse_txt(b'hello\nworld')
        assert len(entries) == 2
        assert 'translation' not in entries[0]

    def test_skips_comment_lines(self):
        entries, _ = _parse_txt(b'# comment\napple\ttest')
        assert len(entries) == 1

    def test_skips_empty_lines(self):
        entries, _ = _parse_txt(b'\n\napple\ttest\n\n')
        assert len(entries) == 1

    def test_strips_html_in_fields(self):
        entries, _ = _parse_txt(b'<b>bold</b>\t<em>italic</em>')
        assert entries[0]['source_text'] == 'bold'
        assert entries[0]['translation'] == 'italic'

    def test_empty_source_counted_as_error(self):
        entries, errors = _parse_txt(b'\tonly-translation')
        assert len(entries) == 0
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# _parse_apkg
# ---------------------------------------------------------------------------

class TestParseApkg:
    def test_basic_two_field_notes(self):
        apkg = _make_apkg(['apple\x1fyabloko', 'banana\x1fbanana_uk'])
        entries, audio, errors = _parse_apkg(apkg, {})
        assert len(entries) == 2
        assert entries[0]['source_text'] == 'apple'
        assert entries[0]['translation'] == 'yabloko'
        assert audio == {}
        assert errors == []

    def test_front_back_auto_detect(self):
        # DB has Front/Back named fields; auto-detection should pick them.
        apkg = _make_apkg(['FrontText\x1fBackText'])
        entries, _, errors = _parse_apkg(apkg, {})
        assert entries[0]['source_text'] == 'FrontText'
        assert entries[0]['translation'] == 'BackText'
        assert errors == []

    def test_explicit_field_mapping(self):
        # Swap: second field is source, first is translation.
        apkg = _make_apkg(['TranslationField\x1fSourceField'])
        entries, _, _ = _parse_apkg(apkg, {'source': 1, 'translation': 0})
        assert entries[0]['source_text'] == 'SourceField'
        assert entries[0]['translation'] == 'TranslationField'

    def test_html_stripped_from_fields(self):
        apkg = _make_apkg(['<div>word</div>\x1f<b>слово</b>'])
        entries, _, _ = _parse_apkg(apkg, {})
        assert entries[0]['source_text'] == 'word'
        assert entries[0]['translation'] == 'слово'

    def test_audio_extracted(self):
        fake_mp3 = b'ID3\x00fake-mp3-data'
        apkg = _make_apkg(
            ['hello [sound:hello.mp3]\x1fworld'],
            media={'0': 'hello.mp3'},
            audio_files={'0': fake_mp3},
        )
        entries, audio, errors = _parse_apkg(apkg, {})
        assert entries[0].get('audio_filename') == 'hello.mp3'
        assert 'hello.mp3' in audio
        assert base64.b64decode(audio['hello.mp3']) == fake_mp3

    def test_missing_audio_file_does_not_fail(self):
        # Sound tag references a file not present in the zip.
        apkg = _make_apkg(
            ['hello [sound:missing.mp3]\x1fworld'],
            media={'0': 'other.mp3'},
            audio_files={'0': b'data'},
        )
        entries, audio, errors = _parse_apkg(apkg, {})
        # Entry should still be created; audio_data may be empty or partial.
        assert len(entries) == 1
        assert errors == []

    def test_bad_zip_returns_parse_error(self):
        entries, audio, errors = _parse_apkg(b'not-a-zip', {})
        assert entries == []
        assert any('zip' in e['reason'].lower() or 'invalid' in e['reason'].lower() for e in errors)

    def test_empty_source_field_counted_as_error(self):
        apkg = _make_apkg(['\x1fonly-translation'])
        entries, _, errors = _parse_apkg(apkg, {})
        assert len(entries) == 0
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# _process_job (integration)
# ---------------------------------------------------------------------------

class TestProcessJob:
    def test_routes_txt(self):
        raw = b'apple\tyabloko\nbanana\tbanana_uk'
        b64 = base64.b64encode(raw).decode()
        entries, audio, errors = _process_job({'file_format': 'txt', 'file_data': b64, 'field_mapping': '{}'})
        assert len(entries) == 2
        assert audio == {}

    def test_routes_apkg(self):
        apkg = _make_apkg(['word\x1ftranslation'])
        b64 = base64.b64encode(apkg).decode()
        entries, audio, errors = _process_job({'file_format': 'apkg', 'file_data': b64, 'field_mapping': '{}'})
        assert len(entries) == 1

    def test_empty_file_raises(self):
        import pytest
        with pytest.raises(ValueError, match='empty'):
            _process_job({'file_format': 'txt', 'file_data': base64.b64encode(b'').decode()})

    def test_bad_b64_raises(self):
        import pytest
        with pytest.raises(Exception):
            _process_job({'file_format': 'txt', 'file_data': '!!!not-b64!!!'})
