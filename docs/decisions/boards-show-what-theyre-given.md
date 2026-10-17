# Boards show what they're given

Status: accepted (2026-10-17)

## Context

The first boards were fixed kinds (Custom, News, Weather, Travel), and the
TV filled the empty ones with sample content while we planned to fetch
the news, the weather and trains on the server. Each feed would have
meant a source, an API key, a schedule and a failure mode for us, and it
would still be news chosen by us rather than by the person.

## Decision

A board is a name and the message it was last given; it fetches nothing.
People make and name their own boards. Anything live is pushed to a
board from outside: typed in the app, or posted by a Claude Routine
through the MCP `post_message` tool on whatever schedule the person sets.
An empty board shows its name.

## Consequences

- No feed code, keys or schedules on the server; the TV only polls its
  display's state.
- The MCP tools address boards by name (case-insensitive), and the first
  board when none is given, so a Routine's prompt names its board.
- Renaming a board breaks Routines that post to its old name; the board
  page says so, and the error lists the boards there are.
- A person can type over a board a Routine feeds; the next run replaces it.
