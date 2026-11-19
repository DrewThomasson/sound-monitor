package org.soundmonitor.recorder

import android.content.Context
import android.graphics.SurfaceTexture
import android.hardware.Camera
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLDisplay
import android.opengl.EGLExt
import android.opengl.EGLSurface
import android.opengl.GLES11Ext
import android.opengl.GLES20
import android.opengl.Matrix
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.view.Surface
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Video for Android 4.4 (no Camera2): the old Camera API previews into a SurfaceTexture, and each frame is
 * drawn with OpenGL onto the H.264 encoder's input surface (and the on-screen preview, if attached).
 * Going through the GPU avoids per-phone color-format differences. Output goes into [ring] exactly like
 * [VideoEngine], so clips, muxing and uploads are unchanged.
 */
@Suppress("DEPRECATION")
class LegacyVideoEngine(private val context: Context, private val ring: EncodedRing) : VideoSource {
    private val thread = HandlerThread("legacy-camera").apply { start() }
    private val handler = Handler(thread.looper)
    private var camera: Camera? = null
    private var encoder: MediaCodec? = null
    private var drainThread: Thread? = null
    @Volatile private var running = false
    @Volatile private var ptsOffsetUs = Long.MIN_VALUE
    private var width = 640
    private var height = 480
    @Volatile private var sensorOrientation = 0
    @Volatile private var frontFacing = false

    // GL state, only touched on [thread].
    private var eglDisplay: EGLDisplay = EGL14.EGL_NO_DISPLAY
    private var eglContext: EGLContext = EGL14.EGL_NO_CONTEXT
    private var eglConfig: EGLConfig? = null
    private var encSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var prevSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var pendingPreview: Surface? = null
    private var texture: SurfaceTexture? = null
    private var program = 0
    private var texId = 0
    private val texMatrix = FloatArray(16)
    private val identity = FloatArray(16).also { Matrix.setIdentityM(it, 0) }
    private var lastDrawNs = 0L
    private val previewMvp = FloatArray(16).also { Matrix.setIdentityM(it, 0) }
    private var frames = 0

    override val rotationDegrees: Int
        get() {
            val p = Prefs(context)
            val display = p.displayRotation.takeIf { it >= 0 } ?: when (
                (context.getSystemService(Context.WINDOW_SERVICE) as android.view.WindowManager).defaultDisplay.rotation) {
                Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0
            }
            val auto = if (frontFacing) (sensorOrientation + display) % 360 else (sensorOrientation - display + 360) % 360
            return (auto + p.videoRotationExtra) % 360
        }

    override fun start() {
        if (running) return
        running = true
        handler.post {
            try {
                openCamera()
                startEncoder()
                setupGl()
                val st = SurfaceTexture(texId)
                st.setOnFrameAvailableListener { handler.post { drawFrame() } }
                texture = st
                camera!!.setPreviewTexture(st)
                camera!!.startPreview()
                Status.cameraText = "On · ${width}×${height}"
            } catch (e: Exception) {
                Log.e(TAG, "legacy camera start failed", e)
                Status.cameraText = "Camera failed: ${e.message}"
                releaseAll()
            }
        }
    }

    override fun quit() {
        running = false
        drainThread?.join(3000)
        drainThread = null
        val done = CountDownLatch(1)
        handler.post { releaseAll(); done.countDown() }
        done.await(3, TimeUnit.SECONDS)
        thread.quitSafely()
        ring.clear()
        ptsOffsetUs = Long.MIN_VALUE
        Status.cameraText = "Off"
    }

    override fun setPreview(surface: Surface?) {
        handler.post {
            pendingPreview = surface
            if (prevSurface != EGL14.EGL_NO_SURFACE) {
                EGL14.eglDestroySurface(eglDisplay, prevSurface); prevSurface = EGL14.EGL_NO_SURFACE
            }
            attachPreview()
        }
    }

    // ---- Camera and encoder ------------------------------------------------------------------

    private fun openCamera() {
        val info = Camera.CameraInfo()
        var id = 0
        for (i in 0 until Camera.getNumberOfCameras()) {
            Camera.getCameraInfo(i, info)
            if (info.facing == Camera.CameraInfo.CAMERA_FACING_BACK) { id = i; break }
        }
        Camera.getCameraInfo(id, info)
        sensorOrientation = info.orientation
        frontFacing = info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT
        val cam = Camera.open(id)
        camera = cam
        val p = cam.parameters
        val sizes = p.supportedPreviewSizes
        val ok = sizes.filter { it.width in 600..1280 && it.height <= 720 }
        val s = (ok.ifEmpty { sizes }).minByOrNull { kotlin.math.abs(it.width - 640) }!!
        width = s.width; height = s.height
        p.setPreviewSize(width, height)
        if (Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO in p.supportedFocusModes) {
            p.focusMode = Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO
        }
        cam.parameters = p
        try {   // optional: hint video use, keep the frame rate modest to save CPU on old phones
            val q = cam.parameters
            q.setRecordingHint(true)
            q.supportedPreviewFpsRange?.filter { it[1] <= 15000 }?.maxByOrNull { it[1] }?.let { q.setPreviewFpsRange(it[0], it[1]) }
            cam.parameters = q
        } catch (e: Exception) { Log.w(TAG, "optional camera settings rejected", e) }
    }

    private lateinit var encoderInput: Surface

    private fun startEncoder() {
        val fmt = MediaFormat.createVideoFormat("video/avc", width, height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, 800_000)
            setInteger(MediaFormat.KEY_FRAME_RATE, 15)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        }
        val enc = MediaCodec.createEncoderByType("video/avc")
        enc.configure(fmt, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        encoderInput = enc.createInputSurface()
        enc.start()
        encoder = enc
        drainThread = Thread({ drainLoop(enc) }, "legacy-video-drain").apply { start() }
    }

    private fun drainLoop(enc: MediaCodec) {
        val info = MediaCodec.BufferInfo()
        while (running) {
            val idx = try { enc.dequeueOutputBuffer(info, 50_000) } catch (e: Exception) { break }
            when {
                idx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> ring.setFormat(enc.outputFormat)
                idx >= 0 -> {
                    if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                        if (ptsOffsetUs == Long.MIN_VALUE) ptsOffsetUs = System.nanoTime() / 1000 - info.presentationTimeUs
                        ring.add(enc.getOutputBufferCompat(idx), info, info.presentationTimeUs + ptsOffsetUs)
                    }
                    enc.releaseOutputBuffer(idx, false)
                }
            }
        }
    }

    // ---- OpenGL ------------------------------------------------------------------------------

    private fun setupGl() {
        eglDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
        val v = IntArray(2)
        check(EGL14.eglInitialize(eglDisplay, v, 0, v, 1)) { "eglInitialize failed" }
        val attrs = intArrayOf(
            EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8, EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
            EGL_RECORDABLE_ANDROID, 1, EGL14.EGL_NONE)
        val configs = arrayOfNulls<EGLConfig>(1); val n = IntArray(1)
        check(EGL14.eglChooseConfig(eglDisplay, attrs, 0, configs, 0, 1, n, 0) && n[0] > 0) { "no EGL config" }
        eglConfig = configs[0]
        eglContext = EGL14.eglCreateContext(eglDisplay, eglConfig, EGL14.EGL_NO_CONTEXT,
            intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0)
        encSurface = EGL14.eglCreateWindowSurface(eglDisplay, eglConfig, encoderInput, intArrayOf(EGL14.EGL_NONE), 0)
        check(EGL14.eglMakeCurrent(eglDisplay, encSurface, encSurface, eglContext)) { "eglMakeCurrent failed" }

        program = buildProgram()
        val t = IntArray(1)
        GLES20.glGenTextures(1, t, 0)
        texId = t[0]
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, texId)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
        attachPreview()
    }

    private fun attachPreview() {
        val s = pendingPreview ?: return
        if (eglContext == EGL14.EGL_NO_CONTEXT || prevSurface != EGL14.EGL_NO_SURFACE) return
        prevSurface = try {
            EGL14.eglCreateWindowSurface(eglDisplay, eglConfig, s, intArrayOf(EGL14.EGL_NONE), 0)
        } catch (e: Exception) { Log.w(TAG, "preview surface failed", e); EGL14.EGL_NO_SURFACE }
    }

    private fun drawFrame() {
        val st = texture ?: return
        if (!running) return
        EGL14.eglMakeCurrent(eglDisplay, encSurface, encSurface, eglContext)
        st.updateTexImage()
        val ts = st.timestamp
        if (ts - lastDrawNs < 60_000_000L) return   // keep about 15 fps whatever the camera delivers
        lastDrawNs = ts
        st.getTransformMatrix(texMatrix)

        GLES20.glViewport(0, 0, width, height)
        draw(identity)
        EGLExt.eglPresentationTimeANDROID(eglDisplay, encSurface, ts)
        EGL14.eglSwapBuffers(eglDisplay, encSurface)

        if (prevSurface != EGL14.EGL_NO_SURFACE &&
            EGL14.eglMakeCurrent(eglDisplay, prevSurface, prevSurface, eglContext)) {
            val w = IntArray(1); val h = IntArray(1)
            EGL14.eglQuerySurface(eglDisplay, prevSurface, EGL14.EGL_WIDTH, w, 0)
            EGL14.eglQuerySurface(eglDisplay, prevSurface, EGL14.EGL_HEIGHT, h, 0)
            GLES20.glViewport(0, 0, w[0], h[0])
            // Turn the preview the same way the saved video is turned for playback (clockwise degrees).
            if (++frames % 30 == 1) Matrix.setRotateM(previewMvp, 0, -rotationDegrees.toFloat(), 0f, 0f, 1f)
            draw(previewMvp)
            EGL14.eglSwapBuffers(eglDisplay, prevSurface)
        }
    }

    private val quad: FloatBuffer = floatBuffer(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f)
    private val uv: FloatBuffer = floatBuffer(0f, 0f, 1f, 0f, 0f, 1f, 1f, 1f)

    private fun draw(mvp: FloatArray) {
        GLES20.glUseProgram(program)
        val aPos = GLES20.glGetAttribLocation(program, "aPos")
        val aTex = GLES20.glGetAttribLocation(program, "aTex")
        GLES20.glEnableVertexAttribArray(aPos)
        GLES20.glVertexAttribPointer(aPos, 2, GLES20.GL_FLOAT, false, 0, quad)
        GLES20.glEnableVertexAttribArray(aTex)
        GLES20.glVertexAttribPointer(aTex, 2, GLES20.GL_FLOAT, false, 0, uv)
        GLES20.glUniformMatrix4fv(GLES20.glGetUniformLocation(program, "uMvp"), 1, false, mvp, 0)
        GLES20.glUniformMatrix4fv(GLES20.glGetUniformLocation(program, "uTex"), 1, false, texMatrix, 0)
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, texId)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    }

    private fun buildProgram(): Int {
        fun shader(type: Int, src: String): Int {
            val s = GLES20.glCreateShader(type)
            GLES20.glShaderSource(s, src); GLES20.glCompileShader(s)
            val ok = IntArray(1); GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0)
            check(ok[0] != 0) { "shader: " + GLES20.glGetShaderInfoLog(s) }
            return s
        }
        val p = GLES20.glCreateProgram()
        GLES20.glAttachShader(p, shader(GLES20.GL_VERTEX_SHADER, """
            attribute vec4 aPos; attribute vec4 aTex; uniform mat4 uMvp; uniform mat4 uTex; varying vec2 vTex;
            void main() { gl_Position = uMvp * aPos; vTex = (uTex * aTex).xy; }"""))
        GLES20.glAttachShader(p, shader(GLES20.GL_FRAGMENT_SHADER, """
            #extension GL_OES_EGL_image_external : require
            precision mediump float; varying vec2 vTex; uniform samplerExternalOES sTex;
            void main() { gl_FragColor = texture2D(sTex, vTex); }"""))
        GLES20.glLinkProgram(p)
        return p
    }

    private fun releaseAll() {
        try { camera?.stopPreview() } catch (_: Exception) {}
        try { camera?.release() } catch (_: Exception) {}
        camera = null
        texture?.release(); texture = null
        if (eglDisplay != EGL14.EGL_NO_DISPLAY) {
            EGL14.eglMakeCurrent(eglDisplay, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
            if (prevSurface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(eglDisplay, prevSurface)
            if (encSurface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(eglDisplay, encSurface)
            if (eglContext != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(eglDisplay, eglContext)
            EGL14.eglTerminate(eglDisplay)
        }
        prevSurface = EGL14.EGL_NO_SURFACE; encSurface = EGL14.EGL_NO_SURFACE
        eglContext = EGL14.EGL_NO_CONTEXT; eglDisplay = EGL14.EGL_NO_DISPLAY
        try { encoder?.stop() } catch (_: Exception) {}
        try { encoder?.release() } catch (_: Exception) {}
        encoder = null
        if (::encoderInput.isInitialized) encoderInput.release()
    }

    companion object {
        private const val TAG = "LegacyVideoEngine"
        private const val EGL_RECORDABLE_ANDROID = 0x3142
        private fun floatBuffer(vararg f: Float): FloatBuffer =
            ByteBuffer.allocateDirect(f.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply { put(f); position(0) }
    }
}
