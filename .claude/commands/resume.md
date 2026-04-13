Read and synthesise the following, in this order:

1. `docs/TASKS.md` — find the "Current Milestone" block. Note the milestone name, status, the first unchecked sub-step, and any listed blockers.
2. Run `git log --oneline -8` — note the last 3 commits (message + hash).
3. `CLAUDE.md` — recall the key invariants section and the current status line.

Then output a resume briefing in this exact format — nothing else, no preamble:

---
**Milestone:** M<N> — <name> (<status>)
**Next sub-step:** <first unchecked [ ] item from TASKS.md, or "milestone complete — awaiting next">
**Last commits:** <3 most recent, one per line>
**Blockers:** <from TASKS.md, or "none">
**Invariants to keep in mind:** <copy the 3 invariants from the "Key invariants" table in CLAUDE.md that are most directly related to the current milestone's domain (e.g. for event work: job_id / idempotency; for entry work: dedup key; for PvP: Redis/Odoo split)>
---

Keep the total output under 20 lines. Do not begin implementing anything.
