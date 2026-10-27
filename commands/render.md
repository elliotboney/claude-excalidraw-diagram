---
description: Open an .excalidraw file in excalidraw.com and screenshot it for review
argument-hint: <path to .excalidraw>
---

Render $ARGUMENTS in the real app and look at it.

With the Playwright browser tools:
1. Go to https://excalidraw.com/ and wait for the canvas.
2. Pages cannot fetch local files, so route a same-origin URL to the file: `page.route('**/x.json*', r => r.fulfill({ path: '<absolute path>', contentType: 'application/json' }))`.
3. In the page, fetch `/x.json`, wrap the text in a `File`, put it in a `DataTransfer`, and dispatch a `drop` event on the canvas.
4. Press Shift+1 to zoom to fit, wait a second, and take a screenshot. Accept any "replace content" dialog.

Then review the screenshot against the skill's rules: text inside its box, labels on their arrows, arrows snapped and level where boxes are aligned, no shared trunks, no clipped text. Report what looks wrong and where.

If the browser is busy or unavailable, say so and fall back to `scripts/validate.py`. Do not claim a visual check you did not do.
