from pathlib import Path

root = Path('VibraAndroid/app/src/main/java/it/vibra/player')
main = root / 'MainActivity.kt'
catalog = root / 'data' / 'CatalogClient.kt'

s = main.read_text(encoding='utf-8')
needle = '        val id = playlistId(value)\n        if (id.isBlank()) return showError(getString(R.string.invalid_playlist))'
replacement = '''        val videoIds = playlistVideoIds(value)
        val id = if (videoIds.isEmpty()) playlistId(value) else ""
        if (videoIds.isEmpty() && id.isBlank()) return showError(getString(R.string.invalid_playlist))'''
assert s.count(needle) == 1, 'Importazione principale non trovata (formato sorgente diverso)'
s = s.replace(needle, replacement, 1)
needle = 'runCatching { CatalogClient.importPlaylist(id) }'
replacement = 'runCatching { if (videoIds.isNotEmpty()) CatalogClient.importVideoIds(videoIds) else CatalogClient.importPlaylist(id) }'
assert s.count(needle) == 1, 'Chiamata CatalogClient non trovata'
s = s.replace(needle, replacement, 1)
needle = '    private fun playlistId(value: String): String {'
replacement = '''    // Accetta anche le playlist temporanee di YouTube create con
    // https://www.youtube.com/watch_videos?video_ids=id1,id2,...
    // mantenendo l'ordine originale degli ID, senza richiedere un ID list=.
    private fun playlistVideoIds(value: String): List<String> {
        val decoded = runCatching {
            android.net.Uri.parse(value).getQueryParameter("video_ids")
        }.getOrNull()
        val raw = decoded ?: value.substringAfter("video_ids=", "").substringBefore('&')
        return raw.split(',')
            .map { it.trim() }
            .filter { it.matches(Regex("[A-Za-z0-9_-]{11}")) }
            .distinct()
            .take(250)
    }

    private fun playlistId(value: String): String {'''
assert s.count(needle) == 1, 'Funzione playlistId non trovata'
s = s.replace(needle, replacement, 1)
main.write_text(s, encoding='utf-8')

s = catalog.read_text(encoding='utf-8')
needle = '    suspend fun resolveAudio(videoId: String): String = withContext(Dispatchers.IO) {'
replacement = '''    // Importazione bulk per URL watch_videos?video_ids=.
    // Tutti i titoli sono recuperati singolarmente con NewPipe Extractor
    // (nessun MP3 viene scaricato o conservato dall'app).
    suspend fun importVideoIds(videoIds: List<String>): List<Track> = withContext(Dispatchers.IO) {
        ensureInitialized()
        videoIds.distinct().take(250).mapNotNull { id ->
            runCatching {
                val info = StreamInfo.getInfo(youtube, "https://www.youtube.com/watch?v=$id")
                Track(
                    videoId = id,
                    title = info.name.ifBlank { "Brano YouTube" },
                    artist = info.uploaderName?.takeIf { it.isNotBlank() } ?: "YouTube",
                    thumbnail = info.thumbnails.lastOrNull()?.url
                        ?: "https://i.ytimg.com/vi/$id/mqdefault.jpg",
                )
            }.getOrNull()
        }.ifEmpty { throw IOException("Nessun brano disponibile nella playlist") }
    }

    suspend fun resolveAudio(videoId: String): String = withContext(Dispatchers.IO) {'''
assert s.count(needle) == 1, 'Funzione resolveAudio non trovata'
s = s.replace(needle, replacement, 1)
catalog.write_text(s, encoding='utf-8')
print('PATCH OK: Vibra importa playlist standard list= e playlist temporanee video_ids=')
