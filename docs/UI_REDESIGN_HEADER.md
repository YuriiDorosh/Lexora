# Lexora — Header UI Redesign Spec (M18.5)

> Version: 1.0
> Created: 2026-04-23
> Status: Planned (not yet implemented)

---

## 1. Goal

Replace the current flat, single-level navbar with a three-group dropdown navbar.
Each group clusters related features under a labelled mega-menu or simple dropdown.
The result must remain mobile-friendly (collapses to a hamburger on small screens)
and consistent with the existing glassmorphism dark theme.

---

## 2. Current Navbar Structure

Existing `website.menu` records (approximate sequence order):

| Sequence | Label | URL | Auth |
|---|---|---|---|
| 10 | Home | / | public |
| 22 | Translator | /translator | public |
| 23 | Roleplay | /my/roleplay | user |
| 25 | Grammar Pro | /my/grammar-practice | user |
| 55 | Daily Practice | /my/practice | user |
| 65 | My Profile | /my/dashboard | user |
| 70 | Leaderboard | /my/leaderboard | user |
| 75 | Arena | /my/arena | user |
| 80 | Shop | /my/shop | user |
| 85 | Inventory | /my/inventory | user |
| — | Library (parent) | # | public |
| — | └─ Useful Words | /useful-words | public |
| — | └─ Grammar Guide | /grammar | public |

---

## 3. Target Navbar Structure

Three dropdown groups replace the flat list. "Home" and "Translator" stay as top-level
standalone items (no dropdown).

```
[Home]  [Translator]  [Practice ▾]  [Library ▾]  [Tools ▾]
                            │               │            │
               ┌────────────┘  ┌────────────┘  ┌────────┘
               │               │               │
          Daily Practice    Useful Words    My Profile
          Grammar Pro       Grammar Guide   Leaderboard
          Roleplay          Idioms *        Arena
          Sentence Builder* Phrasebook *    Shop / Inventory
```

`*` = added in M19/M20/M21 respectively.

### Group definitions

| Group | Parent label | Children |
|---|---|---|
| Practice | `Practice` | Daily Practice, Grammar Pro, Roleplay, Sentence Builder |
| Library | `Library` (existing parent) | Useful Words, Grammar Guide, Idioms, Phrasebook |
| Tools | `Tools` | My Profile, Leaderboard, Arena, Shop, Inventory |

---

## 4. Odoo XML Changes Required

### File: `src/addons/language_portal/data/website_menus.xml`

**Step 1 — Create three parent menu records (or reuse existing Library parent):**

```xml
<!-- Practice group -->
<record id="menu_practice_group" model="website.menu">
    <field name="name">Practice</field>
    <field name="url">#</field>
    <field name="sequence">30</field>
    <field name="parent_id" ref="website.main_menu"/>
</record>

<!-- Library group (already exists — keep as-is, just re-sequence) -->
<!-- existing id: menu_library_group  →  sequence=50 -->

<!-- Tools group -->
<record id="menu_tools_group" model="website.menu">
    <field name="name">Tools</field>
    <field name="url">#</field>
    <field name="sequence">70</field>
    <field name="parent_id" ref="website.main_menu"/>
</record>
```

**Step 2 — Re-parent existing child menus:**

Each existing menu record gets its `parent_id` updated to the appropriate group.

| Menu record id | New parent | New sequence |
|---|---|---|
| `menu_daily_practice` | `menu_practice_group` | 10 |
| `menu_grammar_practice` | `menu_practice_group` | 20 |
| `menu_roleplay` | `menu_practice_group` | 30 |
| `menu_sentence_builder` (M21) | `menu_practice_group` | 40 |
| `menu_useful_words` | `menu_library_group` | 10 |
| `menu_grammar_guide` | `menu_library_group` | 20 |
| `menu_idioms` (M19) | `menu_library_group` | 30 |
| `menu_phrasebook` (M20) | `menu_library_group` | 40 |
| `menu_my_profile` | `menu_tools_group` | 10 |
| `menu_leaderboard` | `menu_tools_group` | 20 |
| `menu_arena` | `menu_tools_group` | 30 |
| `menu_shop` | `menu_tools_group` | 40 |
| `menu_inventory` | `menu_tools_group` | 50 |

**Important:** Set `noupdate="0"` on the `<data>` wrapper so `--update language_portal`
re-applies parent_id changes on existing websites.

### Files to check for existing menu record ids

The actual XML record ids live across multiple modules:

- `src/addons/language_portal/data/website_menus.xml` — Grammar Pro, Roleplay, Translator, Library group + children
- `src/addons/language_learning/data/website_menus.xml` — Daily Practice, My Profile, Leaderboard
- `src/addons/language_pvp/data/website_menus.xml` — Arena
- `src/addons/language_learning/data/website_menus.xml` (or `language_portal`) — Shop, Inventory

Cross-module re-parenting is done by referencing the record via `ref="<module>.<record_id>"`.

---

## 5. CSS Plan

### New tokens in `premium_ui.css`

```css
/* ── Navbar dropdown groups ── */
.lx-nav-dropdown {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  padding: 8px 0;
  min-width: 200px;
}

.lx-nav-dropdown .dropdown-item {
  color: rgba(255,255,255,0.85);
  padding: 8px 20px;
  font-size: 0.9rem;
  border-radius: 6px;
  margin: 1px 4px;
  transition: background 0.15s;
}

.lx-nav-dropdown .dropdown-item:hover {
  background: rgba(99, 102, 241, 0.2);
  color: #ffffff;
}

/* Group label in navbar toggle */
.lx-nav-group-toggle {
  color: rgba(255,255,255,0.9) !important;
  font-weight: 600;
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

.lx-nav-group-toggle::after {
  border-top-color: rgba(255,255,255,0.6);
}

.lx-nav-group-toggle:hover {
  color: #ffffff !important;
}
```

### Applying styles to Odoo-rendered nav

Odoo renders `website.menu` children as Bootstrap `dropdown-menu` items.
The `.lx-nav-dropdown` class needs to be added to the `<ul class="dropdown-menu">` element.
This is done via a QWeb template override in `language_portal/views/branding.xml`:

```xml
<template id="portal_nav_dropdown_style" inherit_id="website.layout" name="Lexora Nav Dropdowns">
    <xpath expr="//ul[contains(@class,'dropdown-menu')]" position="attributes">
        <attribute name="class" add="lx-nav-dropdown" separator=" "/>
    </xpath>
</template>
```

**Caution:** This XPath matches ALL dropdown menus in the layout (including language
switcher). Scope with a more specific selector if side effects appear.

---

## 6. Mobile Behaviour

Odoo's Bootstrap-based navbar collapses all menus (including nested dropdowns) into a
single hamburger menu at breakpoints `< lg` (992px). No custom JS is required — Bootstrap's
`navbar-toggler` handles this natively.

**Requirements:**
- All three group labels must remain visible in mobile expanded view.
- Children must be indented under their group label (Bootstrap adds `.dropdown-menu` inside
  `.navbar-collapse` which renders as a vertical list on mobile — this is correct by default).
- The glassmorphism background on `.lx-nav-dropdown` should be transparent / `background: none`
  on mobile to avoid a dark box within the expanded hamburger menu.

```css
@media (max-width: 991.98px) {
  .lx-nav-dropdown {
    background: transparent;
    backdrop-filter: none;
    border: none;
    box-shadow: none;
    padding: 0;
  }

  .lx-nav-dropdown .dropdown-item {
    padding-left: 32px; /* indent children under group label */
    color: rgba(255,255,255,0.75);
  }
}
```

---

## 7. Implementation Checklist

- [ ] Audit actual XML record ids across all four modules (run `grep -r "menu_" src/addons/*/data/`)
- [ ] Create `menu_practice_group` and `menu_tools_group` parent records
- [ ] Re-parent all child records (set `noupdate="0"` on `<data>` wrapper)
- [ ] Append `.lx-nav-dropdown` CSS block to `premium_ui.css`
- [ ] Add `portal_nav_dropdown_style` QWeb override in `branding.xml`
- [ ] Add mobile media query for transparent dropdown on small screens
- [ ] `--update language_portal` + `docker restart odoo`
- [ ] Test on desktop: three groups expand correctly, children link to correct pages
- [ ] Test on mobile (DevTools 390px): hamburger expands, all children visible and tappable
- [ ] Verify Translator and Home remain standalone (not grouped)
- [ ] Verify user-only items (Arena, Shop, Inventory) are hidden for unauthenticated visitors

---

## 8. Known Constraints

- **Cross-module `parent_id` references**: If `menu_arena` is defined in `language_pvp`,
  its `parent_id` must reference `language_portal.menu_tools_group` via the module-qualified
  ref. This creates a soft dependency — `language_pvp` data file must be loaded after
  `language_portal`. The existing install order already satisfies this.
- **`noupdate="1"` menus won't re-parent on update**: All menu records that need re-parenting
  must have `noupdate="0"`. Check each source file's `<data noupdate="...">` wrapper.
- **Website ID scoping**: Menu records created with `website_id` set to a specific site will
  not appear on other sites. Omit `website_id` for universal menus, or use `website_id="1"`
  for single-site deployments.
