# Dock: minimise panels to corner dots, and full view

A small shared module for every al-Marṣad lab product. It does three things:

- **Minimise to a dot.** Any floating panel can be minimised to a dot in a corner, and the dot can be dragged to any other corner.
- **Full view.** This hides every panel behind a single dot, so the world can be seen whole. Use the button, or press **F**; **Escape** returns.
- **Memory.** Each product's layout is remembered in its own browser storage.

It has no dependencies, needs no network request, and works by keyboard: Tab to a dot, Enter restores it, and the arrow keys move it to another corner.

## Use

A product's build inlines the two files, as `lab/hijrah-night-v2/build.py` does:

```html
<style>/*DOCK_CSS*/</style>
<script>/*DOCK_JS*/</script>
<script>
const dock = Dock.init({
  storeKey: "my-product",
  panels: [
    { id: "controls", el: document.querySelector("header"), label: "the controls", glyph: "≡", corner: "tl", buttonClass: "inline" },
    { id: "reading",  el: document.querySelector("#panel"), label: "the reading panel", glyph: "¶", corner: "br" },
  ],
});
// optional: a "Full view" button
document.querySelector("#fullBtn").onclick = () => dock.setFull(true);
</script>
```

Each panel gets a "–" button unless it has `noButton: true`, in which case the product calls `dock.minimise(id)` itself. These options control where the button goes:

- `buttonHost`: put the button inside a different element.
- `prepend`: put it first in its host.
- `buttonClass`: style it, as one of
  - `inline`, which sits in the host's flex flow;
  - `sticky`, which stays at the top of a scrolling list;
  - `small`.

To keep the dots clear of a header or a bottom sheet that is still open, set `--dock-top` and `--dock-bottom` in px. Hijrah Night does this in its `resize()`.

Colours can be themed with `--dock-bg`, `--dock-fg`, `--dock-ring`, `--dock-line` and `--dock-muted`.
