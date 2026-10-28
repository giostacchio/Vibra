#!/usr/bin/env python3
"""Patch the archived Vibra Android source for temporary YouTube video collections."""
from pathlib import Path

root = Path("VibraAndroid/app/src/main/java/it/vibra/player")
activity_path = root / "MainActivity.kt"
catalog_path = root / "data" / "CatalogClient.kt"

activity = activity_path.read_text(encoding="utf-8")
old = """        val id = playlistId(value)
        if (id.isBlank()) return showError(getString(R.string.invalid_playlist))
"""
new = """        val ids = videoIds(value)
        val id = if (ids.isEmpty()) playlistId(value) else ""
        if (id.isBlank() && ids.isEmpty()) return showError(getString(R.string.invalid_playlist))
"""
assert activity.count(old) == 1, "Cannot find MainActivity import guard"
activity = activity.replace(old,new)
old = "runCatching { CatalogClient.importPlaylist(id) }"
new = "runCatching { if (ids.isNotEmpty()) CatalogClient.importVideoIds(ids) else CatalogClient.importPlaylist(id) }"
assert activity.count(old) == 1, "Cannot find MainActivity import call"
activity = activity.replace(old,new)
anchor = "    private fun playlistId(value: String): String {"
method = """    private fun videoIds(value: String): List<String> {
        // YouTube temporary collection: watch_videos?video_ids=id1,id2,...
        val normalized = value.replace("%2C", ",", ignoreCase = true)
        val raw = normalized.substringAfter("video_ids=", "").substringBefore('&')
        if (raw.isBlank()) return emptyList()
        val parts = raw.split(',').map { it.trim() }
        if (parts.isEmpty() || parts.any { !it.matches(Regex("[A-Za-z0-9_-]{11}")) }) return emptyList()
        return parts.distinct().take(250)
    }

"""
assert activity.count(anchor) == 1, "Cannot find playlistId"
activity = activity.replace(anchor,method+anchor)
activity_path.write_text(activity,encoding="utf-8")

catalog = catalog_path.read_text(encoding="utf-8")
anchor = "    suspend fun resolveAudio(videoId: String): String = withContext(Dispatchers.IO) {"
method = """    suspend fun importVideoIds(ids: List<String>): List<Track> = withContext(Dispatchers.IO) {
        ensureInitialized()
        // Keep exactly the order from the imported link, even when a video is temporarily unreachable.
        ids.distinct().take(250).mapIndexed { index, id ->
            val url = "https://www.youtube.com/watch?v=$id"
            runCatching {
                val info = StreamInfo.getInfo(youtube, url)
                Track(
                    videoId = id,
                    title = info.name.ifBlank { "Brano " + (index + 1) },
                    artist = info.uploaderName?.takeIf { it.isNotBlank() } ?: "YouTube",
                    thumbnail = info.thumbnails.lastOrNull()?.url
                        ?: "https://i.ytimg.com/vi/$id/mqdefault.jpg",
                )
            }.getOrElse {
                // Metadata lookups may fail on an unstable connection; retain the video ID for playback.
                Track(
                    videoId = id,
                    title = "Brano " + (index + 1),
                    artist = "YouTube",
                    thumbnail = "https://i.ytimg.com/vi/$id/mqdefault.jpg",
                )
            }
        }
    }

"""
assert catalog.count(anchor) == 1, "Cannot find CatalogClient resolveAudio"
catalog = catalog.replace(anchor,method+anchor)
catalog_path.write_text(catalog,encoding="utf-8")
print("Vibra patched: standard playlists + watch_videos?video_ids= links")
