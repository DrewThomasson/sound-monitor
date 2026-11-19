package org.soundmonitor.recorder

import android.content.Context
import android.content.SharedPreferences

/** All user settings, stored in the app's private SharedPreferences. */
class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.applicationContext.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var site: String
        get() = sp.getString("site", "porch-5th-floor")!!
        set(v) = sp.edit().putString("site", v).apply()

    var repo: String
        get() = sp.getString("repo", "drewThomasson/sound-monitor-porch")!!
        set(v) = sp.edit().putString("repo", v).apply()

    var token: String
        get() = sp.getString("token", "")!!
        set(v) = sp.edit().putString("token", v).apply()

    /** Comma-separated 24h times, e.g. "07:00,19:00". */
    var uploadTimes: String
        get() = sp.getString("upload_times", "07:00,19:00")!!
        set(v) = sp.edit().putString("upload_times", v).apply()

    /** dB above the rolling background level that starts an event. */
    var marginDb: Float
        get() = sp.getFloat("margin_db", 18f)
        set(v) = sp.edit().putFloat("margin_db", v).apply()

    /** Added to every level reading; set from a sound level meter. */
    var calibrationDb: Float
        get() = sp.getFloat("calibration_db", 0f)
        set(v) = sp.edit().putFloat("calibration_db", v).apply()

    /** Drop events that look like wind instead of only flagging them. */
    var dropWind: Boolean
        get() = sp.getBoolean("drop_wind", false)
        set(v) = sp.edit().putBoolean("drop_wind", v).apply()

    var videoEnabled: Boolean
        get() = sp.getBoolean("video", true)
        set(v) = sp.edit().putBoolean("video", v).apply()

    /** Minimum length of each event video, in seconds. */
    var videoMinSeconds: Int
        get() = sp.getInt("video_min_s", 15)
        set(v) = sp.edit().putInt("video_min_s", v).apply()

    /** Extra rotation (0/90/180/270) if the tablet is mounted so videos come out turned. */
    var videoRotationExtra: Int
        get() = sp.getInt("video_rotation_extra", 0)
        set(v) = sp.edit().putInt("video_rotation_extra", v).apply()

    /** Screen rotation (0/90/180/270) last seen by the status screen; background services can't read it reliably. */
    var displayRotation: Int
        get() = sp.getInt("display_rotation", -1)
        set(v) = sp.edit().putInt("display_rotation", v).apply()

    /** Stop saving clips when free space falls below this many MB. */
    var minFreeMb: Int
        get() = sp.getInt("min_free_mb", 1024)
        set(v) = sp.edit().putInt("min_free_mb", v).apply()

    /** Start recording automatically when the app opens and after a reboot. */
    var autoStart: Boolean
        get() = sp.getBoolean("auto_start", true)
        set(v) = sp.edit().putBoolean("auto_start", v).apply()

    var lastUploadAttemptMs: Long
        get() = sp.getLong("last_upload_attempt", 0L)
        set(v) = sp.edit().putLong("last_upload_attempt", v).apply()

    var lastUploadOkMs: Long
        get() = sp.getLong("last_upload_ok", 0L)
        set(v) = sp.edit().putLong("last_upload_ok", v).apply()

    var lastUploadSummary: String
        get() = sp.getString("last_upload_summary", "")!!
        set(v) = sp.edit().putString("last_upload_summary", v).apply()

    /** Site name made safe for use as a folder name. */
    val siteSlug: String
        get() = site.trim().lowercase().replace(Regex("[^a-z0-9._-]+"), "-").trim('-').ifEmpty { "site" }

    fun parsedUploadTimes(): List<Pair<Int, Int>> =
        uploadTimes.split(',').mapNotNull { t ->
            val p = t.trim().split(':')
            val h = p.getOrNull(0)?.toIntOrNull()
            val m = p.getOrNull(1)?.toIntOrNull() ?: 0
            if (h != null && h in 0..23 && m in 0..59) h to m else null
        }
}
