"""RabbitMQ consumer utility for Odoo cron-based message draining.

Each module that consumes RabbitMQ result events (translation, enrichment,
audio, anki) uses this utility from its own cron-triggered method.

The pattern:
    1. Cron calls ``ModelFoo.action_consume_results()``.
    2. That method calls ``RabbitMQConsumer(self.env).drain(queue_name, handler)``.
    3. The drainer opens a blocking connection, polls via ``basic_get`` until
       the queue is empty, calls the handler for each message, and acks.
    4. Connection is closed after draining.

Using ``basic_get`` (polling) rather than ``basic_consume`` (push) is
intentional: it is safe inside a synchronous Odoo cron context and avoids
keeping a persistent blocking I/O loop alive in an Odoo worker process.
"""

import json
import logging

_logger = logging.getLogger(__name__)

# Maximum messages to drain per cron run per queue, to bound execution time.
DEFAULT_MAX_MESSAGES = 200


def _get_pika():
    try:
        import pika  # noqa: PLC0415
        return pika
    except ImportError:
        return None


class RabbitMQConsumer:
    """Drain a single RabbitMQ queue and dispatch messages to a handler.

    Usage in a model method::

        def action_consume_results(self):
            consumer = RabbitMQConsumer(self.env)
            consumer.drain('translation.completed', self._handle_completed)
            consumer.drain('translation.failed',   self._handle_failed)
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

    def drain(self, queue_name, handler, max_messages=DEFAULT_MAX_MESSAGES):
        """Drain up to ``max_messages`` from ``queue_name``.

        :param queue_name:  str  RabbitMQ queue to poll
        :param handler:     callable(job_id, payload) called for each message
        :param max_messages: int upper bound per cron run
        :returns: int number of messages processed
        """
        pika = _get_pika()
        if pika is None:
            _logger.warning('pika not installed — RabbitMQ consume skipped for %s', queue_name)
            return 0

        host, port, vhost, user, password = self._connection_params()
        processed = 0
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
            # passive=True — don't create the queue; it must already exist
            # (publisher declares it on first use).
            # passive=True: check without creating — queue may not exist yet on
            # first boot.  If it doesn't exist, catch the exception and exit
            # cleanly; the publisher will declare it when the first job is sent.
            try:
                channel.queue_declare(queue=queue_name, durable=True, passive=True)
            except Exception:
                _logger.debug('Queue %s does not exist yet — skipping', queue_name)
                connection.close()
                return 0

            while processed < max_messages:
                method, _props, body = channel.basic_get(
                    queue=queue_name, auto_ack=False
                )
                if method is None:
                    break  # queue empty
                try:
                    message = json.loads(body)
                    job_id = message.get('job_id', '')
                    payload = message.get('payload', {})
                    handler(job_id, payload)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    processed += 1
                except Exception as exc:  # noqa: BLE001
                    _logger.error(
                        'RabbitMQ message handling failed: queue=%s job_id=%s error=%s',
                        queue_name,
                        message.get('job_id', '?') if 'message' in dir() else '?',
                        exc,
                    )
                    # nack without requeue to avoid poison-pill loops;
                    # message goes to dead-letter queue if configured.
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            connection.close()
            if processed:
                _logger.info('RabbitMQ drained %d messages from %s', processed, queue_name)
        except Exception as exc:  # noqa: BLE001
            _logger.warning('RabbitMQ drain failed for %s: %s', queue_name, exc)

        return processed
