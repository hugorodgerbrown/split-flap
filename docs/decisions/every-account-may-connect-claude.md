# Every account may connect Claude

Status: accepted (2026-10-17)

## Context

The Titan template lets only staff connect an MCP client, because a
client acts with the user's full access, and it asks that widening be a
product decision. On Split-Flap, connecting Claude is the product:
dynamic boards (news, weather, trains) are fed by a Claude Routine that
posts to a board over MCP. If only staff can connect, nobody else can
have a live board.

## Decision

`MCP_AUTH["CAN_CONNECT"]` is `apps.mcp.policy.every_account`: any active
account may connect a client. It is set in `config/settings.py` rather
than through the template's `mcp_can_connect` question, whose choices
stop at staff and superusers. `.copier-answers.yml` keeps the template's
default, so `copier update` keeps merging cleanly. If the template
updates that settings line, keep this value.

## Consequences

- A client reaches only its own account's data: every tool works on the
  token's user (`tests/mcp/test_mcp.py`
  `test_people_only_reach_their_own_boards`).
- Turning an account off (`is_active = False`) cuts off its clients on
  their next call, because the rule runs on every call.
- The consent page names boards (it named notes too until RAS-81).
