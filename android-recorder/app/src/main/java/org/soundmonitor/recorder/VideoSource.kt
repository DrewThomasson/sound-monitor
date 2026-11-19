package org.soundmonitor.recorder

import android.view.Surface

/** A camera feeding encoded H.264 into an [EncodedRing]: Camera2 on Android 5+, the old Camera API below. */
interface VideoSource {
    val rotationDegrees: Int
    fun start()
    fun quit()
    fun setPreview(surface: Surface?)
}
