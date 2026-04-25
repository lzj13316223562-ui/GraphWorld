# GraphWorld Icon Library

This folder is reserved for future icon assets.

Current implementation uses inline SVG path data in `web/app.js`:
- `ICON_PATHS`: key -> SVG path `d` (24x24 viewbox)
- `ICON_ALIASES`: backend `semantic_type` -> icon key

To add a new icon:
1. Add a key to `ICON_PATHS` with a simple stroke-only path (24x24).
2. Add aliases in `ICON_ALIASES` for semantic types that should map to it.

The renderer is `appendNodeIcon(...)` in `web/app.js`.
