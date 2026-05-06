"""language.speaking.session — AI Speaking Coach session record (M30).

Each row represents one recorded oral-practice attempt: the topic, the
Whisper transcript, and the LLM-generated feedback (corrections, synonyms,
improved version). Audio blob is stored as `ir.attachment` and linked
via `audio_attachment_id` so it stays in the Odoo filestore alongside
M6's recorded audio.

State machine: pending → transcribing → analyzing → completed / failed.
"""

import json
import logging

from odoo import api, fields, models

# M29 / ADR-029: import the canonical Selection so this model tracks the
# en/uk/el/pl set automatically when a fifth language ships.
from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION

_logger = logging.getLogger(__name__)


class LanguageSpeakingSession(models.Model):
    _name = "language.speaking.session"
    _description = "AI Speaking Coach Session"
    _order = "create_date desc, id desc"
    _rec_name = "topic"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env.user,
    )
    target_language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        required=True,
        index=True,
        string="Target Language",
    )
    topic = fields.Char(
        string="Topic",
        help="The conversation starter shown to the user (LLM-generated or manually entered).",
    )
    transcript = fields.Text(
        string="Transcript",
        help="Faster-Whisper output of the user's spoken response.",
    )
    duration_seconds = fields.Float(
        string="Duration (s)",
        help="Length of the recorded audio.",
    )

    # ── Feedback fields populated by /analyze-speech ──────────────────────
    feedback_corrections = fields.Text(
        string="Corrections (JSON)",
        help='JSON list of {"wrong": "...", "correct": "...", "note": "..."}.',
    )
    feedback_synonyms = fields.Text(
        string="Synonyms (JSON)",
        help='JSON list of {"original": "...", "suggestion": "...", "reason": "..."}.',
    )
    feedback_improved = fields.Text(
        string="Improved Version",
        help="The AI's polished rewrite of the user's transcript.",
    )

    # ── Audio storage ─────────────────────────────────────────────────────
    audio_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Audio Recording",
        ondelete="set null",
        help="Original recording stored as ir.attachment (Odoo filestore).",
    )

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("transcribing", "Transcribing"),
            ("analyzing", "Analyzing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    error_message = fields.Text(string="Error Message")

    # ── Helpers for the portal/JS layer (kept JSON-decoded) ───────────────

    def _corrections_list(self):
        try:
            return json.loads(self.feedback_corrections or "[]")
        except Exception:
            return []

    def _synonyms_list(self):
        try:
            return json.loads(self.feedback_synonyms or "[]")
        except Exception:
            return []

    @api.model
    def create_for_user(self, user_id, target_language, topic=None):
        """Convenience constructor used by the controller.

        Returns a fresh session in `status='pending'` ready to receive a
        transcript and then analysis.
        """
        return self.sudo().create(
            {
                "user_id": user_id,
                "target_language": target_language,
                "topic": topic or "",
                "status": "pending",
            }
        )

    def write_transcript(self, transcript, duration=None):
        """Set the transcript and flip status → analyzing."""
        vals = {"transcript": transcript or "", "status": "analyzing"}
        if duration is not None:
            vals["duration_seconds"] = duration
        self.sudo().write(vals)

    def write_feedback(self, corrections, synonyms, improved):
        """Persist LLM analysis output and flip status → completed."""
        self.sudo().write(
            {
                "feedback_corrections": json.dumps(corrections or [], ensure_ascii=False),
                "feedback_synonyms": json.dumps(synonyms or [], ensure_ascii=False),
                "feedback_improved": improved or "",
                "status": "completed",
            }
        )

    def mark_failed(self, error):
        self.sudo().write({"status": "failed", "error_message": str(error)[:1000]})
