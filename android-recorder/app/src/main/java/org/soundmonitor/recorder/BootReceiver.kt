package org.soundmonitor.recorder

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings

/**
 * After a reboot (e.g. a power cut), reopen the app so recording resumes. Android only allows
 * the microphone and camera when recording is started from a visible screen, so this opens the
 * status screen (which starts recording) if allowed, and otherwise posts a "tap to resume" notification.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (!Prefs(context).autoStart) return
        val open = Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val canOpen = Build.VERSION.SDK_INT < 29 || Settings.canDrawOverlays(context)
        if (canOpen) {
            try { context.startActivity(open); return } catch (_: Exception) {}
        }
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(NotificationChannel("restart", "Restart", NotificationManager.IMPORTANCE_HIGH))
        }
        val pi = PendingIntent.getActivity(context, 1, open,
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0))
        @Suppress("DEPRECATION")
        val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(context, "restart") else Notification.Builder(context)
        nm.notify(2, b.setContentTitle("Recording stopped after restart")
            .setContentText("Tap to resume recording")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pi).setAutoCancel(true).build())
    }
}
