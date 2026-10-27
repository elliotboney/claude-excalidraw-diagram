# claude-excalidraw-diagram

A Claude Code plugin for diagrams you can open and edit at excalidraw.com. Claude writes a short Python script, the bundled generator turns it into an `.excalidraw` file, and a validator checks it before you see it.

What the files get right, so they survive dragging things around in the app:

- Text lives in its box, arrow labels live on their arrow.
- Arrow ends snap to the box side, so arrows follow boxes and stay level when boxes are aligned.
- Several arrows on one side spread out, and each arrow gets its own lane. No tangled shared trunks.
- Title + notes boxes: a larger name over smaller muted detail.
- Nunito for all text.

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
