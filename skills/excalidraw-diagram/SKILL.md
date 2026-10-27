---
name: excalidraw-diagram
description: >-
  Generate editable Excalidraw diagrams (.excalidraw files) — flowcharts, system/architecture
  diagrams, data-flow and pipeline maps, org charts, mind maps, wireframes, network topology.
  Produces a valid Excalidraw scene with a clean palette, Nunito text, title + notes boxes, and arrows that
  are genuinely BOUND to their boxes (so they stay attached when the user drags things in the app).
  Use this skill whenever the user wants a diagram they can OPEN AND EDIT — i.e. mentions Excalidraw,
  or asks to "diagram / map out / sketch / draw / visualize" a system, flow, pipeline, or architecture
  and wants to tweak it afterward, or asks to convert an existing diagram/description into an editable
  drawing. Prefer this over static SVG/HTML/Mermaid whenever editability or hand-drawn style matters.
---

# Excalidraw diagrams

The point of an Excalidraw diagram is that the user **opens it and edits it** — drags boxes
around, redraws arrows, recolors, adds notes. So the bar isn't just "looks right in a
screenshot"; it's "stays sane when someone moves things." That single fact drives almost every
rule below, especially the one about arrow bindings.

You produce a `.excalidraw` file (JSON). The user opens it at **excalidraw.com → File → Open**
(or drag-drops it onto the canvas), or in the Excalidraw VS Code extension.

## Workflow

Don't hand-write the JSON. Write a short Python script that imports the bundled generator,
declares the layout, and saves the file. The generator handles the verbose element schema and —
critically — the arrow binding logic that's easy to get subtly wrong by hand.

1. **Plan the layout.** Decide the boxes, how they group, and the flow direction. Think in
   **bands**: left→right for a process/pipeline, top→bottom for a hierarchy. Assign each box a
   semantic `kind` (see palette) by its ROLE, not its color.
2. **Write a generator script** next to the bundled library. Copy `scripts/excalidraw.py` into your
   working directory (or add its folder to the path) and write a script like the example below.
3. **Run it** to emit the `.excalidraw` file.
4. **Validate** with `scripts/validate.py` — this catches unbound/floating arrows before the user
   ever sees them. Fix anything it flags.
5. **Hand the file to the user** with the one-line "open at excalidraw.com → File → Open" instruction.

### Minimal example

```python
from excalidraw import Diagram   # bundled in this skill's scripts/

d = Diagram(theme="dark")        # dark canvas, Nunito text

# left→right flow; lay out by x. Same band shares a y.
d.label(40, 60, "Request path", kind="process", size=16)
d.box("browser", 40,  100, 180, 64, kind="neutral", text="Browser\nclient")
d.box("api",     320, 100, 180, 64, kind="process", text="API server", sub="FastAPI :8000")
d.box("db",      600, 100, 180, 64, kind="data",    text="Postgres")
d.box("cache",   600, 200, 180, 64, kind="data",    text="Redis\ncache")

d.arrow("browser", "api", label="HTTPS")   # connect by NAME -> bound, stays attached
d.arrow("api", "db")
d.arrow("api", "cache", dashed=True)

d.save("request-path.excalidraw")
```

Then run `python validate.py request-path.excalidraw` and fix any problems it reports.

## Three rules that make a diagram editable (learned the hard way, Oct 2026)

These came from a hand-fixed diagram: the generator's first output rendered badly, the owner rebuilt
it in the app, and the saved JSON showed what the app itself writes. Match the app.

**1. Text lives IN the shape.** A box's label is a text element with `containerId` = the box id,
and the box lists it in `boundElements`. Never draw a rectangle and park a separate text element
on top of it: that text stays behind when the box is dragged and can't be edited by double-clicking
the box. `Diagram.box(text=...)` does the binding; `validate.py` flags any text floating over a box.

**2. Arrow labels live ON the arrow.** Same mechanism: the label is a text element whose
`containerId` is the arrow id, and the arrow lists it. Excalidraw then keeps it centered on the
path as the arrow re-routes. `Diagram.arrow(label=...)` does this; never place a label as a free
text element near the midpoint.

**3. Connectors SNAP to the shape.** An arrow end is attached only if all of these hold:

- `startBinding`/`endBinding` names the box id, **with a `fixedPoint`** (`[fx, fy]`, fractions
  of the box's width and height). That `fixedPoint` is what the app writes when you drop an
  arrow end onto a shape. Without it the end is "near" the box, not on it, and re-routes
  unpredictably.
- the fixed point is on the **facing side**, about 6 px outside it: the app writes
  `[1.0239, 0.5001]` for the middle of the right side of a 240 px box. A lone arrow on a side uses
  the midpoint; several arrows on one side spread out (see "Arrow style" below). Do NOT aim the end
  at the other box's center and clip to the edge; that lands off-middle whenever the boxes differ
  in size, and the arrow then stays tilted after the user aligns the boxes by their middles.
- the box's `boundElements` names the arrow id (binding is **two-way**),
- the endpoint sits exactly at that fixed point.

`Diagram.arrow()` records the arrow; `save()` places every port and lane at once (it needs all
arrows to share a side out fairly), writes the matching fixed points, and records both sides.
So **always connect arrows by box name**, not raw coordinates; use a coordinate tuple only for a
deliberately dangling arrow.

**Title + notes is the one exception.** When a box names a thing and then describes it (a system
and what it holds, a person and what they own), pass `sub=`:
`c.box("stripe", 64, kind="process", text="Stripe", sub="payments, payouts")`. The name becomes a 20 px
title and the notes 14 px muted text under it. Excalidraw allows one bound text per shape, so both
are separate texts GROUPED with the box: they drag with it, double-click edits either, arrows still
snap to the box. Resizing the box does not re-center them. Use it whenever the first line is a
name and the rest is detail; that used to be one long bound text with `\n`. Keep prose (red notes,
callouts) as a single bound text. `validate.py` accepts text grouped with its box.

Text must also carry a real `width` (the generator estimates it and sets `autoResize: true`).
A width of 0 makes excalidraw.com wrap one character per line.

`validate.py` checks all of this. Run it every time; treat a problem as a must-fix, not a warning.

**Prefer elbow (right-angle) arrows over straight diagonals.** `Diagram.arrow()` defaults to
`elbow=True`, which produces orthogonal arrows that Excalidraw's elbow router keeps tidy and
re-routes automatically as boxes move. In a banded layout this reads much cleaner than diagonal
lines criss-crossing the canvas, and it stays clean after the user drags things. Only pass
`elbow=False` for the occasional case where a direct diagonal genuinely looks better (e.g. a single
short connector where an elbow would add a pointless jog).

## Arrow style (house style, Oct 27, 2026)

These rules come from a hand-fixed generated diagram. `save()` applies them automatically.

- **Spread ports.** When n arrows use one side of a box, their ends sit at (i+1)/(n+1) along it,
  ordered by where the other end is (top neighbour gets the top port), so they do not cross at
  the box. An arrow to a box aligned by middle keeps the midpoint and stays level; the rest spread
  above and below it. Applies to fan-in and fan-out alike.
- **One lane per arrow.** Every elbow arrow gets its own vertical segment in the gap, pinned with
  `fixedSegments` so Excalidraw's router keeps it. No shared trunk or bus. The lane order is
  searched to minimize crossings and legs lying on each other.
- **Wide gaps.** Lanes need room: about 14 px per arrow crossing the gap plus 28. `save()` warns
  when lanes are squeezed; widen the gap (the hand fix was +70 px, to about 170).
- **Labels by the source**, on the first leg, by default. Pass `label_at` only to override.
- A horizontal arrow within 12 px of level is snapped level by sliding its target port.

## Palette & fonts

Pick `kind` by the box's role so diagrams read consistently. Dark theme is the default and looks
sharp; pass `theme="light"` for print/embedding in light docs.

| kind | role | dark color |
|---|---|---|
| `source` / `data` | inputs, databases, raw/stored data | violet |
| `process` | services, transforms, business logic | emerald |
| `emphasis` | the central hub / most important node | bright emerald |
| `accent` | queues, buses, connectors, intermediate artifacts | orange |
| `ui` | frontends, dashboards, things the user sees / final outputs | cyan |
| `note` | annotations, rules, callouts (renders dashed, no fill) | rose |
| `neutral` | external, generic, or legacy components | slate |

Fonts: **Nunito (`FONT_NUNITO`, fontFamily 6) for all text**, boxes, arrow labels, titles and
headers (house style, Oct 27, 2026). It is the default; do not pass another `font=`. `validate.py` warns
on anything else. Boxes are crisp (`roughness 0`), rounded (`roundness type 3`), stroke 1.5.

## Layout that doesn't look like a hairball

The full, sourced rule set is in `references/layout-rules.md` (graph-drawing research, ELK/dot/dagre
conventions, ISO 5807/BPMN/C4 guidance, Excalidraw internals). The short version:

- **Crossings first.** Edge crossings are the one aesthetic with a large measured effect on reading.
  Order boxes within a column so connected boxes sit near each other; `validate.py` reports the count.
- **Columns, not coordinates.** One column per stage with one width and a fixed gap:
  `c = d.column(400, 320, y=150, gap=40)` then `c.box("fab", 90, kind="process", text=...)`.
  120–170 px between columns (room for one lane per arrow), 30–40 px between boxes.
- **Level the lanes.** Boxes joined by a horizontal arrow across columns get `d.align_middle(a, b)`.
  The generator snaps arrow ends to side midpoints, so middle-aligned boxes give a straight arrow;
  `validate.py` warns when an arrow is a few px off level.
- **Ports follow the flow.** A target wholly to the right is entered from the left, left out of the
  source's right side, however far up or down it sits (ELK's rule). Done automatically.
- **Labels** default to the first leg by the source. For a big fan-out from one box, where ports
  are close together, `label_at=0.88` puts them by the targets instead. One or two words each.
- **Box sizing.** ~200–320 px wide, ~56–130 px tall, 16 px text, at most 4 short lines; `box()`
  warns when the text will not fit. Prose goes in a `note` box next to the thing it annotates.
- **Headers.** `d.label(...)` for the title and one header per column, colored with the column's `kind`.
- **Hub nodes.** The central node gets `kind="emphasis"` and a bit more size so the eye lands there.

## When NOT to reach for this

If the user wants a polished, non-editable graphic for a slide or README and won't touch it again,
a static SVG/HTML diagram may be a better fit. If they want a quick text-defined chart and don't care
about manual editing, Mermaid is lighter. This skill wins whenever **editability** or the
**hand-drawn aesthetic** is the point.

## Hand-editing the JSON

For tweaks the generator doesn't cover (custom shapes, ellipses, images, frames, exact styling),
see `references/schema.md` for the Excalidraw element schema and the exact fields each element type
needs. Prefer extending the generator over one-off hand edits, but the reference is there when you
need it.
