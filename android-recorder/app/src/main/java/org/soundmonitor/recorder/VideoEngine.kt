package org.soundmonitor.recorder

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureRequest
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.util.Range
import android.util.Size
import android.view.Surface

/**
 * Runs the back camera continuously into a hardware H.264 encoder and keeps the last minute or so of
 * encoded frames in [ring]. Clips are cut from the ring after an event, so the video starts a couple
 * of seconds before the noise. An optional preview surface (the status screen) can be attached.
 */
class VideoEngine(private val context: Context, private val ring: EncodedRing) {
    private val thread = HandlerThread("camera").apply { start() }
    private val handler = Handler(thread.looper)
    private var camera: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var encoder: MediaCodec? = null
    private var encoderSurface: Surface? = null
    private var previewSurface: Surface? = null
    private var drainThread: Thread? = null
    @Volatile private var running = false
    @Volatile private var ptsOffsetUs = Long.MIN_VALUE
    var size: Size = Size(640, 480)
        private set
    @Volatile private var sensorOrientation = 0
    @Volatile private var frontFacing = false

    /**
     * Rotation to store in each video file so it plays upright (camera sensors are usually mounted
     * sideways). Uses the screen rotation the status screen last saw, plus any manual correction.
     */
    val rotationDegrees: Int
        get() {
            val p = Prefs(context)
            @Suppress("DEPRECATION")
            val display = p.displayRotation.takeIf { it >= 0 } ?: when (
                (context.getSystemService(Context.WINDOW_SERVICE) as android.view.WindowManager).defaultDisplay.rotation) {
                Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0
            }
            val auto = if (frontFacing) (sensorOrientation + display) % 360 else (sensorOrientation - display + 360) % 360
            return (auto + p.videoRotationExtra) % 360
        }

    @SuppressLint("MissingPermission")
    fun start() {
        if (running) return
        running = true
        handler.post {
            try {
                val mgr = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                val id = pickCamera(mgr) ?: run { fail("No camera found"); return@post }
                val chars = mgr.getCameraCharacteristics(id)
                val map = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)!!
                sensorOrientation = chars.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 0
                frontFacing = chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_FRONT
                size = pickSize(map.getOutputSizes(MediaCodec::class.java) ?: emptyArray())
                startEncoder()
                mgr.openCamera(id, object : CameraDevice.StateCallback() {
                    override fun onOpened(cd: CameraDevice) { camera = cd; createSession() }
                    override fun onDisconnected(cd: CameraDevice) { cd.close(); camera = null; fail("Camera disconnected") }
                    override fun onError(cd: CameraDevice, error: Int) { cd.close(); camera = null; fail("Camera error $error") }
                }, handler)
            } catch (e: Exception) {
                Log.e(TAG, "camera start failed", e)
                fail("Camera failed: ${e.message}")
            }
        }
    }

    fun stop() {
        running = false
        handler.post {
            try { session?.close() } catch (_: Exception) {}
            try { camera?.close() } catch (_: Exception) {}
            session = null; camera = null
        }
        drainThread?.join(3000)
        drainThread = null
        handler.post {
            try { encoder?.stop() } catch (_: Exception) {}
            encoder?.release(); encoder = null
            encoderSurface?.release(); encoderSurface = null
        }
        ring.clear()
        ptsOffsetUs = Long.MIN_VALUE
        Status.cameraText = "Off"
    }

    fun quit() { stop(); thread.quitSafely() }

    /** Attach or detach the on-screen preview. Rebuilds the capture session. */
    fun setPreview(surface: Surface?) {
        handler.post {
            previewSurface = surface
            if (camera != null && running) createSession()
        }
    }

    private fun fail(msg: String) {
        Status.cameraText = msg
        Log.w(TAG, msg)
    }

    private fun pickCamera(mgr: CameraManager): String? {
        val ids = mgr.cameraIdList
        return ids.firstOrNull {
            mgr.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
        } ?: ids.firstOrNull()
    }

    /** About 640 px wide: plenty to see cars, small enough for cheap encoders and uploads. */
    private fun pickSize(sizes: Array<Size>): Size {
        if (sizes.isEmpty()) return Size(640, 480)
        val ok = sizes.filter { it.width in 600..1280 && it.height <= 720 }
        return (ok.ifEmpty { sizes.toList() }).minByOrNull { kotlin.math.abs(it.width - 640) }!!
    }

    private fun startEncoder() {
        val fmt = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, size.width, size.height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, 800_000)
            setInteger(MediaFormat.KEY_FRAME_RATE, 15)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        }
        val enc = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        enc.configure(fmt, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        encoderSurface = enc.createInputSurface()
        enc.start()
        encoder = enc
        drainThread = Thread({ drainLoop(enc) }, "video-drain").apply { start() }
    }

    private fun drainLoop(enc: MediaCodec) {
        val info = MediaCodec.BufferInfo()
        while (running) {
            val idx = try { enc.dequeueOutputBuffer(info, 50_000) } catch (e: Exception) { break }
            when {
                idx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> ring.setFormat(enc.outputFormat)
                idx >= 0 -> {
                    // Camera timestamps use a different clock than the audio. Line them up once,
                    // on the first frame, then keep the camera's own frame spacing.
                    if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                        if (ptsOffsetUs == Long.MIN_VALUE) ptsOffsetUs = System.nanoTime() / 1000 - info.presentationTimeUs
                        ring.add(enc.getOutputBufferCompat(idx), info, info.presentationTimeUs + ptsOffsetUs)
                    }
                    enc.releaseOutputBuffer(idx, false)
                }
            }
        }
    }

    private fun createSession() {
        val cd = camera ?: return
        val encSurf = encoderSurface ?: return
        try { session?.close() } catch (_: Exception) {}
        val targets = listOfNotNull(encSurf, previewSurface)
        @Suppress("DEPRECATION")
        cd.createCaptureSession(targets, object : CameraCaptureSession.StateCallback() {
            override fun onConfigured(s: CameraCaptureSession) {
                session = s
                try {
                    val req = cd.createCaptureRequest(CameraDevice.TEMPLATE_RECORD).apply {
                        targets.forEach { addTarget(it) }
                        set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
                        set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, Range(10, 15))
                    }
                    s.setRepeatingRequest(req.build(), null, handler)
                    Status.cameraText = "On · ${size.width}×${size.height}"
                } catch (e: Exception) {
                    // Some cameras reject a 10-15 fps range; retry with the default.
                    try {
                        val req = cd.createCaptureRequest(CameraDevice.TEMPLATE_RECORD).apply { targets.forEach { addTarget(it) } }
                        s.setRepeatingRequest(req.build(), null, handler)
                        Status.cameraText = "On · ${size.width}×${size.height}"
                    } catch (e2: Exception) { fail("Camera failed: ${e2.message}") }
                }
            }
            override fun onConfigureFailed(s: CameraCaptureSession) {
                if (previewSurface != null) { previewSurface = null; createSession() } else fail("Camera session failed")
            }
        }, handler)
    }

    companion object { private const val TAG = "VideoEngine" }
}
