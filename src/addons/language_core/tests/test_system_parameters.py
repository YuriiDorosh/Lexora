from odoo.tests.common import TransactionCase


class TestSystemParameters(TransactionCase):
    """Verify that default system parameter values are installed correctly."""

    def _get(self, key):
        return self.env['ir.config_parameter'].sudo().get_param(key)

    def test_pvp_min_entries_default(self):
        """language.pvp.min_entries must default to 10 (SPEC §4.12)."""
        self.assertEqual(self._get('language.pvp.min_entries'), '10')

    def test_audio_max_upload_bytes_default(self):
        """language.audio.max_upload_bytes must default to 10 MB (SPEC §4.5)."""
        expected = str(10 * 1024 * 1024)  # 10485760
        self.assertEqual(self._get('language.audio.max_upload_bytes'), expected)
