"""RabbitMQ publisher stub.

Real connection and publish logic is implemented in M3 when the
translation service integration is wired up.  This stub provides the
interface that all callers (language_translation, language_enrichment,
language_audio, language_anki_jobs) will use so they can be written
against a stable API now.
"""

import json
import logging
import uuid

_logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """Publish events to RabbitMQ on behalf of Odoo.

    Usage::

        publisher = RabbitMQPublisher(self.env)
        job_id = publisher.publish('translation.requested', {
            'entry_id': entry.id,
            'source_text': entry.source_text,
            'source_language': entry.source_language,
            'target_language': 'uk',
        })

    The returned ``job_id`` should be stored on the corresponding job
    record (e.g. ``language.translation``) so it can be matched when
    the result event arrives.
    """

    def __init__(self, env):
        self.env = env

    def publish(self, event_type, payload, job_id=None):
        """Publish an event.

        :param event_type: str  e.g. 'translation.requested'
        :param payload:    dict event-specific fields
        :param job_id:     str UUID; generated if not supplied
        :returns:          str the job_id embedded in the message
        """
        if job_id is None:
            job_id = str(uuid.uuid4())

        message = {
            'job_id': job_id,
            'event_type': event_type,
            'payload': payload,
        }

        # TODO M3: open a pika connection from env config parameters and
        # publish to the appropriate exchange/routing key.
        _logger.info(
            'RabbitMQ publish (stub): event_type=%s job_id=%s payload=%s',
            event_type,
            job_id,
            json.dumps(payload),
        )
        return job_id
