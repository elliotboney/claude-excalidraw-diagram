# Excalidraw element schema (for hand-editing)

Read this only when the bundled generator can't express what you need (ellipses, diamonds,
free-draw, images, frames, custom arrowheads, precise styling). Otherwise extend `excalidraw.py`.

## Scene wrapper

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "...",
  "elements": [ ... ],
  "appState": { "viewBackgroundColor": "#020617", "gridSize": null, "theme": "dark" },
  "files": {}
}
```

## Fields every element shares

`type`, `id` (unique string), `x`, `y`, `width`, `height`, `angle` (radians, 0),
`strokeColor`, `backgroundColor` (`"transparent"` for no fill), `fillStyle`
(`"solid" | "hachure" | "cross-hatch"`), `strokeWidth`, `strokeStyle`
(`"solid" | "dashed" | "dotted"`), `roughness` (0 clean, 1 hand-drawn, 2 sketchy),
`opacity` (0–100), `groupIds` (array; same id → moves together), `frameId` (null),
`roundness` (`{"type":3}` for rounded rects/lines, `null` for sharp/text), `seed` (random int),
`version`, `versionNonce` (random int), `isDeleted` (false), `boundElements` (array), `updated`
(epoch ms), `link` (null), `locked` (false).

## Type-specific fields

**rectangle / ellipse / diamond** — just the shared fields. Switch `type` to change shape.

**text**
- `text`, `originalText` (same string; `\n` for line breaks)
- `fontSize` (px), `fontFamily` (`1` Hand-drawn/Virgil, `2` Normal/Helvetica, `3` Code/monospace, `5` Excalifont, `6` Nunito: the house font for all text)
- `textAlign` (`"left"|"center"|"right"`), `verticalAlign` (`"top"|"middle"`)
- `lineHeight` (e.g. 1.25)
- `containerId`: set to a shape's id to make the text live *inside* that shape (bound label).
  When you do, the shape's `boundElements` must include `{"type":"text","id":<textId>}`.
  Simpler alternative used by the generator: leave `containerId` null and put the shape + text in
  the same `groupIds` so they move together without binding fragility.

**arrow / line**
- `points`: array of `[dx, dy]` offsets **relative to the element's `x,y`**. First is `[0,0]`.
  Two points = straight; add midpoints for elbows/curves.
- `lastCommittedPoint` (null), `startArrowhead` (null or `"arrow"|"triangle"|"dot"|"bar"`),
  `endArrowhead` (usually `"arrow"`).
- `startBinding` / `endBinding`: `{ "elementId": <boxId>, "focus": 0, "gap": 6 }` or `null`.
  - `focus`: −1..1 offset of the attach point along the edge; `0` = centered, recomputed live.
  - `gap`: px standoff between arrow tip and box edge. The actual endpoint coordinate must sit
    ~`gap` px **outside** the box, or the binding is dropped on import.
  - **Two-way:** each bound box must also have `{"id":<arrowId>,"type":"arrow"}` in its
    `boundElements`. Missing the reciprocal entry = arrow detaches when the box is dragged.

## Binding checklist (the common bug)

For every arrow that should stay attached:
1. `arrow.startBinding.elementId` / `endBinding.elementId` → a real box id ✔
2. that box's `boundElements` contains the arrow's id ✔
3. the arrow's first/last absolute point (`x+points[i]`) sits just outside that box's edge ✔

`scripts/validate.py` checks all three. Run it after any hand-edit.

## Gotchas

- Don't reuse `id`s. Don't leave `boundElements` referencing deleted elements.
- `roundness: {"type":3}` on a text element looks wrong — text uses `null`.
- Mixed `fontFamily` across labels looks inconsistent; pick one.
- Excalidraw renders its own fonts; you can't embed JetBrains Mono — `fontFamily:3` is the closest.
- Colors are plain hex; the dark canvas (`viewBackgroundColor`) makes deep fills read well.
