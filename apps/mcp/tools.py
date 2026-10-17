"""The MCP tools. Each is a function of (user, arguments) returning JSON-able data.

Add a tool by writing a function and listing it in TOOLS with its JSON
Schema. Raise ToolError for a mistake the model should see and correct.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from apps.boards.services import BoardError, display_for, find_board, post_message
from apps.notes.forms import NoteForm
from apps.notes.models import Note
from apps.public.pages import page_as_markdown


class ToolError(Exception):
    """A problem with the call that the model can fix and retry."""


@dataclass(frozen=True)
class Tool:
    """One MCP tool: its name, description, input schema and implementation."""

    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[[Any, dict[str, Any]], dict[str, Any]]
    read_only: bool = True
    # The result's "markdown" is the text content, so the caller gets the
    # document itself rather than JSON around it.
    markdown: bool = False
    # A ui:// resource in apps/mcp/resources.py that the client renders with
    # the result (an MCP App). The text content still goes to the model.
    ui: str | None = None

    def describe(self) -> dict[str, Any]:
        """Return the tool as tools/list lists it."""
        described: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {"readOnlyHint": self.read_only},
        }
        if self.ui:
            # "ui/resourceUri" is the spec's older flat key, kept until every
            # client reads the nested one.
            described["_meta"] = {"ui": {"resourceUri": self.ui}, "ui/resourceUri": self.ui}
        return described


def list_notes(user: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Return the user's latest notes, newest first."""
    limit = args.get("limit", 20)
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ToolError("limit must be a whole number from 1 to 100.")
    notes = Note.objects.for_user(user)[:limit]
    return {
        "notes": [
            {"uuid": str(n.uuid), "text": n.text, "written_at": n.written_at.isoformat()}
            for n in notes
        ]
    }


def add_note(user: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Add a note for the user."""
    form = NoteForm({"text": args.get("text", "")})
    if not form.is_valid():
        raise ToolError("; ".join(f"{k}: {' '.join(map(str, v))}" for k, v in form.errors.items()))
    note = form.save(commit=False)
    note.owner = user
    note.save()
    return {"uuid": str(note.uuid), "text": note.text, "written_at": note.written_at.isoformat()}


def list_boards(user: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Return every board on the user's display and what each shows."""
    display = display_for(user)
    return {"display": display.name, "boards": [b.as_json() for b in display.boards.all()]}


def _board_name(args: dict[str, Any]) -> str | None:
    """Return the board name a tool was given, if any."""
    name = args.get("board")
    if name is not None and not isinstance(name, str):
        raise ToolError("board must be a string.")
    return name


def get_board(user: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Return one board on the user's display."""
    try:
        board = find_board(display_for(user), _board_name(args))
    except BoardError as error:
        raise ToolError(str(error)) from error
    return board.as_json()


def post_board_message(user: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Show a message on one of the user's boards."""
    text = args.get("text", "")
    if not isinstance(text, str):
        raise ToolError("text must be a string.")
    try:
        board = post_message(display_for(user), text, _board_name(args))
    except BoardError as error:
        raise ToolError(str(error)) from error
    return board.as_json()


def privacy_policy(user: Any, args: dict[str, Any]) -> dict[str, str]:
    """Return the privacy notice: what is kept about the user, and why."""
    return page_as_markdown("privacy")


def terms_of_service(user: Any, args: dict[str, Any]) -> dict[str, str]:
    """Return the terms of service."""
    return page_as_markdown("terms")


def help_page(user: Any, args: dict[str, Any]) -> dict[str, str]:
    """Return the help: signing in, passkeys, installing, offline use."""
    return page_as_markdown("help")


NO_ARGUMENTS: dict[str, Any] = {"type": "object", "properties": {}}

TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool(
            name="list_notes",
            description="List the user's latest notes, newest first.",
            input_schema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            },
            func=list_notes,
            ui="ui://notes/list",
        ),
        Tool(
            name="add_note",
            description="Add a note for the user.",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string", "maxLength": 2000}},
                "required": ["text"],
            },
            func=add_note,
            read_only=False,
        ),
        Tool(
            name="post_message",
            description=(
                "Show a message on the user's split-flap board, which they watch on a TV. "
                "The board has 6 rows of 22 tiles and shows capital letters, digits and "
                "! @ # $ ( ) - + & = ; : ' \" % , . / ? °. Lowercase is shown as capitals; "
                "anything else is a blank tile. Words wrap and the message is centred; use a "
                "line break to start a new row. {r} {o} {y} {g} {b} {v} {w} are red, orange, "
                "yellow, green, blue, violet and white colour tiles. These emoji show as "
                "pictograms: ☀ ⛅ ☁ 🌧 ⛈ ❄ 🌙 ☂ 🚆 ✈ 🚗 🚲 🏠 ☕ 🎵 📰 ❤ ★ 😊 ✓ ✗ ↑ ↓ ← →. "
                "The TV turns to the board within a few seconds and shows the message until "
                "the next one; boards fetch nothing themselves. An empty text clears the "
                "board, which then shows its name."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "maxLength": 400},
                    "board": {
                        "type": "string",
                        "maxLength": 40,
                        "description": (
                            "The board's name, as list_boards gives it; case doesn't matter. "
                            "Leave it out for the first board."
                        ),
                    },
                },
                "required": ["text"],
            },
            func=post_board_message,
            read_only=False,
        ),
        Tool(
            name="get_board",
            description="What one board on the user's split-flap display is showing.",
            input_schema={
                "type": "object",
                "properties": {
                    "board": {
                        "type": "string",
                        "maxLength": 40,
                        "description": (
                            "The board's name, as list_boards gives it; case doesn't matter. "
                            "Leave it out for the first board."
                        ),
                    }
                },
            },
            func=get_board,
        ),
        Tool(
            name="list_boards",
            description=(
                "List the boards on the user's split-flap display, in the order the TV shows "
                "them, with the message each shows. The user names their boards; an empty "
                "message means the board shows its name."
            ),
            input_schema=NO_ARGUMENTS,
            func=list_boards,
        ),
        Tool(
            name="privacy_policy",
            description=(
                "The privacy notice: what is kept about the user, why, and for how long. "
                "Use it for any question about privacy or personal data."
            ),
            input_schema=NO_ARGUMENTS,
            func=privacy_policy,
            markdown=True,
        ),
        Tool(
            name="terms_of_service",
            description="The terms of service for using the app.",
            input_schema=NO_ARGUMENTS,
            func=terms_of_service,
            markdown=True,
        ),
        Tool(
            name="help",
            description=(
                "How to use the app: signing in, passkeys, installing it and using it offline."
            ),
            input_schema=NO_ARGUMENTS,
            func=help_page,
            markdown=True,
        ),
    ]
}
