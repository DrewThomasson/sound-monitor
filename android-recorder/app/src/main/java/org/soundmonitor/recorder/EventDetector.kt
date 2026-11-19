package org.soundmonitor.recorder

import kotlin.math.log10
import kotlin.math.max

/**
 * Finds loud events relative to the street's normal background level.
 *
 * Background = median of the 1-second levels over the last 10 minutes, so the trigger adapts to the
 * spot (5th floor vs street level) and to time of day. An event starts when a 100 ms chunk reaches
 * background + margin, and ends after [postUs] below that (minus 3 dB of hysteresis) or at [maxUs].
 */
class EventDetector(
    private val marginDb: () -> Float,
    private val onEvent: (Event) -> Unit,
) {
    class Event(
        val startUs: Long, val endUs: Long, val peakDb: Float, val avgDb: Float,
        val backgroundDb: Float, val lowRatio: Float,
    ) {
        val durationS: Double get() = (endUs - startUs) / 1e6
        /** Energy mostly below ~150 Hz: engine rumble or traffic. */
        val lowFrequency: Boolean get() = lowRatio > 0.4f
        /** Almost all energy below ~150 Hz with nothing above it is typical of wind on the mic. */
        val windSuspected: Boolean get() = lowRatio > 0.9f
    }

    private val postUs = 2_000_000L
    private val maxUs = 60_000_000L
    private val warmupSeconds = 30

    private val secondLevels = ArrayDeque<Float>()
    private var secEnergy = 0.0
    private var secChunks = 0
    private var background = Float.NaN
    private var secondsSinceRecalc = 0

    private var inEvent = false
    private var evStart = 0L
    private var evPeak = 0f
    private var evEnergy = 0.0
    private var evLow = 0.0
    private var evChunks = 0
    private var quietSince = -1L
    private var evBackground = 0f

    /** Called with each second's average level, for the level log. */
    var onSecond: ((Long, Float, Float) -> Unit)? = null
    private var secMax = 0f
    private var calOffsetForSecond = 0f

    fun onChunk(c: AudioEngine.Chunk, calibrationDb: Float) {
        Status.levelDb = c.levelDb
        // 1-second level (energy average), used for the background estimate and the level log.
        secEnergy += c.energy
        secChunks++
        secMax = max(secMax, c.levelDb)
        calOffsetForSecond = calibrationDb
        if (secChunks == 10) {
            val meanSq = secEnergy / (secChunks * 4410)
            val secDb = (if (meanSq < 1) 0.0 else 10 * log10(meanSq)).toFloat() + calibrationDb
            onSecond?.invoke(c.ptsUs, secDb, secMax)
            if (!inEvent) {
                secondLevels.addLast(secDb)
                if (secondLevels.size > 600) secondLevels.removeFirst()
            }
            secEnergy = 0.0; secChunks = 0; secMax = 0f
            if (++secondsSinceRecalc >= 10 && secondLevels.size >= warmupSeconds) {
                background = secondLevels.sorted()[secondLevels.size / 2]
                secondsSinceRecalc = 0
            }
        }
        if (background.isNaN()) {
            Status.backgroundDb = Float.NaN
            Status.thresholdDb = Float.NaN
            return
        }
        val threshold = background + marginDb()
        Status.backgroundDb = background
        Status.thresholdDb = threshold

        if (!inEvent) {
            if (c.levelDb >= threshold) {
                inEvent = true
                Status.inEvent = true
                evStart = c.ptsUs
                evPeak = c.levelDb
                evEnergy = c.energy; evLow = c.lowEnergy; evChunks = 1
                quietSince = -1L
                evBackground = background
            }
            return
        }
        evPeak = max(evPeak, c.levelDb)
        evEnergy += c.energy; evLow += c.lowEnergy; evChunks++
        if (c.levelDb < threshold - 3f) {
            if (quietSince < 0) quietSince = c.ptsUs
        } else {
            quietSince = -1L
        }
        val end = (quietSince >= 0 && c.ptsUs - quietSince >= postUs) || c.ptsUs - evStart >= maxUs
        if (end) {
            inEvent = false
            Status.inEvent = false
            val meanSq = evEnergy / (evChunks * 4410)
            val avg = (if (meanSq < 1) 0.0 else 10 * log10(meanSq)).toFloat() + calibrationDb
            val lowRatio = if (evEnergy > 0) (evLow / evEnergy).toFloat() else 0f
            onEvent(Event(evStart, c.ptsUs + 100_000, evPeak, avg, evBackground, lowRatio))
        }
    }
}
