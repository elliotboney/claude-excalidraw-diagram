<p align="center"><img src="logo.png" alt="claude-excalidraw-diagram logo" width="240"></p>

# claude-excalidraw-diagram

A Claude Code plugin for diagrams you can open and edit at excalidraw.com. Claude writes a short Python script, the bundled generator turns it into an `.excalidraw` file, and a validator checks it before you see it.

## Why this exists

A diagram that looks right in a screenshot can still fall apart the moment you drag a box. Generated Excalidraw files tend to fail in the same few ways: text that wraps one letter per line, labels that float next to arrows instead of riding on them, arrows that look attached but detach on drag, and fan-outs that tangle into a hairball. Every rule below came from a real diagram that broke one of these ways. The fix was made by hand in the app, then the saved JSON was diffed against the generated one, and the difference became a rule in the generator and a check in the validator. `/excalidraw-diagram:learn` runs that same loop on your own hand fixes.

## The rules

**Editable first.** These three are what keep a diagram intact when someone edits it.

1. **Text lives in the shape.** A box's label is bound to the box (`containerId`), so it moves and edits with it. No text box parked on top of a rectangle.
2. **Labels live on the arrow.** An arrow's label is bound to the arrow and rides along its path when the arrow re-routes. You can drag it along the arrow in the app.
3. **Arrows snap to the box.** Both ends carry a `fixedPoint` binding on the facing side, about 6 px outside it, which is exactly what the app writes when you drop an arrow on a shape. The binding is two-way. Align two boxes by their middles and the arrow between them comes out level.

**Arrows that flow.**

- **Ports follow the direction, not the angle.** If the target sits to the right, the arrow leaves the right side and enters the left side, however far up or down the target is. That is the rule layered layout engines like ELK use.
- **Spread ports.** When several arrows use one side of a box, their ends spread along it, ordered by where the other end sits, so they never cross at the box. An arrow to a middle-aligned box keeps the center and stays straight.
- **One lane per arrow.** Each elbow arrow gets its own vertical segment in the gap between columns, pinned with `fixedSegments` so the app's router keeps it. No merged trunk where you cannot tell which line goes where. Lane order is searched to minimize crossings and legs lying on top of each other.
- **Room for lanes.** 120 to 170 px between columns. The generator warns when lanes are squeezed.
- **Near-level means level.** An arrow within 12 px of level is snapped straight.

**Layout.**

- **Crossings first.** Order boxes within a column so connected boxes sit near each other.
- **Columns, not coordinates.** One column per stage, one width, a fixed gap. Left to right for a process, top to bottom for a hierarchy.
- **Labels by the source**, on the first leg, one or two words.

**Text.**

- **Nunito everywhere**, boxes, labels, titles.
- **Title + notes boxes.** When a box names a thing and then describes it, the name is a 20 px title and the detail sits under it in 14 px muted text. Prose callouts stay a single block of text.
- **Real text widths.** A width of 0 makes excalidraw.com wrap one character per line, so every text carries a measured width and the generator warns when it will not fit its box.

**Meaning, not decoration.** Color by role (source, process, emphasis, output, note), at most a handful of colors, never color alone: dashed strokes mark guesses and notes.

## The research behind it

The layout rules are ranked by what has been measured to help people read diagrams, not by taste. Full write-up with links: [`references/layout-rules.md`](skills/excalidraw-diagram/references/layout-rules.md).

- **Edge crossings hurt reading the most.** Purchase (1997) found crossings by far the most important aesthetic. Bends and symmetry mattered less. Angles and grid snapping had no significant effect.
- **Continuity is next.** Ware et al. (2002): after path length, a path the eye can follow straight and the number of crossings are the biggest costs, and they trade off. Do not bend a straight path just to dodge one crossing.
- **Layered layout engines agree on the mechanics.** Graphviz dot, Eclipse ELK, and dagre all put each stage in a layer, align connected nodes, assign ports by flow direction, and reserve space between layers for labels. The defaults here are borrowed from them and sized for hand-editable diagrams.
- **Flowchart and architecture conventions** (ISO 5807, BPMN, C4): one dominant direction, the happy path on one straight line, one level of abstraction per diagram, a label on every line saying what flows.
- **Excalidraw's own source** settles the file details: how bindings and `fixedPoint`s are stored, how the elbow router picks an exit side, how labels are positioned along a path, and how big the cut-out behind a label is.

## What the validator checks

`scripts/validate.py` runs after every build. Problems are must-fix, warnings are worth a look.

- Every arrow end is bound, two-way, with a `fixedPoint`, and sits on the box edge.
- No text floats over a box unless it is grouped with it, and no text has zero width.
- No arrow passes through a box it is not connected to.
- Arrows a few px off level, with the boxes to align.
- Crossings and overlapping arrow legs, naming the arrows involved.
- Any font other than Nunito.

## Commands

| Command | Does |
|---|---|
| `/excalidraw-diagram:diagram <description>` | Plans, generates, validates a new diagram, and keeps the script |
| `/excalidraw-diagram:validate <file>` | Checks bindings, floating text, crossings, shared lanes, fonts |
| `/excalidraw-diagram:render <file>` | Opens the file in excalidraw.com (Playwright) and reviews a screenshot |
| `/excalidraw-diagram:learn <generated> <hand-fixed>` | Diffs your hand fix against the generated file and folds the rules into the skill |

The skill also triggers on its own when you ask Claude to diagram or map something.

## Install

```
claude plugin marketplace add elliotboney/claude-excalidraw-diagram
claude plugin install excalidraw-diagram@excalidraw-diagram
```

Or inside Claude Code: `/plugin marketplace add elliotboney/claude-excalidraw-diagram`, then `/plugin install excalidraw-diagram@excalidraw-diagram`.

Needs Python 3. `render` needs the Playwright MCP server.
