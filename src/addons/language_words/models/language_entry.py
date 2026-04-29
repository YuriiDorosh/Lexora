import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .language_lang import LANGUAGE_SELECTION
from .normalize import normalize

_logger = logging.getLogger(__name__)

ENTRY_TYPE_SELECTION = [
    ('word', 'Word'),
    ('phrase', 'Phrase'),
    ('sentence', 'Sentence'),
    ('collocation', 'Collocation'),
]

ENTRY_STATUS_SELECTION = [
    ('active', 'Active'),
    ('archived', 'Archived'),
]

CREATED_FROM_SELECTION = [
    ('manual', 'Manual'),
    ('anki_import', 'Anki Import'),
    ('copied_from_post', 'Copied from Post'),
    ('copied_from_entry', 'Copied from Entry'),
    ('copied_from_chat', 'Copied from Chat'),
]


class LanguageEntry(models.Model):
    """Core learning entry — a word, phrase, sentence, or collocation.

    A single model with a ``type`` field (ADR-001).
    Dedup key = normalize(source_text) + source_language + owner_id (ADR-003).
    Private by default; sharing is opt-in (ADR-004).
    """

    _name = 'language.entry'
    _description = 'Learning Entry'
    _rec_name = 'source_text'
    _order = 'create_date desc'

    # ------------------------------------------------------------------ #
    # Core fields (SPEC §3.1)
    # ------------------------------------------------------------------ #

    type = fields.Selection(
        selection=ENTRY_TYPE_SELECTION,
        string='Type',
        required=True,
        default='word',
        index=True,
    )
    source_text = fields.Char(
        string='Source Text',
        required=True,
    )
    normalized_text = fields.Char(
        string='Normalized Text',
        readonly=True,
        copy=False,
        index=True,
        help='Computed at save; used for dedup lookup (SPEC §3.2).',
    )
    source_language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Source Language',
        required=True,
        index=True,
    )
    owner_id = fields.Many2one(
        comodel_name='res.users',
        string='Owner',
        required=True,
        default=lambda self: self.env.uid,
        index=True,
        ondelete='cascade',
    )
    is_shared = fields.Boolean(
        string='Shared',
        default=False,
        help='When True, other Language Users can see and copy this entry.',
    )
    status = fields.Selection(
        selection=ENTRY_STATUS_SELECTION,
        string='Status',
        default='active',
        required=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Provenance fields
    # ------------------------------------------------------------------ #

    created_from = fields.Selection(
        selection=CREATED_FROM_SELECTION,
        string='Created From',
        default='manual',
    )
    copied_from_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Copied From User',
        ondelete='set null',
    )
    copied_from_entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Copied From Entry',
        ondelete='set null',
    )
    # copied_from_post_id — added in language_portal (M7) via _inherit
    # because language.post is defined in language_portal which depends on language_words

    # ------------------------------------------------------------------ #
    # Related records (progressively populated by later modules)
    # ------------------------------------------------------------------ #

    media_links = fields.One2many(
        comodel_name='language.media.link',
        inverse_name='entry_id',
        string='Media Links',
    )
    note = fields.Text(
        string='Context Sentence',
        help='Sentence where this word/phrase was found; used for Sentence Builder.',
    )

    # translations  — added in M3 (language.translation)
    # enrichments   — added in M4 (language.enrichment)
    # audio_ids     — added in M6 (language.audio)

    pvp_eligible = fields.Boolean(
        string='PvP Eligible',
        compute='_compute_pvp_eligible',
        store=True,
        help='True if the entry has at least one completed translation (SPEC §3.1).',
    )

    # ------------------------------------------------------------------ #
    # Computed fields
    # ------------------------------------------------------------------ #

    @api.depends()
    def _compute_pvp_eligible(self):
        # M3 will add depends on translation_ids.status
        for entry in self:
            entry.pvp_eligible = False

    # ------------------------------------------------------------------ #
    # ORM overrides
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            raw = vals.get('source_text', '')
            vals['normalized_text'] = normalize(raw)
            self._check_duplicate(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'source_text' in vals:
            vals['normalized_text'] = normalize(vals['source_text'])
            # Re-check dedup when source_text changes, against other entries
            for record in self:
                self._check_duplicate(
                    {
                        'normalized_text': vals['normalized_text'],
                        'source_language': vals.get('source_language', record.source_language),
                        'owner_id': vals.get('owner_id', record.owner_id.id),
                    },
                    exclude_id=record.id,
                )
        return super().write(vals)

    # ------------------------------------------------------------------ #
    # Dedup helpers
    # ------------------------------------------------------------------ #

    def _check_duplicate(self, vals, exclude_id=None):
        """Raise ValidationError if a duplicate entry exists.

        Dedup key = normalize(source_text) + source_language + owner_id (ADR-003).
        """
        normalized = vals.get('normalized_text') or normalize(vals.get('source_text', ''))
        source_language = vals.get('source_language')
        owner_id = vals.get('owner_id')

        if not normalized or not source_language or not owner_id:
            return

        domain = [
            ('normalized_text', '=', normalized),
            ('source_language', '=', source_language),
            ('owner_id', '=', owner_id),
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))

        existing = self.sudo().search(domain, limit=1)
        if existing:
            raise ValidationError(
                f'This entry already exists in your vocabulary: '
                f'"{existing.source_text}" ({dict(LANGUAGE_SELECTION)[source_language]}). '
                'Duplicate entries are not allowed.'
            )

    # ------------------------------------------------------------------ #
    # Copy (for "copy to my list")
    # ------------------------------------------------------------------ #

    def copy_to_user(self, target_user_id):
        """Create a new entry owned by *target_user_id* copying this entry's content.

        Sets provenance fields (ADR-002 / ADR-014).
        Raises ValidationError if the target user already has the same entry.
        """
        self.ensure_one()
        return self.sudo().create({
            'type': self.type,
            'source_text': self.source_text,
            'source_language': self.source_language,
            'owner_id': target_user_id,
            'created_from': 'copied_from_entry',
            'copied_from_user_id': self.owner_id.id,
            'copied_from_entry_id': self.id,
        })
