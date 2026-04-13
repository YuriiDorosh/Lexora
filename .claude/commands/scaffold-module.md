Create the standard Odoo 18 addon scaffold for a new Lexora module named: $ARGUMENTS

**Before generating any files:**
- Check whether `src/addons/$ARGUMENTS/` already exists using the Glob or Bash tool.
- If the directory exists, stop immediately and report: "Module $ARGUMENTS already exists at src/addons/$ARGUMENTS/ — aborting to avoid overwrite. Delete the directory or choose a different name."
- Only proceed if the directory does not exist.
1. Read `CLAUDE.md` to confirm the module install order and verify `$ARGUMENTS` appears in it.
2. Identify the correct `depends` list: always include `language_security` as a base; add others based on where `$ARGUMENTS` sits in the install order chain.

Generate these files (create them, do not just describe them):

**`src/addons/$ARGUMENTS/__manifest__.py`**
```python
{
    "name": "<Human-readable name for $ARGUMENTS>",
    "version": "18.0.0.1.0",
    "category": "Language Learning",
    "license": "LGPL-3",
    "author": "Lexora",
    "depends": [<derived from install order>],
    "data": [],
    "installable": True,
    "auto_install": False,
}
```

**`src/addons/$ARGUMENTS/__init__.py`**
```python
from . import models
```

**`src/addons/$ARGUMENTS/models/__init__.py`**
```python
# Models for $ARGUMENTS — populated in later sub-steps
```

**`src/addons/$ARGUMENTS/security/ir.model.access.csv`**
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

**`src/addons/$ARGUMENTS/views/.gitkeep`** — empty file

After creating the files, add a sub-step to `docs/TASKS.md` under the current milestone:
`- [x] Scaffold $ARGUMENTS module (manifest, models/__init__, security CSV, views/)`
