# The MCP server has no notes tools

Status: accepted (RAS-81), 2026-10-17

## Context

The Titan template's MCP server ships its example feature: `list_notes`,
`add_note` and a Notes card (`ui://notes/list`), with server instructions
and a consent scope that talk about notes. Riffle is a split-flap display;
Claude connects to it to post to boards, and the notes tools only confused
that (Claude was told "Riffle keeps short notes").

## Decision

The MCP server offers the board tools (`post_message`, `get_board`,
`list_boards`) and the public pages (`privacy_policy`, `terms_of_service`,
`help`), nothing else. The instructions and the consent scope describe
boards. The MCP Apps machinery (`apps/mcp/resources.py`, `ui/bridge.js`)
stays with no views, so a board card can be added without rebuilding it,
and its tests use a sample view.

## Consequences

- `copier update` will conflict where the template changes its notes
  tools, notes view or tests in `apps/mcp/`: keep this app's side.
- The `apps/notes` Django app and its `/app/` pages are not part of this
  decision; removing them is separate work.
