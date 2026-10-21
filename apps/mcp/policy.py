"""Who may connect an MCP client to this project (MCP_AUTH["CAN_CONNECT"]).

An MCP client acts with the user's full access, so widening this is a
product decision. Riffle uses every_account: connecting Claude is how
a person's Routines post to their boards
(docs/decisions/every-account-may-connect-claude.md). The rule runs on the
consent page and on every call, so turning an account off cuts its
clients off. staff_only is the template's narrower choice, kept for the
template.
"""

from typing import Any


def staff_only(user: Any) -> bool:
    """An active staff member may connect."""
    return bool(user.is_active and user.is_staff)


def every_account(user: Any) -> bool:
    """Any active account may connect; each reaches only its own data."""
    return bool(user.is_active)
