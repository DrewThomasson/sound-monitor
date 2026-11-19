package org.soundmonitor.recorder

/** Live state shared between the recording service and the screens. */
object Status {
    @Volatile var running = false
    @Volatile var startedAtMs = 0L
    @Volatile var levelDb = 0f
    @Volatile var backgroundDb = Float.NaN
    @Volatile var thresholdDb = Float.NaN
    @Volatile var inEvent = false
    @Volatile var eventsToday = 0
    @Volatile var eventsTodayDate = ""
    @Volatile var lastEventText = "None yet"
    @Volatile var cameraText = "Off"
    @Volatile var uploadText = ""
    @Volatile var uploading = false
    @Volatile var warning = ""
    @Volatile var pendingBytes = 0L
    @Volatile var freeBytes = 0L
    @Volatile var batteryText = ""
}
