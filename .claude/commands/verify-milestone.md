Present the verification checklist for the current active milestone.

Steps:
1. Read `docs/TASKS.md` — identify the current milestone (the block under "Current Milestone", not "Completed Milestones").
2. Read `docs/PLAN.md` — find that milestone's "Verification:" block and extract every command and expected output.
3. Read the "Verification steps passed" list in `docs/TASKS.md` to see what already passed.

Output in this format:

---
**Milestone:** M<N> — <name>
**Verification progress:** <X already passed> / <Y total steps>

| # | Status | Command | Expected output |
|---|---|---|---|
| 1 | ✓ done | `<command>` | `<expected>` |
| 2 | ◻ to do | `<command>` | `<expected>` |
...

**Instructions:**
Run each ◻ command manually. Report which passed. I will then update `docs/TASKS.md`.
---

Do not run the commands yourself. Output the table only and wait for my results.
