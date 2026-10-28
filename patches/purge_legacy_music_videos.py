#!/usr/bin/env python3
"""Remove previously superseded YouTube entries when importing temporary playlists into Vibra."""
from pathlib import Path

root=Path("VibraAndroid/app/src/main/java/it/vibra/player")
store=root/"data/FavoritesStore.kt"
s=store.read_text(encoding="utf-8")
anchor="    fun addAll(tracks: List<Track>) {"
assert s.count(anchor)==1, "FavoritesStore.addAll not found"
new="""    // Remove only legacy Battisti/Mina links replaced by verified song recordings.
    // All unrelated favourites stay untouched.
    fun purgeLegacyBattistiMinaVideos(): Int {
        val retired = setOf(
            "b8BDwKKbdu0", // old Mina Insieme Carosello
            "_Hzq3WeEJ9c", // old Mina Mi sei scoppiato (advertising short)
            "boHdH7hq9XA", // old Mina Grande grande grande ad
            "5LHDnExNY6I", // superseded Mina Ancora
            "GBFpmkhLjMQ", // superseded Battisti Io vorrei
            "4b-OPuArSlg", // superseded Battisti E penso a te
        )
        val prior = all()
        val clean = prior.filterNot { it.videoId in retired }
        if (clean.size != prior.size) save(clean)
        return prior.size - clean.size
    }

"""
s=s.replace(anchor,new+anchor)
store.write_text(s,encoding="utf-8")

activity=root/"MainActivity.kt"
s=activity.read_text(encoding="utf-8")
anchor="                    favorites.addAll(tracks)"
assert s.count(anchor)==1,"MainActivity playlist save not found"
s=s.replace(anchor,"                    if (ids.isNotEmpty()) favorites.purgeLegacyBattistiMinaVideos()\n"+anchor)
activity.write_text(s,encoding="utf-8")
print("PATCH OK: old advertising/superseded video ids are removed on temporary playlist import")
