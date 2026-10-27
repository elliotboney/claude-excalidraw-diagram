# Layout rules for flow diagrams

What graph-drawing research, the layered layout engines (Graphviz dot, Eclipse ELK, dagre), and the
process-diagram standards agree on, reduced to rules a generator can follow. Sourced Oct 26, 2026.
The generator in `scripts/excalidraw.py` implements the ones marked **[auto]**; `validate.py` flags
violations of the ones marked **[check]**; the rest are layout decisions you make when writing the spec.

## Priority, from the evidence

1. **Edge crossings** hurt reading more than anything else measured. Purchase 1997 found crossings
   "by far the most important aesthetic"; bends and symmetry were second tier; minimum angle and
   grid snapping had no significant effect. **[check]** counts crossings between unrelated arrows.
   (https://research.monash.edu/en/publications/which-aesthetic-has-the-greatest-effect-on-human-understanding/)
2. **Continuity**: a path the eye can follow straight. Ware 2002: after path length, continuity and
   crossings are the two biggest cognitive costs, and they trade off, so do not bend a straight path
   to remove one crossing. **[auto]** arrows between middle-aligned boxes are straight; **[check]**
   flags an arrow that is off level by a few px.
   (https://research.monash.edu/en/publications/cognitive-measurements-of-graph-aesthetics/)
3. **Bends**: fewer is better, and only where the edge changes direction (ELK `unnecessaryBendpoints`).
   **[auto]** elbow arrows get one Z or N bend; the app's router re-solves on drag.
4. Unevaluated but conventional, use as tie-breakers: even node distribution, uniform edge length,
   consistent flow direction, aspect ratio (Bennett et al. 2007, Table 1).
   (https://diglib.eg.org/items/8f9c6297-fddf-4ed0-84e3-df3ef6858de5)

## Flow direction and ports

- One dominant direction. Left to right for a process or pipeline, top to bottom for a hierarchy.
  Start top left, finish bottom right. Happy path on one straight line; exceptions branch below it.
  (ISO 5807 via https://en.wikipedia.org/wiki/Flowchart; https://processcamp.io/exercises/best-practices;
  https://lucid.co/diagram/flowchart/how-to-make-a-flowchart)
- **Ports follow the direction, not the angle.** ELK: for flow RIGHT, edges leave the EAST side and
  enter the WEST side; DOWN uses SOUTH out, NORTH in. So a hub fanning out to a column of targets
  leaves its right side for every one of them, however far up or down the target sits. **[auto]**
  `Diagram._sides`: if the target is wholly to the right, right→left; wholly below, bottom→top; and
  so on; only when boxes overlap on both axes fall back to the dominant axis.
  (https://raw.githubusercontent.com/eclipse-elk/elk/master/plugins/org.eclipse.elk.alg.layered/src/org/eclipse/elk/alg/layered/graph/LGraphUtil.java)
- Snap each end to the **midpoint of that side**, about 6 px out. That is what Excalidraw writes
  (`fixedPoint [1.0239, 0.5001]` on a 240 px box, `mode: "orbit"`), and it is why "align middle" on
  two boxes levels the arrow between them. **[auto]** `Diagram._side_point`.
- Back edges (feedback, loops) are routed around the outside, arrowhead kept in the real direction
  (dot reverses them internally; ELK `feedbackEdges`). Draw them dashed and route them below or above
  the main band, never through it.
  (https://eclipse.dev/elk/reference/options/org-eclipse-elk-layered-feedbackEdges.html)

## Layers, alignment, spacing

- Every stage is a **layer** (a column for LR flow). Same x and same width for every box in a column;
  a fixed gap between boxes. **[auto]** `Diagram.column(x, w, y, gap)`.
- Boxes joined by a horizontal arrow across adjacent columns are **aligned by middle** so the arrow is
  level (Brandes-Köpf "improve straightness" in ELK). **[auto]** `Diagram.align_middle(a, b, ...)`.
- Gaps: engines default to 50 px between nodes in a layer and 50 px between layers (dagre), 20 px
  (ELK), 0.25 in / 0.5 in (dot). For a hand-sized diagram with 16 px labels on the arrows use **120 to
  170 px between columns** (one lane per arrow needs the room) (room for a label like "PO") and **30 to 40 px between boxes** in a column.
  Vendor guidance: 60 to 80 px vertical, 100 to 120 px horizontal, 16 to 20 px grid.
  (https://github.com/dagrejs/dagre/wiki; https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html;
  https://www.useworkspace.dk/en/blog/flowchart-best-practices)
- Order boxes within a column to minimize crossings (layer sweep / barycenter: put each box near the
  average position of the boxes it connects to in the neighbouring column). **[check]** reports the
  crossing count so you can reorder.
- An arrow never passes through a box it is not connected to. **[check]**.

## Fan-out and fan-in

- **House rule (Oct 27, 2026): separate ports and separate lanes, not a merged bus.** ELK's
  default without `mergeEdges` does the same: each edge gets its own port on the side, ordered to
  avoid crossings, and its own vertical segment in the gap (orthogonal edge routing assigns
  "slots" between layers). **[auto]** `Diagram._route` on save. **[check]** flags two arrows
  sharing a segment. The merged-trunk alternative (ELK `mergeEdges`, dot `concentrate=true`) is
  what this generator did before Oct 27; the hand fix rejected it.
  (https://eclipse.dev/elk/reference/options/org-eclipse-elk-layered-mergeEdges.html)
- **Labels default to the first leg, by the source** (from the hand fix). With separate lanes they
  no longer stack on a trunk. For a big fan-out with tight ports, put them near each target
  (`label_at≈0.85–0.9`). Excalidraw's own default is the middle of the
  middle segment; `labelPosition` (0..1 of path length) overrides it, and the app writes that same
  field when you drag a label. **[auto]** `Diagram.arrow(label_at=...)`.
  (https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/linearElementEditor.ts)
- dot and ELK reserve space for a label by inserting a dummy node of the label's size between the
  ranks; the practical version here is the 80 to 120 px column gap above.

## Text

- 2 to 5 words per process box, one line per label where possible, never wrap an arrow label.
  Verb-noun for steps, nouns for stores. Expand acronyms once.
  (https://www.useworkspace.dk/en/blog/flowchart-best-practices; https://c4model.com/diagrams/checklist)
- Text lives IN the shape (bound), arrow labels live ON the arrow (bound). **[check]** flags floating
  text over a box and labels with zero width.
- Size the box for the text at 16 px, about 0.55 × fontSize per character. **[auto]** `box()` warns
  when the text will not fit.

## Meaning, not decoration

- Color carries meaning: at most 3 to 6 colors, one meaning each, and never color alone (pair with a
  dashed stroke or a shape). Legend for anything non-obvious. Title with type and scope.
  (https://lucid.co/diagram/flowchart/how-to-make-a-flowchart; https://c4model.com/diagrams/notation;
  https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams)
- Every line unidirectional and labeled with its intent in that direction; no bidirectional arrows.
  (https://c4model.com/diagrams/checklist)
- One level of abstraction per diagram; split past about 15 nodes into sub-diagrams. The 7±2 figure
  is about recall, not visible items; chunk instead.
  (https://dev.to/simonbrown/how-to-review-a-software-architecture-diagram-6p0;
  https://www.nngroup.com/articles/chunking/)
- Gestalt: proximity groups, similarity types, a container only around a real boundary, the main path
  as figure and exceptions as ground, and no stray lines since a line always reads as a relationship.
  (https://www.uxtigers.com/post/gestalt-principles)

## Excalidraw specifics that matter for generated files

- Binding type is `{ elementId, fixedPoint: [fx, fy], mode: "orbit" | "inside" }`. `focus` and `gap`
  are gone; the app recomputes a `fixedPoint` from the endpoint for any binding without `mode`.
  `orbit` keeps the end on the outline at `BASE_BINDING_GAP + strokeWidth/2` px; `inside` puts it at
  the fixed point. Elbow arrows are always `orbit`. Values within 0.0001 of 0.5 are nudged to 0.5001.
  (https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/binding.ts;
  https://github.com/excalidraw/excalidraw/pull/9670)
- The elbow router picks the exit side from the fixed point's position on the shape (which corner-to-
  center wedge it falls in), then runs A* on a grid built from box edges, penalizing bends and
  forbidding backward moves. Putting the fixed point at a side midpoint is what fixes the exit side.
  (https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/heading.ts;
  https://plus.excalidraw.com/blog/building-elbow-arrows-part-two)
- Object snapping is 8 screen px to corners and centers; align middle has no shortcut, align
  top/bottom/left/right is Ctrl/Cmd+Shift+Arrow, distribute is Alt+H / Alt+V.
  (https://github.com/excalidraw/excalidraw/blob/master/packages/excalidraw/snapping.ts)
