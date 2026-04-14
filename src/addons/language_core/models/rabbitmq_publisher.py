"""RabbitMQ publisher — connects via pika and publishes durable messages.

Each caller gets a fresh connection per publish call.  This is acceptable
for Odoo because publishes are infrequent (one per async job enqueue) and
keeping a persistent connection alive across Odoo workers is complex.

Connection parameters are read from ``ir.config_parameter`` so they can be
overridden in production without code changes (ADR-018).
"""

import json
import logging
import uuid

_logger = logging.getLogger(__name__)


def _get_pika():
    """Import pika lazily so modules that don't use RabbitMQ don't fail."""
    try:
        import pika  # noqa: PLC0415
        return pika
    except ImportError:
        return None


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

    If publishing fails (RabbitMQ down, pika not installed), the error is
    logged but NOT re-raised — the caller's DB transaction is not rolled back.
    The caller must handle the case where ``job_id`` was returned but the
    message was not delivered (e.g. by leaving the job record in ``pending``
    state for a retry cron).
    """

    def __init__(self, env):
        self.env = env

    def _connection_params(self):
        get = self.env['ir.config_parameter'].sudo().get_param
        host = get('rabbitmq.host', 'rabbitmq')
        port = int(get('rabbitmq.port', '5672'))
        vhost = get('rabbitmq.vhost', '/')
        user = get('rabbitmq.user', 'guest')
        password = get('rabbitmq.password', 'guest')
        return host, port, vhost, user, password

    def publish(self, event_type, payload, job_id=None):
        """Publish an event to the named queue.

        :param event_type: str  e.g. 'translation.requested' — also used as queue name
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

        pika = _get_pika()
        if pika is None:
            _logger.warning(
                'pika not installed — RabbitMQ publish skipped: event_type=%s job_id=%s',
                event_type, job_id,
            )
            return job_id

        host, port, vhost, user, password = self._connection_params()
        try:
            credentials = pika.PlainCredentials(user, password)
            conn_params = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=credentials,
                connection_attempts=2,
                retry_delay=1,
                socket_timeout=5,
            )
            connection = pika.BlockingConnection(conn_params)
            channel = connection.channel()
            # Declare queue as durable so it survives RabbitMQ restarts.
            channel.queue_declare(queue=event_type, durable=True)
            channel.basic_publish(
                exchange='',
                routing_key=event_type,
                body=json.dumps(message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent message
                    content_type='application/json',
                ),
            )
            connection.close()
            _logger.info(
                'RabbitMQ published: event_type=%s job_id=%s', event_type, job_id
            )
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                'RabbitMQ publish failed: event_type=%s job_id=%s error=%s',
                event_type, job_id, exc,
            )

        return job_id
