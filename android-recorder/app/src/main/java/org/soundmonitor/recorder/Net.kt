package org.soundmonitor.recorder

import android.os.Build
import android.util.Log
import org.conscrypt.Conscrypt
import java.net.HttpURLConnection
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory

/**
 * Opens connections that work on Android 4.4 too. Android 4.4 lacks the AES-GCM cipher suites Hugging Face
 * requires, so below Android 5 connections use the bundled Conscrypt TLS stack instead of the system one.
 */
object Net {
    private val modern: SSLSocketFactory? by lazy {
        if (Build.VERSION.SDK_INT >= 21) null
        else try {
            SSLContext.getInstance("TLS", Conscrypt.newProvider()).apply { init(null, null, null) }.socketFactory
        } catch (e: Throwable) { Log.w("Net", "Conscrypt unavailable", e); null }
    }

    fun open(url: String): HttpURLConnection {
        val c = URL(url).openConnection() as HttpURLConnection
        val f = modern
        if (f != null && c is HttpsURLConnection) c.sslSocketFactory = f
        return c
    }
}
