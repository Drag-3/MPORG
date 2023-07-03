import logging
import threading
from pathlib import Path

from lyrics_searcher.utils import Tagger
from lyrics_searcher.utils import Track
from lyrics_searcher.lyric_finder import LyricsSearcher

lyrics_searcher = LyricsSearcher()


def search_lyrics_by_name_artist(track_name, track_artist):
    track = Track(track_name=track_name, track_artists=[track_artist])
    return lyrics_searcher.get_genius_lyrics(track)


def search_lyrics_by_spotify_url(spotify_url, track_info=None, lrc=False):
    return lyrics_searcher.get_spotify_lyrics(t_url=spotify_url, track_info=track_info, lrc=lrc)


def search_lyrics_by_spotify_track_id(track_id, track_info=None, lrc=False):
    return lyrics_searcher.get_spotify_lyrics(t_id=track_id, track_info=track_info, lrc=lrc)


def search_lyrics_by_file(music_file: Path, lrc=False):
    # Extract track metadata from the music file and search for lyrics
    track = extract_info_from_file(music_file)

    if not track:
        logging.warning(f"Failed to extract track metadata from: {music_file}")
        return None, None

    if not track.track_url or 'https://open.spotify.com/track/' not in track.track_url:
        source_type = 'genius'
    else:
        source_type = 'spotify'

    result = None
    lyric_type = None
    if source_type == 'spotify':
        lyric_type, result = search_lyrics_by_spotify_url(track.track_url, track, lrc)
        if not lyric_type:
            source_type = 'genius'

    if source_type == "genius":
        result = search_lyrics_by_name_artist(track.track_name, track.track_artists)
        if result:
            lyric_type = 'txt'

    if result:
        return lyric_type, result
    return None, None


def extract_info_from_file(file):
    metadata = Tagger(file)

    comment = metadata.get('comment', [])
    artist = metadata.get('artist', [])
    title = metadata.get('title', [])
    album = metadata.get('album', [])
    track = Track(track_name=title[0] if title else '',
                  track_artists=artist[0] if artist else [],
                  track_url=comment[0] if comment else '',
                  album_name=album[0] if album else '')
    return track
