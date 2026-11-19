package org.soundmonitor.recorder

import android.media.MediaCodec
import android.media.MediaFormat
import java.nio.ByteBuffer

/** One encoded audio or video frame, with its time on the shared clock (microseconds). */
class Sample(val ptsUs: Long, val flags: Int, val data: ByteArray) {
    val isKey: Boolean get() = flags and MediaCodec.BUFFER_FLAG_KEY_FRAME != 0
}

/**
 * Keeps the last [keepUs] of encoded frames from one encoder, so a clip can include the
 * seconds before an event was detected.
 */
class EncodedRing(private val keepUs: Long) {
    private val samples = ArrayDeque<Sample>()
    @Volatile var format: MediaFormat? = null
        private set

    fun setFormat(f: MediaFormat) { format = f }

    @Synchronized fun add(buf: ByteBuffer, info: MediaCodec.BufferInfo, ptsUs: Long) {
        if (info.size <= 0 || info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) return
        val bytes = ByteArray(info.size)
        buf.position(info.offset)
        buf.limit(info.offset + info.size)
        buf.get(bytes)
        samples.addLast(Sample(ptsUs, info.flags, bytes))
        while (samples.isNotEmpty() && ptsUs - samples.first().ptsUs > keepUs) samples.removeFirst()
    }

    @Synchronized fun latestUs(): Long = samples.lastOrNull()?.ptsUs ?: Long.MIN_VALUE

    /**
     * Frames from [fromUs] to [toUs]. With [startOnKey], starts at the last keyframe at or
     * before [fromUs] so the video decodes from its first frame.
     */
    @Synchronized fun slice(fromUs: Long, toUs: Long, startOnKey: Boolean): List<Sample> {
        val list = samples.toList()
        var start = list.indexOfFirst { it.ptsUs >= fromUs }
        if (start < 0) return emptyList()
        if (startOnKey) {
            var k = start
            while (k > 0 && !list[k].isKey) k--
            if (!list[k].isKey) {
                k = list.indexOfFirst { it.ptsUs >= fromUs && it.isKey }
                if (k < 0) return emptyList()
            }
            start = k
        }
        return list.subList(start, list.size).takeWhile { it.ptsUs <= toUs }
    }

    @Synchronized fun clear() { samples.clear() }
}
