---
description: Draw an editable Excalidraw diagram from a description
argument-hint: <what to draw, and where to save it>
---

Load the `excalidraw-diagram` skill and follow it to draw: $ARGUMENTS

1. Plan the columns (one per stage, left to right), the boxes in each, and the arrows. Use title + notes boxes (`sub=`) where a box names a thing and then describes it.
2. Write a short Python generator script next to the output file. It imports `Diagram` from the skill's `scripts/` folder (the skill's base directory is shown when it loads). Keep the script: it is how the diagram gets edited later.
3. Run it, then run `scripts/validate.py` on the output. Fix every problem and every warning you can (crossings, squeezed lanes, text that does not fit) by changing the script, then rerun.
4. Report the file path, the script path, and anything the validator still warns about, with the reason it was left.

Ask one question first only if the description could produce wildly different diagrams.
