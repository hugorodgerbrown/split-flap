"""Add a board, post to it from the display page, then delete it.

Scenario: boards (docs/testing.md, "Journeys").
"""

from typing import Any

from playwright.sync_api import Page, expect


def test_add_post_and_delete_a_board(signed_in_page: Page, live_server: Any) -> None:
    """The preview follows the message box, and Save puts it on the display."""
    page = signed_in_page
    page.goto(f"{live_server.url}/app/display/")
    page.get_by_label("New board").fill("News")
    page.get_by_role("button", name="Add board").click()
    expect(page.get_by_role("link", name="News", exact=True)).to_have_attribute(
        "aria-current", "page"
    )

    save = page.get_by_role("button", name="Save")
    expect(save).to_be_disabled()
    page.get_by_label("Message").fill("Rail strike off ")
    page.get_by_role("button", name="Train").click()
    preview = page.get_by_role("img", name="News: Rail strike off :train:")
    expect(preview).to_be_visible()
    expect(preview.locator("use")).to_have_count(2)  # the pictogram, on both halves of its flap
    expect(page.get_by_text("Draft", exact=True)).to_be_visible()
    save.click()

    expect(page.get_by_text("On the display", exact=True)).to_be_visible()
    expect(page.get_by_text("Posted")).to_be_visible()
    page.get_by_role("link", name="Delete News…").click()
    page.get_by_role("button", name="Delete board").click()
    expect(page.get_by_role("link", name="News", exact=True)).to_have_count(0)
    expect(page.get_by_role("link", name="Home", exact=True)).to_be_visible()
