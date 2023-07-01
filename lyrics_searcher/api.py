import threading
from pathlib import Path

from utils import Tagger
from utils import Track
from lyric_finder import LyricsSearcher

lyrics_searcher = LyricsSearcher()
locks = {}


def search_lyrics_by_name_artist(track_name, track_artist):
    track = Track(track_name=track_name, track_artists=[track_artist])
    return lyrics_searcher.get_genius_lyrics(track)


def search_lyrics_by_spotify_url(spotify_url, track_info=None):
    return lyrics_searcher.get_spotify_lyrics(t_url=spotify_url, track_info=track_info)


def search_lyrics_by_spotify_track_id(track_id, track_info=None):
    return lyrics_searcher.get_spotify_lyrics(t_id=track_id, track_info=track_info)


def search_lyrics_by_file(music_file: Path):
    filename = music_file.stem
    lyric_file = music_file.parent

    # Extract track metadata from the music file and search for lyrics
    track = extract_info_from_file(music_file)

    if not track:
        print(f"Failed to extract track metadata from: {music_file}")
        return

    if not track.track_url or 'https://open.spotify.com/track/' not in track.track_url:
        source_type = 'genius'
    else:
        source_type = 'spotify'

    result = None
    lyric_type = None
    if source_type == 'spotify':
        lyric_type, result = search_lyrics_by_spotify_url(track.track_url, track)
        if not lyric_type:
            source_type = 'genius'

    if source_type == "genius":
        result = search_lyrics_by_name_artist(track.track_name, track.track_artists)
        if result:
            lyric_type = 'txt'

    if result:
        destination = lyric_file / (filename + '.' + lyric_type)
        print(lyric_type)
        if not locks.get(str(destination)):
            locks[str(destination)] = threading.Lock()

        with locks[str(destination)]:
            if (lyric_file / (filename + ".txt")).exists() or (lyric_file / (filename + ".lrc")).exists():
                txt = lyric_file / (filename + ".txt")
                lrc = lyric_file / (filename + ".lrc")
                if txt.exists():
                    print(f"Deleting {txt}")
                    txt.unlink()

                else:
                    print(f"Deleting {lrc}")
                    lrc.unlink()

            with open(destination, 'w') as f:
                f.write(result)

        print(f"Lyric file created for: {music_file}")
    else:
        print(f"No lyrics found for: {music_file}")


def extract_info_from_file(file):
    metadata = Tagger(file)

    #print(metadata.tagger.get('comment'))
    comment = metadata.get('comment', [])
    artist = metadata.get('artist', [])
    title = metadata.get('title', [])
    album = metadata.get('album', [])
    track = Track(track_name=title[0] if title else '',
                  track_artists=artist[0] if artist else [],
                  track_url=comment[0] if comment else '',
                  album_name=album[0] if album else '')
    return track
