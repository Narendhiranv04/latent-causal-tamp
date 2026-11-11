# 0110: Teaser assets — white background, tighter column

Previous turn sync: `799bba243` (top-down approach pose) was pushed to `origin/approach-d-v1`.

## Changes
- **Background colour:** `PAPER` is now pure white `#FFFFFF` (was `#F7F5F0`). It is used for the on-paper previews, the joint fills and the target's centre dot. Assets stay transparent.
- **`right_column_abc`:**
  - each panel keeps the shared x window (400–1300 px), but is trimmed to its own content rows: (a)/(b) at 2–854 px, (c) at 112–854 px
  - the gap between panels is now 14 px (was 40)
  - column height is 1842 px (was 2720)

No geometry changed; all schematic checks are unchanged. CONCEPTUAL ILLUSTRATION.
