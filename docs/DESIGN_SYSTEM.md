# saas-vanilla Design System

## Foundation

`saas-vanilla` uses Tabler as the base admin UI library and then layers a local design system on top of it.

This means:

- Tabler provides layout primitives, form styling, cards, tables, and responsive behavior.
- Local CSS tokens define the durable visual identity.
- Jinja macros define repeatable UI patterns for all future SaaS projects.

## Durable rules

### 1. Use tokens, not ad-hoc colors

Prefer the local custom properties in `app/static/css/style.css`:

- `--ds-ink`
- `--ds-muted`
- `--ds-bg`
- `--ds-panel`
- `--ds-accent`
- `--ds-accent-2`
- `--ds-ring`

### 2. Favor shared macros

Use the shared macros in `app/templates/macros/ui.html` before creating page-specific markup:

- `page_header()`
- `stat_card()`
- `empty_state()`
- `icon()`

### 3. Keep the shell consistent

All future projects should preserve:

- left navigation pattern
- top page header pattern
- card-based content sections
- dense but readable admin tables
- visible empty states

### 4. Branding can move, layout should not

Project-specific work should usually customize:

- product name
- descriptive copy
- accent emphasis
- page-specific modules

Project-specific work should usually preserve:

- spacing rhythm
- component anatomy
- navigation behavior
- form styling
- table patterns

## Recommended extension pattern

When adding a new page:

1. Add the route and permission slug.
2. Start with `page_header()`.
3. Use existing card/table/form structures first.
4. Add a new macro only if the pattern will repeat across future products.

