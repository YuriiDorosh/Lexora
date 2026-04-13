Review the RabbitMQ event handler for: $ARGUMENTS

If $ARGUMENTS is a file path, read that file. If it is an event name (e.g. `translation.requested`), search `src/` for the publisher and consumer code for that event.

Check each criterion from ADR-018 (`docs/DECISIONS.md`). Mark each: ✓ pass / ✗ fail / ? not visible in the shown code.

**Checklist:**

1. **job_id in payload** — does the published event include a `job_id` UUID field?
2. **Dedup guard (publisher side)** — does Odoo set the job record to `pending` and check it is not already `processing/completed` before publishing?
3. **Dedup guard (consumer side)** — does the worker check if the `job_id` is already in a terminal state before doing any work?
4. **Status state machine** — does the code follow exactly `pending → processing → completed | failed`? Is `processing` set before the work starts?
5. **Ack placement** — is `channel.basic_ack()` (or equivalent) called AFTER the durable write to Odoo, not before?
6. **Completed-job no-op** — if a completed job is redelivered, does the handler log it and return early without reprocessing?
7. **Nack on exception** — if the worker raises an unhandled exception, is the message nacked (requeued) rather than acked?

For each ✗ criterion, show:
- The exact lines that are wrong
- The corrected version

If $ARGUMENTS is not yet implemented (stub stage), note which criteria cannot be verified yet and which must be designed correctly from the first implementation.
