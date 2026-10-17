package com.ultraniche.splitflap.tv

import android.content.Context

/** The little the app remembers: which display it shows, and whether to start with the TV. */
class Store(context: Context) {
    private val prefs = context.getSharedPreferences("split-flap", Context.MODE_PRIVATE)

    /** The display's board this TV shows, or null until it is paired. */
    var displayUrl: String?
        get() = prefs.getString(KEY_DISPLAY_URL, null)
        set(value) = prefs.edit().putString(KEY_DISPLAY_URL, value).apply()

    /** Open the board when the TV turns on. Off unless the person turns it on. */
    var startOnBoot: Boolean
        get() = prefs.getBoolean(KEY_START_ON_BOOT, false)
        set(value) = prefs.edit().putBoolean(KEY_START_ON_BOOT, value).apply()

    private companion object {
        const val KEY_DISPLAY_URL = "display_url"
        const val KEY_START_ON_BOOT = "start_on_boot"
    }
}
