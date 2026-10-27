---
description: Learn house style from a hand-fixed copy of a generated diagram
argument-hint: <generated.excalidraw> <hand-fixed.excalidraw>
---

The user fixed a generated diagram by hand in the app. Learn what they changed and fold it into the `excalidraw-diagram` skill. Files: $ARGUMENTS

1. Load both files. Match elements by `id`. Ignore `version`, `versionNonce`, `updated`, `seed`, `index`.
2. Report the changes grouped by kind, with counts: boxes moved or resized (and by how much, e.g. a column shifted 70 px), arrow bindings and `fixedPoint`s, `fixedSegments`, label text and positions, fonts, colors, stroke styles, added or deleted elements. Name elements by their text.
3. State the rule each group implies in one line. Where a change could mean two different rules, ask, as a numbered list with your recommended answer first. Wait for the answers.
4. Then update the skill: the generator (`scripts/excalidraw.py`), the checks (`scripts/validate.py`), `SKILL.md`, and `references/layout-rules.md` as needed. Regenerate any diagram whose script lives in the current project and validate it.
5. Report what changed in the skill, in plain words.
