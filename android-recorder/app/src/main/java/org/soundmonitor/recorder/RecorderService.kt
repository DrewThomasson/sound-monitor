package org.soundmonitor.recorder

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.StatFs
import android.util.Log
import android.view.Surface
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

/**
 * The always-on recorder. Runs as a foreground service (with a permanent notification) so Fire OS
 * doesn't kill it, holds a partial wake lock so it keeps working with the screen off, and:
 *  - listens continuously and saves an audio clip + video for every loud event,
 *  - logs the sound level every second,
 *  - uploads everything to the Hugging Face dataset at the scheduled times.
 */
class RecorderService : Service() {
    private lateinit var prefs: Prefs
    private lateinit var store: EventStore
    private lateinit var outbox: File
    private val audioRing = EncodedRing(75_000_000L)
    private val videoRing = EncodedRing(75_000_000L)
    private var audio: AudioEngine? = null
    private var video: VideoEngine? = null
    private lateinit var detector: EventDetector
    private val clipExecutor = Executors.newSingleThreadExecutor()
    private val uploadExecutor = Executors.newSingleThreadExecutor()
    private lateinit var tick: Handler
    private val tickThread = HandlerThread("tick").apply { start() }
    private val main = Handler(Looper.getMainLooper())
    private var wakeLock: PowerManager.WakeLock? = null
    private var levelWriter: FileWriter? = null
    private var levelHourKey = ""
    private var levelFile: File? = null
    private var nextRetryMs = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        prefs = Prefs(this)
        store = EventStore(this)
        outbox = File(filesDir, "outbox").apply { mkdirs() }
        tick = Handler(tickThread.looper)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { stopEverything(); stopSelf(); return START_NOT_STICKY }
            ACTION_UPLOAD -> { if (Status.running) uploadNow(); return START_STICKY }
            ACTION_TEST_EVENT -> { if (Status.running) testEvent(); return START_STICKY }
        }
        if (Status.running) return START_STICKY
        if (!micAllowed()) { notifyMicMissing(); stopSelf(); return START_NOT_STICKY }
        goForeground()
        startEverything()
        return START_STICKY
    }

    private fun goForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Recording", NotificationManager.IMPORTANCE_LOW))
        }
        val n = buildNotification("Starting…")
        if (Build.VERSION.SDK_INT >= 30) {
            var type = ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            if (videoAllowed()) type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA
            startForeground(NOTIF_ID, n, type)
        } else {
            startForeground(NOTIF_ID, n)
        }
    }

    private fun buildNotification(text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        @Suppress("DEPRECATION")
        val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL) else Notification.Builder(this)
        return b.setContentTitle("Street Noise Recorder")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setContentIntent(pi)
            .build()
    }

    private fun micAllowed(): Boolean = Build.VERSION.SDK_INT < 23 ||
        checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED

    /** Android can take the mic permission back (for example a one-time grant); say so instead of stopping silently. */
    private fun notifyMicMissing() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(NotificationChannel(ALERT_CHANNEL, "Problems", NotificationManager.IMPORTANCE_HIGH))
        }
        val pi = PendingIntent.getActivity(
            this, 2, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        @Suppress("DEPRECATION")
        val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, ALERT_CHANNEL) else Notification.Builder(this)
        nm.notify(ALERT_ID, b.setContentTitle("Recording stopped")
            .setContentText("Microphone permission was removed. Tap to fix.")
            .setSmallIcon(android.R.drawable.stat_notify_error)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .build())
    }

    /** Day logs left as .part (the app wasn't running at midnight) are finished so they upload. */
    private fun finishOldLevelFiles() {
        val today = hourFmt.format(Date())
        File(outbox, "sites/${prefs.siteSlug}/levels").listFiles()?.forEach {
            if (it.name.endsWith(".csv.part") && !it.name.startsWith(today)) finishLevelFile(it)
        }
    }

    private fun startEverything() {
        (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).cancel(ALERT_ID)
        try { finishOldLevelFiles() } catch (e: Exception) { Log.w(TAG, "level cleanup failed", e) }
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "streetnoise:recorder").apply {
            setReferenceCounted(false); acquire()
        }
        Status.running = true
        Status.startedAtMs = System.currentTimeMillis()
        Status.warning = ""
        detector = EventDetector({ prefs.marginDb }, { ev -> onEvent(ev) })
        detector.onSecond = { ptsUs, db, max -> logSecond(wallMs(ptsUs), db, max) }
        val eng = AudioEngine(audioRing, { prefs.calibrationDb }) { c ->
            detector.onChunk(c, prefs.calibrationDb)
        }
        audio = eng
        eng.start()
        if (prefs.lastUploadAttemptMs == 0L) prefs.lastUploadAttemptMs = System.currentTimeMillis()
        if (videoAllowed()) {
            video = VideoEngine(this, videoRing).also { it.start() }
            pendingPreview?.let { video?.setPreview(it) }
        }
        tick.post(tickRunnable)
    }

    private fun stopEverything() {
        tick.removeCallbacksAndMessages(null)
        audio?.stop(); audio = null
        video?.quit(); video = null
        Status.running = false
        Status.inEvent = false
        synchronized(this) {
            try { levelWriter?.close() } catch (_: Exception) {}
            levelWriter = null
            levelFile?.let { finishLevelFile(it) }
            levelFile = null; levelHourKey = ""
        }
        wakeLock?.release(); wakeLock = null
    }

    override fun onDestroy() {
        stopEverything()
        clipExecutor.shutdown()
        uploadExecutor.shutdown()
        tickThread.quitSafely()
        instance = null
        super.onDestroy()
    }

    // ---- Events -----------------------------------------------------------------------------

    private val tsFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
    private val nameFmt = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
    private val dayFmt = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    /** Wall-clock time (ms) for a timestamp on the audio clock (µs from System.nanoTime). */
    private fun wallMs(ptsUs: Long): Long = System.currentTimeMillis() - (System.nanoTime() / 1000 - ptsUs) / 1000

    private fun onEvent(ev: EventDetector.Event) {
        if (ev.windSuspected && prefs.dropWind) return
        val startWall = Date(wallMs(ev.startUs))
        val day = dayFmt.format(startWall)
        val name = "event_${nameFmt.format(startWall)}"
        val site = prefs.siteSlug
        val audioPath = "sites/$site/recordings/$day/$name.m4a"
        val videoPath = "sites/$site/videos/$day/$name.mp4"
        val lowSpace = freeBytes() < prefs.minFreeMb * 1024L * 1024L
        if (lowSpace) Status.warning = "Storage low: clips paused until the next upload"

        val fromUs = ev.startUs - 2_000_000L
        val audioTo = ev.endUs
        val videoTo = maxOf(ev.endUs, ev.startUs + prefs.videoMinSeconds * 1_000_000L)
        val withVideo = video != null && !lowSpace

        clipExecutor.execute {
            var audioOk = false
            var videoOk = false
            if (!lowSpace) {
                // Wait until the rings hold everything up to the end of the clip.
                val waitUntil = System.currentTimeMillis() + (videoTo - ev.startUs) / 1000 + 5000
                while (audioRing.latestUs() < audioTo && System.currentTimeMillis() < waitUntil) Thread.sleep(200)
                if (withVideo) {
                    while (videoRing.latestUs() < videoTo && System.currentTimeMillis() < waitUntil) Thread.sleep(200)
                    val v = videoRing.slice(fromUs, videoTo, true)
                    if (v.isNotEmpty()) {
                        val a = audioRing.slice(v.first().ptsUs, videoTo, false)
                        videoOk = ClipWriter.write(File(outbox, videoPath), a, audioRing, v, videoRing, video?.rotationDegrees ?: 0)
                    }
                }
                // The video already holds the sound, so a separate audio file is only needed without one.
                // That halves the number of files uploaded (Hugging Face recommends < 100k per repo).
                if (!videoOk) {
                    audioOk = ClipWriter.write(File(outbox, audioPath), audioRing.slice(fromUs, audioTo, false), audioRing, null, null)
                }
            }
            store.insert(ContentValues().apply {
                put("timestamp", tsFmt.format(startWall))
                put("duration", ev.durationS)
                put("peak_db", ev.peakDb.toDouble())
                put("avg_db", ev.avgDb.toDouble())
                put("background_db", ev.backgroundDb.toDouble())
                put("filename", if (audioOk) audioPath else if (videoOk) videoPath else "")
                put("video_filename", if (videoOk) videoPath else "")
                put("low_frequency", if (ev.lowFrequency) 1 else 0)
                put("wind_suspected", if (ev.windSuspected) 1 else 0)
                put("site", prefs.site)
                put("calibration_db", prefs.calibrationDb.toDouble())
            })
            val today = dayFmt.format(Date())
            if (Status.eventsTodayDate != today) { Status.eventsTodayDate = today; Status.eventsToday = 0 }
            Status.eventsToday++
            Status.lastEventText = "${SimpleDateFormat("h:mm a", Locale.US).format(startWall)} · ${"%.0f".format(ev.peakDb)} dB" +
                (if (ev.windSuspected) " (wind?)" else "")
        }
    }

    // ---- Per-second level log ---------------------------------------------------------------

    private val hourFmt = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    @Synchronized private fun logSecond(now: Long, db: Float, max: Float) {
        val key = hourFmt.format(Date(now))
        try {
            if (key != levelHourKey) {
                levelWriter?.close()
                levelFile?.let { finishLevelFile(it) }
                levelHourKey = key
                val f = File(outbox, "sites/${prefs.siteSlug}/levels/$key.csv.part")
                f.parentFile?.mkdirs()
                val isNew = !f.exists()
                levelFile = f
                levelWriter = FileWriter(f, true).also { if (isNew) it.write("unix_time,level_db,max_db\n") }
            }
            levelWriter?.write("${now / 1000},${"%.1f".format(Locale.US, db)},${"%.1f".format(Locale.US, max)}\n")
            levelWriter?.flush()
        } catch (e: Exception) { Log.w(TAG, "level log failed", e) }
    }

    /** A finished day: drop ".part" so it gets uploaded. */
    private fun finishLevelFile(f: File) {
        if (f.exists()) f.renameTo(File(f.path.removeSuffix(".part")))
    }

    // ---- Housekeeping and scheduled uploads -------------------------------------------------

    private val tickRunnable = object : Runnable {
        override fun run() {
            try { housekeeping() } catch (e: Exception) { Log.w(TAG, "tick failed", e) }
            tick.postDelayed(this, 30_000)
        }
    }

    private fun housekeeping() {
        Status.freeBytes = freeBytes()
        Status.pendingBytes = outbox.walkTopDown().filter { it.isFile }.sumOf { it.length() }
        val bat = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        if (bat != null) {
            val lvl = bat.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) * 100 / bat.getIntExtra(BatteryManager.EXTRA_SCALE, 100).coerceAtLeast(1)
            val temp = bat.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) / 10f
            val plugged = bat.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0
            Status.batteryText = "$lvl%${if (plugged) " charging" else " ON BATTERY"} · ${"%.0f".format(temp)}°C"
            Status.warning = when {
                temp >= 45f -> "Tablet is hot (${"%.0f".format(temp)}°C). Move it out of the sun."
                !plugged && lvl < 30 -> "Tablet isn't charging"
                Status.freeBytes < prefs.minFreeMb * 1024L * 1024L -> "Storage low: clips paused until the next upload"
                Status.warning.startsWith("Tablet") || Status.warning.startsWith("Storage") -> ""
                else -> Status.warning
            }
        }
        val text = buildString {
            append(if (Status.inEvent) "Loud event now" else "Listening")
            append(" · ${Status.eventsToday} events today")
            if (Status.warning.isNotEmpty()) append(" · ${Status.warning}")
        }
        (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(NOTIF_ID, buildNotification(text))

        val now = System.currentTimeMillis()
        if (!Status.uploading && (dueSince(prefs.lastUploadAttemptMs) || (nextRetryMs in 1..now))) uploadNow()
    }

    /** True if a scheduled upload time has passed since [lastMs]. */
    private fun dueSince(lastMs: Long): Boolean {
        val now = Calendar.getInstance()
        for ((h, m) in prefs.parsedUploadTimes()) {
            val t = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, h); set(Calendar.MINUTE, m); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
                if (after(now)) add(Calendar.DAY_OF_MONTH, -1)
            }
            if (t.timeInMillis > lastMs) return true
        }
        return false
    }

    fun uploadNow() {
        if (Status.uploading) return
        Status.uploading = true
        Status.uploadText = "Uploading…"
        prefs.lastUploadAttemptMs = System.currentTimeMillis()
        uploadExecutor.execute {
            val wifi = (applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager)
                .createWifiLock(WifiManager.WIFI_MODE_FULL, "streetnoise:upload")
            try {
                wifi.acquire()
                val summary = UploadJob(outbox, prefs, store).run()
                prefs.lastUploadOkMs = System.currentTimeMillis()
                prefs.lastUploadSummary = summary
                Status.uploadText = ""
                nextRetryMs = 0
            } catch (e: Exception) {
                Log.w(TAG, "upload failed", e)
                Status.uploadText = "Upload failed: ${e.message?.take(120)}. Retrying in 15 min."
                nextRetryMs = System.currentTimeMillis() + 15 * 60_000L
            } finally {
                try { wifi.release() } catch (_: Exception) {}
                Status.uploading = false
            }
        }
    }

    private fun videoAllowed(): Boolean = prefs.videoEnabled && (Build.VERSION.SDK_INT < 23 ||
        checkSelfPermission(android.Manifest.permission.CAMERA) == android.content.pm.PackageManager.PERMISSION_GRANTED)

    private fun freeBytes(): Long = try { StatFs(outbox.path).availableBytes } catch (_: Exception) { 0L }

    /** Fake 3-second event ending now, for checking clip saving and uploads without a real noise. */
    fun testEvent() {
        val now = System.nanoTime() / 1000
        val bg = Status.backgroundDb.takeIf { !it.isNaN() } ?: 0f
        onEvent(EventDetector.Event(now - 3_000_000L, now, Status.levelDb, Status.levelDb, bg, 0f))
    }

    fun setPreview(surface: Surface?) { video?.setPreview(surface) }

    companion object {
        private const val TAG = "RecorderService"
        private const val CHANNEL = "recording"
        private const val NOTIF_ID = 1
        private const val ALERT_CHANNEL = "alerts"
        private const val ALERT_ID = 3
        const val ACTION_STOP = "stop"
        const val ACTION_UPLOAD = "upload"
        const val ACTION_TEST_EVENT = "test_event"
        @Volatile var instance: RecorderService? = null
        /** Preview surface requested before the service was ready. */
        @Volatile var pendingPreview: Surface? = null

        fun start(ctx: Context, action: String? = null) {
            val i = Intent(ctx, RecorderService::class.java).setAction(action)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
        }
    }
}
