---
description: Check an .excalidraw file for detached arrows, floating text, crossings, and style drift
argument-hint: <path to .excalidraw>
---

Run the `excalidraw-diagram` skill's `scripts/validate.py` on: $ARGUMENTS
If no path was given, use the most recently modified `.excalidraw` file under the current directory.

Report each problem and warning in plain words: which boxes or arrows, what is wrong, and the fix.
If a generator script produced the file (look for a `.py` that saves to this path), apply the fixes there and rerun it. Otherwise list the fixes and stop: do not hand-edit a file the user drew in the app without asking.
