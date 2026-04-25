## Summary

<!-- 1–3 bullet points describing WHAT changed and WHY. Link the milestone if applicable. -->

- 
- 

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature / milestone
- [ ] Refactor (no behaviour change)
- [ ] Docs / comments only
- [ ] CI / tooling
- [ ] Breaking change

## Milestone / scope

<!-- e.g. "M21 — Sentence Builder" or "M18.5 — Header UI Redesign" -->


## Test plan

<!-- How was this verified? Check all that apply. -->

- [ ] `docker exec odoo odoo --config /etc/odoo/odoo.conf -d lexora --test-enable --no-http --stop-after-init -u <module>`  → 0 failures
- [ ] `make up-dev` → all services start clean
- [ ] Manual portal smoke test on the golden path
- [ ] Edge case tested: ___
- [ ] No test required (docs / config only)

## Odoo modules changed

<!-- List any `language_*` modules modified so reviewers know what to re-install. -->

- 

## Checklist

- [ ] `ruff check` passes (no new lint errors)
- [ ] `ruff format` applied (code is formatted)
- [ ] No secrets / credentials committed
- [ ] `docs/TASKS.md` updated if this completes a milestone sub-step
- [ ] `docs/DECISIONS.md` updated if an architectural decision was made

---

🤖 Generated with [Claude Code](https://claude.ai/claude-code)
