package com.ultraniche.splitflap.tv

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtocolTest {
    private val server = "https://split-flap.example"
    private val display = "$server/d/0b6f3c1e-8a2d-4f5b-9c7e-1d2e3f4a5b6c/"

    @Test
    fun readsAStartedPairing() {
        val started = Protocol.parseStarted(
            JSONObject(
                """{"code": "K7Q-4MD", "pair_url": "$server/app/display/pair/?code=K7Q4MD",
                   "poll_url": "$server/d/pair/abc/", "poll_seconds": 3, "expires_at": "x"}""",
            ),
        )
        assertEquals("K7Q-4MD", started.code)
        assertEquals("$server/d/pair/abc/", started.pollUrl)
        assertEquals(3, started.pollSeconds)
    }

    @Test
    fun keepsThePollIntervalSensible() {
        val json = JSONObject("""{"code": "A", "pair_url": "b", "poll_url": "c", "poll_seconds": 0}""")
        assertEquals(1, Protocol.parseStarted(json).pollSeconds)
    }

    @Test
    fun readsEachPollAnswer() {
        assertEquals(Protocol.Poll.Waiting, Protocol.parsePoll(200, JSONObject("""{"status": "waiting"}"""), server))
        assertEquals(
            Protocol.Poll.Paired(display, "Living room"),
            Protocol.parsePoll(
                200,
                JSONObject("""{"status": "paired", "display_url": "$display", "display_name": "Living room"}"""),
                server,
            ),
        )
        assertEquals(Protocol.Poll.Expired, Protocol.parsePoll(410, JSONObject("""{"status": "expired"}"""), server))
        assertEquals(Protocol.Poll.Expired, Protocol.parsePoll(404, null, server))
        assertEquals(Protocol.Poll.Expired, Protocol.parsePoll(200, JSONObject("{}"), server))
    }

    @Test
    fun refusesALinkToAnotherSite() {
        val elsewhere = JSONObject(
            """{"status": "paired", "display_url": "https://evil.example/d/0b6f3c1e-8a2d-4f5b-9c7e-1d2e3f4a5b6c/"}""",
        )
        assertEquals(Protocol.Poll.Expired, Protocol.parsePoll(200, elsewhere, server))
    }

    @Test
    fun onlyOpensADisplaysBoard() {
        assertTrue(Protocol.isDisplayUrl(display, server))
        assertFalse(Protocol.isDisplayUrl("http://split-flap.example/d/0b6f3c1e-8a2d-4f5b-9c7e-1d2e3f4a5b6c/", server))
        assertFalse(Protocol.isDisplayUrl("$server/app/", server))
        assertFalse(Protocol.isDisplayUrl("$display?x=1", server))
        assertFalse(Protocol.isDisplayUrl("not a url", server))
    }

    @Test
    fun followsOnlyOwnPages() {
        assertTrue(Protocol.isOwnPage("$server/d/pair/abc/", server))
        assertTrue(Protocol.isOwnPage("https://SPLIT-FLAP.example:443/", server))
        assertFalse(Protocol.isOwnPage("https://split-flap.example.evil/", server))
        assertFalse(Protocol.isOwnPage("javascript:alert(1)", server))
    }

    @Test
    fun showsTheAddressToType() {
        assertEquals("split-flap.example/app/display/pair/", Protocol.typedPairAddress(server))
    }
}
