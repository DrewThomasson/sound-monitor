package org.soundmonitor.recorder

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Settings: where to upload, when, and how sensitive detection is. Set once, rarely touched. */
class SettingsActivity : Activity() {
    private lateinit var prefs: Prefs
    private lateinit var site: EditText
    private lateinit var repo: EditText
    private lateinit var token: EditText
    private lateinit var times: EditText
    private lateinit var margin: EditText
    private lateinit var calibration: EditText
    private lateinit var videoMin: EditText
    private lateinit var minFree: EditText
    private lateinit var rotation: EditText
    private lateinit var video: CheckBox
    private lateinit var dropWind: CheckBox
    private lateinit var result: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(16), dp(16), dp(16), dp(32)) }
        fun header(t: String) = root.addView(TextView(this).apply {
            text = t; textSize = 18f; setTypeface(typeface, Typeface.BOLD); setPadding(0, dp(20), 0, dp(4))
        })
        fun field(label: String, value: String, hint: String = "", type: Int = InputType.TYPE_CLASS_TEXT): EditText {
            root.addView(TextView(this).apply { text = label; alpha = 0.75f; setPadding(0, dp(8), 0, 0) })
            return EditText(this).apply { setText(value); this.hint = hint; inputType = type; setSingleLine() }.also { root.addView(it) }
        }
        val num = InputType.TYPE_CLASS_NUMBER
        val signedDec = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL or InputType.TYPE_NUMBER_FLAG_SIGNED

        header("Site and upload")
        site = field("Site name (used as the folder name in the dataset)", prefs.site, "porch-5th-floor")
        repo = field("Hugging Face dataset", prefs.repo, "user/dataset-name")
        token = field("Hugging Face token (needs write access)", prefs.token, "hf_…",
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        times = field("Upload times (24-hour, comma separated)", prefs.uploadTimes, "07:00,19:00")

        header("Detection")
        margin = field("Start an event this many dB above the background level", fmt(prefs.marginDb), "18", signedDec)
        calibration = field("Calibration offset in dB (from a sound level meter; 0 if unknown)", fmt(prefs.calibrationDb), "0", signedDec)
        dropWind = CheckBox(this).apply { text = "Discard events that look like wind (otherwise they're kept and flagged)"; isChecked = prefs.dropWind }
        root.addView(dropWind)

        header("Recording")
        video = CheckBox(this).apply { text = "Record a video of each event"; isChecked = prefs.videoEnabled }
        root.addView(video)
        videoMin = field("Minimum video length (seconds)", prefs.videoMinSeconds.toString(), "15", num)
        rotation = field("Extra video rotation if videos come out turned (0, 90, 180 or 270)", prefs.videoRotationExtra.toString(), "0", num)
        minFree = field("Stop saving clips when free space is below (MB)", prefs.minFreeMb.toString(), "1024", num)

        val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, dp(20), 0, 0) }
        buttons.addView(Button(this).apply { text = "Save"; setOnClickListener { save() } },
            LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        buttons.addView(Button(this).apply { text = "Test connection"; setOnClickListener { save(); testConnection() } },
            LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        root.addView(buttons)
        result = TextView(this).apply { setPadding(0, dp(12), 0, 0); textSize = 15f }
        root.addView(result)

        if (Build.VERSION.SDK_INT >= 23) {
            header("Restart after a power cut")
            root.addView(TextView(this).apply {
                text = "Android only lets the app reopen itself after a reboot if it's allowed to display over other apps. " +
                    "Without this, you'll get a notification to tap instead."
                alpha = 0.75f
            })
            root.addView(Button(this).apply {
                text = if (Settings.canDrawOverlays(this@SettingsActivity)) "Allowed ✓" else "Allow auto-restart"
                setOnClickListener {
                    try {
                        startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                    } catch (_: Exception) {
                        result.text = "This tablet doesn't offer that setting. Use the notification after a reboot."
                    }
                }
            })
        }
        root.addView(TextView(this).apply {
            text = "\nFiles go to sites/<site name>/ in the dataset. Changes to video take effect the next time recording starts."
            alpha = 0.6f; textSize = 13f
        })
        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private fun fmt(f: Float) = if (f == f.toInt().toFloat()) f.toInt().toString() else f.toString()

    private fun save() {
        val problems = mutableListOf<String>()
        prefs.site = site.text.toString().trim().ifEmpty { "porch-5th-floor" }
        val r = repo.text.toString().trim()
        if (Regex("^[\\w.-]+/[\\w.-]+$").matches(r)) prefs.repo = r else problems += "Dataset should look like user/name"
        prefs.token = token.text.toString().trim()
        val t = times.text.toString().trim()
        prefs.uploadTimes = t
        if (prefs.parsedUploadTimes().isEmpty()) { problems += "Upload times should look like 07:00,19:00"; prefs.uploadTimes = "07:00,19:00" }
        margin.text.toString().toFloatOrNull()?.takeIf { it in 3f..60f }?.let { prefs.marginDb = it } ?: run { problems += "Margin should be 3-60 dB" }
        calibration.text.toString().toFloatOrNull()?.takeIf { it in -60f..60f }?.let { prefs.calibrationDb = it } ?: run { problems += "Calibration should be -60 to 60 dB" }
        videoMin.text.toString().toIntOrNull()?.takeIf { it in 5..60 }?.let { prefs.videoMinSeconds = it } ?: run { problems += "Video length should be 5-60 s" }
        minFree.text.toString().toIntOrNull()?.takeIf { it >= 100 }?.let { prefs.minFreeMb = it } ?: run { problems += "Free space limit should be at least 100 MB" }
        rotation.text.toString().toIntOrNull()?.takeIf { it in listOf(0, 90, 180, 270) }?.let { prefs.videoRotationExtra = it }
            ?: run { problems += "Rotation should be 0, 90, 180 or 270" }
        prefs.videoEnabled = video.isChecked
        prefs.dropWind = dropWind.isChecked
        result.text = if (problems.isEmpty()) "Saved" else problems.joinToString("\n")
    }

    private fun testConnection() {
        val tok = prefs.token
        if (tok.isBlank()) { result.text = "Enter a token first"; return }
        result.text = "Checking…"
        Thread {
            val msg = try {
                val (name, canWrite) = HfUploader(prefs.repo, tok).whoami()
                if (canWrite) "Connected as $name. Token can write." else "Connected as $name, but this token is read-only. Create one with write access."
            } catch (e: Exception) { "Couldn't connect: ${e.message?.take(150)}" }
            runOnUiThread { result.text = msg }
        }.start()
    }
}
