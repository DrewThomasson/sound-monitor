package org.soundmonitor.recorder

import android.media.MediaCodec
import android.media.MediaMuxer
import android.util.Log
import java.io.File
import java.nio.ByteBuffer

/** Writes MP4 / M4A files from encoded frames taken out of the rings. */
object ClipWriter {
    private const val TAG = "ClipWriter"

    /**
     * Writes [audio] (and [video], if given) to [out] via a temporary file, so the uploader never
     * sees a half-written clip. Times are shifted so the file starts at 0.
     * Returns false if there was nothing usable to write.
     */
    fun write(out: File, audio: List<Sample>, audioRing: EncodedRing, video: List<Sample>?, videoRing: EncodedRing?,
              rotationDegrees: Int = 0): Boolean {
        val aFmt = audioRing.format
        val vFmt = videoRing?.format
        val useVideo = video != null && video.isNotEmpty() && vFmt != null
        if ((audio.isEmpty() || aFmt == null) && !useVideo) return false
        out.parentFile?.mkdirs()
        val tmp = File(out.path + ".tmp")
        var muxer: MediaMuxer? = null
        try {
            val m = MediaMuxer(tmp.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            muxer = m
            if (useVideo && rotationDegrees != 0) m.setOrientationHint(rotationDegrees)
            val vTrack = if (useVideo) m.addTrack(vFmt!!) else -1
            val aTrack = if (audio.isNotEmpty() && aFmt != null) m.addTrack(aFmt) else -1
            m.start()
            val t0 = listOfNotNull(
                if (useVideo) video!!.first().ptsUs else null,
                if (aTrack >= 0) audio.first().ptsUs else null,
            ).min()
            val info = MediaCodec.BufferInfo()
            fun put(track: Int, s: Sample) {
                info.set(0, s.data.size, s.ptsUs - t0, s.flags and MediaCodec.BUFFER_FLAG_KEY_FRAME)
                m.writeSampleData(track, ByteBuffer.wrap(s.data), info)
            }
            // Interleave by time, which some players need for smooth playback.
            val a = if (aTrack >= 0) audio else emptyList()
            val v = if (useVideo) video!! else emptyList()
            var i = 0; var j = 0
            while (i < a.size || j < v.size) {
                if (j >= v.size || (i < a.size && a[i].ptsUs <= v[j].ptsUs)) put(aTrack, a[i++]) else put(vTrack, v[j++])
            }
            m.stop()
            m.release(); muxer = null
            return tmp.renameTo(out)
        } catch (e: Exception) {
            Log.e(TAG, "writing ${out.name} failed", e)
            try { muxer?.release() } catch (_: Exception) {}
            tmp.delete()
            return false
        }
    }
}
