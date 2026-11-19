package org.soundmonitor.recorder

import android.util.Base64
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Minimal Hugging Face Hub client: uploads files to a dataset repo in one commit, using the same
 * HTTP API as the official huggingface_hub library (preupload check, LFS upload for binary files,
 * then a commit). No Google services or extra libraries needed.
 */
class HfUploader(private val repo: String, private val token: String) {
    private val hub = "https://huggingface.co"

    class HubException(msg: String) : Exception(msg)

    /** Returns the account name the token belongs to, and whether it can write. */
    fun whoami(): Pair<String, Boolean> {
        val r = request("GET", "$hub/api/whoami-v2", null, "application/json")
        val j = JSONObject(r)
        val name = j.optString("name")
        val access = j.optJSONObject("auth")?.optJSONObject("accessToken")
        val role = access?.optString("role") ?: ""
        return name to (role == "write" || role == "fineGrained")
    }

    /** Upload [files] (local file -> path in repo) as one commit. */
    fun commit(files: List<Pair<File, String>>, summary: String) {
        if (files.isEmpty()) return
        // 1. Ask the Hub which files must go through LFS (binary/large) and which can be inline.
        val pre = JSONArray()
        val hashes = HashMap<String, String>()
        for ((f, path) in files) {
            pre.put(JSONObject().put("path", path).put("size", f.length()).put("sample", sampleB64(f)))
        }
        val preResp = JSONObject(request("POST", "$hub/api/datasets/$repo/preupload/main",
            JSONObject().put("files", pre).toString(), "application/json"))
        val modes = HashMap<String, String>()
        val arr = preResp.getJSONArray("files")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            modes[o.getString("path")] = o.optString("uploadMode", "lfs")
        }

        // 2. Upload LFS files (skips any the Hub already has).
        val lfs = files.filter { modes[it.second] != "regular" }
        for (f in lfs) hashes[f.second] = sha256(f.first)
        for (batch in lfs.chunked(100)) uploadLfs(batch, hashes)

        // 3. Commit: inline content for small text files, LFS pointers for the rest.
        val sb = StringBuilder()
        sb.append(JSONObject().put("key", "header").put("value",
            JSONObject().put("summary", summary).put("description", "")).toString()).append('\n')
        for ((f, path) in files) {
            val line = if (modes[path] == "regular") {
                JSONObject().put("key", "file").put("value", JSONObject()
                    .put("content", Base64.encodeToString(f.readBytes(), Base64.NO_WRAP))
                    .put("path", path).put("encoding", "base64"))
            } else {
                JSONObject().put("key", "lfsFile").put("value", JSONObject()
                    .put("path", path).put("algo", "sha256").put("oid", hashes[path]).put("size", f.length()))
            }
            sb.append(line.toString()).append('\n')
        }
        request("POST", "$hub/api/datasets/$repo/commit/main", sb.toString(), "application/x-ndjson")
    }

    private fun uploadLfs(batch: List<Pair<File, String>>, hashes: Map<String, String>) {
        val objs = JSONArray()
        batch.forEach { (f, p) -> objs.put(JSONObject().put("oid", hashes[p]).put("size", f.length())) }
        val body = JSONObject()
            .put("operation", "upload")
            .put("transfers", JSONArray().put("basic").put("multipart"))
            .put("objects", objs)
            .put("hash_algo", "sha256")
            .put("ref", JSONObject().put("name", "main"))
        val resp = JSONObject(request("POST", "$hub/datasets/$repo.git/info/lfs/objects/batch",
            body.toString(), "application/vnd.git-lfs+json", accept = "application/vnd.git-lfs+json"))
        val byOid = batch.associateBy { hashes[it.second] }
        val out = resp.getJSONArray("objects")
        for (i in 0 until out.length()) {
            val o = out.getJSONObject(i)
            o.optJSONObject("error")?.let { throw HubException("LFS error: ${it.optString("message")}") }
            val actions = o.optJSONObject("actions") ?: continue   // already on the Hub
            val file = byOid[o.getString("oid")]?.first ?: continue
            val up = actions.optJSONObject("upload")
            if (up != null) {
                val hdr = up.optJSONObject("header")
                if (hdr != null && hdr.has("chunk_size")) throw HubException("File too large for basic upload: ${file.name}")
                putFile(up.getString("href"), file, hdr)
            }
            actions.optJSONObject("verify")?.let { v ->
                request("POST", v.getString("href"),
                    JSONObject().put("oid", o.getString("oid")).put("size", o.getLong("size")).toString(),
                    "application/vnd.git-lfs+json", extraHeaders = v.optJSONObject("header"))
            }
        }
    }

    private fun putFile(href: String, f: File, headers: JSONObject?) {
        val c = Net.open(href)
        try {
            c.requestMethod = "PUT"
            c.doOutput = true
            c.connectTimeout = 30_000
            c.readTimeout = 120_000
            c.setFixedLengthStreamingMode(f.length())
            headers?.keys()?.forEach { k -> c.setRequestProperty(k, headers.getString(k)) }
            c.outputStream.use { os -> FileInputStream(f).use { it.copyTo(os) } }
            val code = c.responseCode
            if (code !in 200..299) throw HubException("LFS upload of ${f.name} failed: HTTP $code ${readErr(c)}")
        } finally { c.disconnect() }
    }

    private fun request(
        method: String, url: String, body: String?, contentType: String,
        accept: String = "application/json", extraHeaders: JSONObject? = null,
    ): String {
        val c = Net.open(url)
        try {
            c.requestMethod = method
            c.connectTimeout = 30_000
            c.readTimeout = 120_000
            c.setRequestProperty("Authorization", "Bearer $token")
            c.setRequestProperty("Accept", accept)
            c.setRequestProperty("User-Agent", "street-noise-recorder/${BuildInfo.VERSION}")
            extraHeaders?.keys()?.forEach { k -> c.setRequestProperty(k, extraHeaders.getString(k)) }
            if (body != null) {
                val bytes = body.toByteArray()
                c.doOutput = true
                c.setRequestProperty("Content-Type", contentType)
                c.setFixedLengthStreamingMode(bytes.size)
                c.outputStream.use { it.write(bytes) }
            }
            val code = c.responseCode
            if (code !in 200..299) throw HubException("HTTP $code from ${URL(url).path}: ${readErr(c)}")
            return c.inputStream.bufferedReader().use { it.readText() }
        } finally { c.disconnect() }
    }

    private fun readErr(c: HttpURLConnection): String =
        try { c.errorStream?.bufferedReader()?.use { it.readText() }?.take(300) ?: "" } catch (_: Exception) { "" }

    private fun sampleB64(f: File): String {
        val buf = ByteArray(512)
        val n = FileInputStream(f).use { it.read(buf) }.coerceAtLeast(0)
        return Base64.encodeToString(buf, 0, n, Base64.NO_WRAP)
    }

    private fun sha256(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        FileInputStream(f).use { ins ->
            val buf = ByteArray(64 * 1024)
            while (true) { val n = ins.read(buf); if (n <= 0) break; md.update(buf, 0, n) }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    companion object { const val TAG = "HfUploader" }
}

/** Collects finished files from the outbox and uploads them in commits of a manageable size. */
class UploadJob(private val outbox: File, private val prefs: Prefs, private val store: EventStore) {

    fun run(): String {
        val token = prefs.token.trim()
        if (token.isEmpty()) throw HfUploader.HubException("No Hugging Face token set")
        if (prefs.repo.isBlank()) throw HfUploader.HubException("No Hugging Face dataset set")
        val up = HfUploader(prefs.repo.trim(), token)
        val site = prefs.siteSlug

        // Event list for this upload (only events whose clip files are finished).
        val rows = store.pending()
        val stamp = java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.US).format(java.util.Date())
        if (rows.isNotEmpty()) {
            val csv = File(outbox, "sites/$site/events/events_$stamp.csv")
            csv.parentFile?.mkdirs()
            csv.writeText(buildString {
                append(store.csvColumns.joinToString(",")).append('\n')
                rows.forEach { r -> append(r.values.joinToString(",") { csvEscape(it) }).append('\n') }
            })
        }
        writeStatus(File(outbox, "sites/$site/status.json"))

        val files = outbox.walkTopDown().filter {
            it.isFile && !it.name.endsWith(".tmp") && !it.name.endsWith(".part")
        }.toList().sortedBy { it.path }
        if (files.isEmpty()) return "Nothing to upload"

        // Hugging Face suggests 50-100 files per commit; 100 files / 150 MB also suits slow Wi-Fi.
        val batches = ArrayList<MutableList<File>>()
        var cur = ArrayList<File>(); var bytes = 0L
        for (f in files) {
            if (cur.isNotEmpty() && (cur.size >= 100 || bytes + f.length() > 150L * 1024 * 1024)) {
                batches += cur; cur = ArrayList(); bytes = 0
            }
            cur += f; bytes += f.length()
        }
        if (cur.isNotEmpty()) batches += cur

        var sent = 0
        var sentBytes = 0L
        batches.forEachIndexed { i, b ->
            val pairs = b.map { it to it.relativeTo(outbox).path.replace(File.separatorChar, '/') }
            up.commit(pairs, "Upload from $site ($stamp, part ${i + 1}/${batches.size})")
            b.forEach { sentBytes += it.length(); it.delete() }
            sent += b.size
        }
        store.markUploaded(rows.map { it.id })
        pruneEmptyDirs(outbox)
        return "${rows.size} events, $sent files, ${"%.1f".format(sentBytes / 1e6)} MB"
    }

    private fun writeStatus(f: File) {
        f.parentFile?.mkdirs()
        val j = JSONObject()
            .put("site", prefs.site)
            .put("updated", java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss Z", java.util.Locale.US).format(java.util.Date()))
            .put("running_since_ms", Status.startedAtMs)
            .put("background_db", Status.backgroundDb.toDouble().takeIf { !it.isNaN() } ?: JSONObject.NULL)
            .put("trigger_db", Status.thresholdDb.toDouble().takeIf { !it.isNaN() } ?: JSONObject.NULL)
            .put("calibration_db", prefs.calibrationDb.toDouble())
            .put("margin_db", prefs.marginDb.toDouble())
            .put("camera", Status.cameraText)
            .put("battery", Status.batteryText)
            .put("free_bytes", Status.freeBytes)
            .put("warning", Status.warning)
            .put("app_version", BuildInfo.VERSION)
            .put("device", "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL} (Android ${android.os.Build.VERSION.RELEASE})")
        f.writeText(j.toString(2))
    }

    private fun csvEscape(s: String) = if (s.any { it == ',' || it == '"' || it == '\n' }) "\"${s.replace("\"", "\"\"")}\"" else s

    private fun pruneEmptyDirs(root: File) {
        root.walkBottomUp().filter { it.isDirectory && it != root }.forEach { if (it.list()?.isEmpty() == true) it.delete() }
    }
}

/** Filled in from the installed package when the service starts, so it always matches the app version. */
object BuildInfo { @Volatile var VERSION = "unknown" }
