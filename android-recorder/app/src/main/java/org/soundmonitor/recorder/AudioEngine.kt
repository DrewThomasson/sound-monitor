package org.soundmonitor.recorder

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaRecorder
import android.util.Log
import kotlin.math.PI
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Reads the microphone continuously. Every 100 ms chunk is:
 *  - measured (level in dB, same formula as the original desktop app: 20*log10(RMS of 16-bit samples)),
 *  - passed to [onChunk] for event detection and the per-second level log,
 *  - encoded to AAC into [ring] so clips can include audio from before an event started.
 */
class AudioEngine(
    private val ring: EncodedRing,
    private val calibrationDb: () -> Float,
    private val onChunk: (Chunk) -> Unit,
) {
    class Chunk(val ptsUs: Long, val levelDb: Float, val energy: Double, val lowEnergy: Double)

    private val rate = 44100
    private val chunkSamples = rate / 10
    @Volatile private var running = false
    private var thread: Thread? = null

    fun start() {
        if (running) return
        running = true
        thread = Thread({ loop() }, "audio").apply { priority = Thread.MAX_PRIORITY; start() }
    }

    fun stop() {
        running = false
        thread?.join(3000)
        thread = null
    }

    private fun loop() {
        val minBuf = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        // VOICE_RECOGNITION turns off automatic gain control on most devices, which keeps levels comparable.
        val rec = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION, rate, AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT, max(minBuf, chunkSamples * 2 * 4)
        )
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            Status.warning = "Microphone unavailable"
            Log.e(TAG, "AudioRecord failed to initialize")
            running = false
            return
        }
        val fmt = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, rate, 1).apply {
            setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
            setInteger(MediaFormat.KEY_BIT_RATE, 96_000)
            setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, chunkSamples * 2)
        }
        val enc = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        enc.configure(fmt, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        enc.start()

        val pcm = ShortArray(chunkSamples)
        val bytes = ByteArray(chunkSamples * 2)
        val info = MediaCodec.BufferInfo()
        // Low-pass filter (~150 Hz) used to measure how much energy is low rumble (engines, wind).
        val alpha = (2 * PI * 150 / rate).let { it / (it + 1) }
        var lp = 0.0
        var samplesRead = 0L
        rec.startRecording()
        val baseUs = System.nanoTime() / 1000

        try {
            while (running) {
                var got = 0
                while (got < chunkSamples && running) {
                    val n = rec.read(pcm, got, chunkSamples - got)
                    if (n <= 0) { Thread.sleep(5); continue }
                    got += n
                }
                if (!running) break
                val ptsUs = baseUs + samplesRead * 1_000_000L / rate
                samplesRead += got

                var sum = 0.0
                var low = 0.0
                for (i in 0 until got) {
                    val s = pcm[i].toDouble()
                    sum += s * s
                    lp += alpha * (s - lp)
                    low += lp * lp
                    bytes[2 * i] = (pcm[i].toInt() and 0xff).toByte()
                    bytes[2 * i + 1] = (pcm[i].toInt() shr 8).toByte()
                }
                val rms = sqrt(sum / got)
                val db = (if (rms < 1) 0.0 else 20 * log10(rms)).toFloat() + calibrationDb()
                onChunk(Chunk(ptsUs, db, sum, low))

                val inIdx = enc.dequeueInputBuffer(10_000)
                if (inIdx >= 0) {
                    val ib = enc.getInputBufferCompat(inIdx)
                    ib.clear()
                    ib.put(bytes, 0, got * 2)
                    enc.queueInputBuffer(inIdx, 0, got * 2, ptsUs, 0)
                }
                drain(enc, info)
            }
        } catch (e: Exception) {
            Log.e(TAG, "audio loop failed", e)
            Status.warning = "Audio error: ${e.message}"
        } finally {
            try { rec.stop() } catch (_: Exception) {}
            rec.release()
            try { enc.stop() } catch (_: Exception) {}
            enc.release()
        }
    }

    private fun drain(enc: MediaCodec, info: MediaCodec.BufferInfo) {
        while (true) {
            val idx = enc.dequeueOutputBuffer(info, 0)
            when {
                idx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> ring.setFormat(enc.outputFormat)
                idx >= 0 -> {
                    ring.add(enc.getOutputBufferCompat(idx), info, info.presentationTimeUs)
                    enc.releaseOutputBuffer(idx, false)
                }
                else -> return
            }
        }
    }

    companion object { private const val TAG = "AudioEngine" }
}

@Suppress("DEPRECATION")
fun MediaCodec.getInputBufferCompat(i: Int): java.nio.ByteBuffer =
    if (android.os.Build.VERSION.SDK_INT >= 21) getInputBuffer(i)!! else inputBuffers[i]

@Suppress("DEPRECATION")
fun MediaCodec.getOutputBufferCompat(i: Int): java.nio.ByteBuffer =
    if (android.os.Build.VERSION.SDK_INT >= 21) getOutputBuffer(i)!! else outputBuffers[i]
