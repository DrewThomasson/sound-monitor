package org.soundmonitor.recorder

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.SurfaceTexture
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.Surface
import android.view.TextureView
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Status screen: is it recording, how loud is it, what's waiting to upload, and a camera preview for aiming. */
class MainActivity : Activity() {
    private lateinit var prefs: Prefs
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var state: TextView
    private lateinit var level: TextView
    private lateinit var meter: MeterView
    private lateinit var levelNote: TextView
    private lateinit var stats: TextView
    private lateinit var details: TextView
    private lateinit var warning: TextView
    private lateinit var startStop: Button
    private lateinit var preview: TextureView
    private var previewSurface: Surface? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        // Show over the lock screen (e.g. after a reboot). Android only lets recording use the mic and
        // camera if it was started while this screen is actually visible.
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
        }
        setContentView(buildUi())
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
    }

    private fun saveRotation() {
        @Suppress("DEPRECATION")
        prefs.displayRotation = when (windowManager.defaultDisplay.rotation) {
            Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0
        }
    }

    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        saveRotation()
        fitPreview(preview.width, preview.height)
    }

    /** Turn the camera preview to match the screen (the standard Camera2 TextureView correction). */
    private fun fitPreview(w: Int, h: Int) {
        if (w == 0 || h == 0) return
        @Suppress("DEPRECATION")
        val rot = windowManager.defaultDisplay.rotation
        val m = android.graphics.Matrix()
        val view = android.graphics.RectF(0f, 0f, w.toFloat(), h.toFloat())
        val buf = android.graphics.RectF(0f, 0f, 480f, 640f)
        val cx = view.centerX(); val cy = view.centerY()
        if (rot == Surface.ROTATION_90 || rot == Surface.ROTATION_270) {
            buf.offset(cx - buf.centerX(), cy - buf.centerY())
            m.setRectToRect(view, buf, android.graphics.Matrix.ScaleToFit.FILL)
            val s = maxOf(h / 480f, w / 640f)
            m.postScale(s, s, cx, cy)
            m.postRotate(90f * (rot - 2), cx, cy)
        } else if (rot == Surface.ROTATION_180) {
            m.postRotate(180f, cx, cy)
        }
        preview.setTransform(m)
    }

    override fun onResume() {
        super.onResume()
        saveRotation()
        ui.post(refresher)
        if (!prefs.introSeen && intro?.isShowing != true) showIntro()
        // Recording itself starts in onWindowFocusChanged, once this screen is really visible.
        if (!hasPermissions()) askPermissions()
        // "adb shell am start -n org.soundmonitor.recorder/.MainActivity -a test_event" saves a test clip.
        val debuggable = applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0
        if (debuggable && intent?.action == RecorderService.ACTION_TEST_EVENT) {
            intent.action = null
            ui.postDelayed({ RecorderService.instance?.testEvent() }, 500)
        }
    }

    /**
     * If recording was started while this screen wasn't visible (locked screen, after a reboot), Android
     * gives it silence and no camera. Now that the screen is really visible, restart it once to fix that.
     */
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (!hasFocus || !hasPermissions()) return
        if (!Status.running) {
            if (prefs.autoStart) RecorderService.start(this)
            return
        }
        val blocked = Status.warning == "Microphone unavailable" ||
            Status.cameraText.startsWith("Camera error") || Status.cameraText.startsWith("Camera failed")
        if (blocked && System.currentTimeMillis() - lastRestartMs > 15_000) {
            lastRestartMs = System.currentTimeMillis()
            Status.warning = "Restarting recording to regain the microphone and camera…"
            stopService(Intent(this, RecorderService::class.java))
            ui.postDelayed({ RecorderService.start(this) }, 1500)
        }
    }
    private var lastRestartMs = 0L

    override fun onPause() {
        ui.removeCallbacks(refresher)
        super.onPause()
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun buildUi(): View {
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(16), dp(16), dp(16), dp(16)) }
        state = TextView(this).apply { textSize = 22f; setTypeface(typeface, Typeface.BOLD) }
        root.addView(state)
        val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER; setPadding(0, dp(8), 0, 0) }
        startStop = Button(this).apply { setOnClickListener { toggle() } }
        buttons.addView(startStop, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        buttons.addView(Button(this).apply {
            text = "Upload now"
            setOnClickListener { RecorderService.instance?.uploadNow() ?: run { Status.uploadText = "Start recording first" } }
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        buttons.addView(Button(this).apply {
            text = "Settings"
            setOnClickListener { startActivity(Intent(this@MainActivity, SettingsActivity::class.java)) }
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        root.addView(buttons)

        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, dp(12), 0, dp(12)) }
        preview = TextureView(this)
        val previewBox = FrameLayout(this).apply { setBackgroundColor(Color.BLACK); addView(preview) }
        row.addView(previewBox, LinearLayout.LayoutParams(dp(220), dp(165)))
        val right = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(16), 0, 0, 0) }
        right.addView(TextView(this).apply { text = "Sound level now"; alpha = 0.7f })
        level = TextView(this).apply { textSize = 34f; setTypeface(typeface, Typeface.BOLD) }
        right.addView(level)
        meter = MeterView(this)
        right.addView(meter, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(14)))
        levelNote = TextView(this).apply { alpha = 0.7f; textSize = 13f; setPadding(0, dp(4), 0, 0) }
        right.addView(levelNote)
        row.addView(right, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        root.addView(row)

        warning = TextView(this).apply { setTextColor(Color.rgb(230, 120, 40)); textSize = 15f; visibility = View.GONE }
        root.addView(warning)
        stats = TextView(this).apply { textSize = 17f; setPadding(0, dp(8), 0, dp(8)) }
        root.addView(stats)
        details = TextView(this).apply { textSize = 15f; setLineSpacing(0f, 1.25f) }
        root.addView(details)


        preview.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(st: SurfaceTexture, w: Int, h: Int) {
                st.setDefaultBufferSize(640, 480)
                fitPreview(w, h)
                previewSurface = Surface(st)
                RecorderService.pendingPreview = previewSurface
                RecorderService.instance?.setPreview(previewSurface)
            }
            override fun onSurfaceTextureSizeChanged(st: SurfaceTexture, w: Int, h: Int) { fitPreview(w, h) }
            override fun onSurfaceTextureDestroyed(st: SurfaceTexture): Boolean {
                RecorderService.pendingPreview = null
                RecorderService.instance?.setPreview(null)
                previewSurface?.release(); previewSurface = null
                return true
            }
            override fun onSurfaceTextureUpdated(st: SurfaceTexture) {}
        }
        return ScrollView(this).apply { addView(root) }
    }

    private var intro: android.app.AlertDialog? = null

    /** First-run explanation, including the reminder about local recording laws. */
    private fun showIntro() {
        intro = android.app.AlertDialog.Builder(this)
            .setTitle("Welcome to Street Noise Recorder")
            .setMessage(
                "This app turns a spare tablet into a round-the-clock street noise monitor.\n\n" +
                "• It listens all the time and saves a short video with sound of every loud event, such as cars revving.\n" +
                "• It logs the sound level every second.\n" +
                "• Twice a day it uploads everything to a Hugging Face dataset in your own account, so you can build evidence for your city.\n\n" +
                "To upload, you'll need a free Hugging Face account, a dataset and a write token. Settings has links for each.\n\n" +
                "Please point the camera at the street, not into homes or private spaces, and check your local laws: " +
                "some places restrict recording conversations or people without their consent. You're responsible for how you use this app."
            )
            .setPositiveButton("Open settings") { _, _ ->
                prefs.introSeen = true
                startActivity(Intent(this, SettingsActivity::class.java))
            }
            .setNegativeButton("Later") { _, _ -> prefs.introSeen = true }
            .setCancelable(false)
            .show()
    }

    private fun toggle() {
        if (Status.running) {
            stopService(Intent(this, RecorderService::class.java))
            prefs.autoStart = false
        } else {
            prefs.autoStart = true
            if (hasPermissions()) RecorderService.start(this) else askPermissions()
        }
    }

    private val time = SimpleDateFormat("MMM d, h:mm a", Locale.US)

    private val refresher = object : Runnable {
        override fun run() {
            val running = Status.running
            state.text = when {
                !running -> "Not recording"
                Status.inEvent -> "● Recording · loud event now"
                else -> "● Recording · ${prefs.site}"
            }
            state.setTextColor(if (running) Color.rgb(220, 60, 60) else Color.GRAY)
            startStop.text = if (running) "Stop" else "Start recording"
            level.text = if (running) "${"%.0f".format(Status.levelDb)} dB" else "–"
            meter.set(Status.levelDb, Status.thresholdDb, running)
            levelNote.text = when {
                !running -> ""
                Status.backgroundDb.isNaN() -> "Learning the background level (first 30 s)…"
                else -> "Background ${"%.0f".format(Status.backgroundDb)} dB · events start at ${"%.0f".format(Status.thresholdDb)} dB"
            }
            warning.text = Status.warning
            warning.visibility = if (Status.warning.isEmpty()) View.GONE else View.VISIBLE
            stats.text = "Events today: ${Status.eventsToday}    Waiting to upload: ${"%.0f".format(Status.pendingBytes / 1e6)} MB    " +
                "Free space: ${"%.1f".format(Status.freeBytes / 1e9)} GB"
            val lastOk = prefs.lastUploadOkMs
            details.text = buildString {
                append("Last event: ${Status.lastEventText}\n")
                append("Last upload: ${if (lastOk == 0L) "never" else time.format(Date(lastOk)) + " · " + prefs.lastUploadSummary}\n")
                if (Status.uploadText.isNotEmpty()) append("${Status.uploadText}\n")
                append("Upload times: ${prefs.uploadTimes}\n")
                append("Camera: ${Status.cameraText}\n")
                if (Status.batteryText.isNotEmpty()) append("Battery: ${Status.batteryText}\n")
                if (running) append("Running since: ${time.format(Date(Status.startedAtMs))}\n")
                if (prefs.repo.isBlank() || prefs.token.isBlank())
                    append("\nRecordings are kept on this tablet until you add a Hugging Face dataset and token in Settings.")
            }
            ui.postDelayed(this, 500)
        }
    }

    // ---- Permissions -------------------------------------------------------------------------

    private fun needed(): Array<String> {
        val p = mutableListOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
        if (Build.VERSION.SDK_INT >= 33) p += Manifest.permission.POST_NOTIFICATIONS
        return p.toTypedArray()
    }

    private fun hasPermissions(): Boolean = Build.VERSION.SDK_INT < 23 ||
        checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun askPermissions() {
        if (Build.VERSION.SDK_INT >= 23) requestPermissions(needed(), 1)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (hasPermissions() && prefs.autoStart && !Status.running) RecorderService.start(this)
    }
}

/** Horizontal level bar with a marker at the trigger level. */
class MeterView(context: android.content.Context) : View(context) {
    private var level = 0f
    private var trigger = Float.NaN
    private var on = false
    private val bg = android.graphics.Paint().apply { color = Color.argb(50, 128, 128, 128) }
    private val bar = android.graphics.Paint()
    private val mark = android.graphics.Paint().apply { color = Color.rgb(220, 60, 60); strokeWidth = 6f }

    fun set(levelDb: Float, triggerDb: Float, running: Boolean) { level = levelDb; trigger = triggerDb; on = running; invalidate() }

    override fun onDraw(c: android.graphics.Canvas) {
        val w = width.toFloat(); val h = height.toFloat()
        c.drawRect(0f, 0f, w, h, bg)
        if (!on) return
        // Scale 20-100 dB across the bar.
        fun x(db: Float) = ((db - 20f) / 80f).coerceIn(0f, 1f) * w
        bar.color = if (!trigger.isNaN() && level >= trigger) Color.rgb(220, 60, 60) else Color.rgb(60, 170, 90)
        c.drawRect(0f, 0f, x(level), h, bar)
        if (!trigger.isNaN()) c.drawLine(x(trigger), 0f, x(trigger), h, mark)
    }
}
