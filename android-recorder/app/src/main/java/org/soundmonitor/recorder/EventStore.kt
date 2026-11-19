package org.soundmonitor.recorder

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Local log of events, in the same shape as the desktop app's `events` table plus a few columns
 * for the new site. Rows are copied into a CSV with each upload and marked uploaded.
 */
class EventStore(context: Context) : SQLiteOpenHelper(context, "events.db", null, 1) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, duration REAL, peak_db REAL, avg_db REAL, background_db REAL,
                filename TEXT, video_filename TEXT, low_frequency INTEGER, wind_suspected INTEGER,
                site TEXT, calibration_db REAL, uploaded INTEGER DEFAULT 0)"""
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {}

    fun insert(v: ContentValues): Long = writableDatabase.insert("events", null, v)

    class Row(val id: Long, val values: List<String>)

    val csvColumns = listOf(
        "timestamp", "duration", "peak_db", "avg_db", "background_db", "filename", "video_filename",
        "low_frequency", "wind_suspected", "site", "calibration_db"
    )

    fun pending(): List<Row> {
        val out = ArrayList<Row>()
        readableDatabase.rawQuery(
            "SELECT id, ${csvColumns.joinToString()} FROM events WHERE uploaded = 0 ORDER BY id", null
        ).use { c ->
            while (c.moveToNext()) out += Row(c.getLong(0), (1..csvColumns.size).map { c.getString(it) ?: "" })
        }
        return out
    }

    fun markUploaded(ids: List<Long>) {
        if (ids.isEmpty()) return
        val db = writableDatabase
        db.beginTransaction()
        try {
            ids.chunked(500).forEach { chunk ->
                db.execSQL("UPDATE events SET uploaded = 1 WHERE id IN (${chunk.joinToString()})")
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    fun countSince(timestampPrefix: String): Int =
        readableDatabase.rawQuery("SELECT COUNT(*) FROM events WHERE timestamp >= ?", arrayOf(timestampPrefix)).use {
            it.moveToFirst(); it.getInt(0)
        }
}
