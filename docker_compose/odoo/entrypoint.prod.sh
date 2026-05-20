#!/bin/sh
# ============================================================
# Lexora — Odoo production entrypoint (M38)
# ============================================================
# Runs as PID 1 inside the Odoo container.  Reads the templated
# config, sed-substitutes secrets from environment variables
# (sourced from `.env.prod`), chmod 600s the result, and execs
# odoo with the rendered config.
#
# Failure modes are noisy: if either env var is missing, the
# substitution leaves the @@PLACEHOLDER@@ literal in the conf
# file, which Odoo would happily accept as a wrong password.
# We refuse to start in that case so the operator sees the
# misconfiguration immediately.
#
# See ADR-037 §37d.
# ============================================================

set -eu

TPL=/etc/odoo/odoo.prod.conf.template
# Render to /tmp: the official odoo:18 image owns /etc/odoo as root:root
# (mode 755) and runs the container as the unprivileged `odoo` user, which
# can overwrite existing files in /etc/odoo but cannot create new files
# there.  `sed -i` needs to create a tempfile in the target directory
# before atomically renaming it, so writing the rendered conf inside
# /etc/odoo crashes with "Permission denied" on every restart.
# /tmp is universally writable and the rendered conf is re-generated on
# every container start anyway — no need for it to live on a persistent
# path.  See ADR-037 §37d.
OUT=/tmp/odoo.prod.conf

if [ ! -f "$TPL" ]; then
    echo "[entrypoint.prod] FATAL: template not found at $TPL" >&2
    exit 1
fi

# Refuse to start if either secret is unset or empty.
: "${ADMIN_PASSWD:?[entrypoint.prod] FATAL: ADMIN_PASSWD env var is required (set in .env.prod)}"
: "${DB_PASSWORD:?[entrypoint.prod] FATAL: DB_PASSWORD env var is required (set in .env.prod)}"

cp "$TPL" "$OUT"

# Use a delimiter other than `/` so passwords containing `/` are safe.
# Use `|` — uncommon in generated passwords.
if printf '%s' "$ADMIN_PASSWD" | grep -q '|'; then
    echo "[entrypoint.prod] FATAL: ADMIN_PASSWD contains '|'; pick a password without that character" >&2
    exit 1
fi
if printf '%s' "$DB_PASSWORD" | grep -q '|'; then
    echo "[entrypoint.prod] FATAL: DB_PASSWORD contains '|'; pick a password without that character" >&2
    exit 1
fi

sed -i "s|@@ADMIN_PASSWD@@|${ADMIN_PASSWD}|g" "$OUT"
sed -i "s|@@DB_PASSWORD@@|${DB_PASSWORD}|g"   "$OUT"

# Sanity: the placeholders MUST be gone after substitution.
if grep -q '@@ADMIN_PASSWD@@\|@@DB_PASSWORD@@' "$OUT"; then
    echo "[entrypoint.prod] FATAL: placeholder substitution failed; check ADMIN_PASSWD/DB_PASSWORD" >&2
    exit 1
fi

chmod 600 "$OUT"

echo "[entrypoint.prod] config rendered at $OUT (chmod 600); starting Odoo with workers=4 proxy_mode=True"
exec odoo --config "$OUT" "$@"
