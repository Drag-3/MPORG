import logging
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
import json

import musicbrainzngs
import diskcache
from ftfy import ftfy
from acoustid import fingerprint_file, lookup
from acrcloud.recognizer import ACRCloudRecognizer

from mporg import CONFIG_DIR
from mporg.spotify_searcher import Track


logging.getLogger('__main.' + __name__)
logging.propagate = True


class Fingerprinter:
    @abstractmethod
    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        pass


class ACRFingerprinter(Fingerprinter):
    def __init__(self, config: dict):
        self.acrcloud = ACRCloudRecognizer(config)
        self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "audiocache_A"))

    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        cache_key = str(path_to_fingerprint)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logging.info(f"Using cached result for {path_to_fingerprint}")
            return cached_result
        try:
            logging.info(f"Starting fingerprintng for {path_to_fingerprint}")
            result = self.acrcloud.recognize_by_file(path_to_fingerprint, 0)
        except Exception as e:
            logging.exception(f"Error recognizing fingerprint: {e}")
            return FingerprintResult(code="error", type="fail")

        out = FingerprintResult()
        if not isinstance(result, dict):  # A Weired Error occured in acrcloud package
            logging.critical(f"Invalid Response. Not of dict {result} for ||| {path_to_fingerprint}")
            out.code = 999
            out.type = "fail"
            return out

        out.code = result['status']['code']
        if out.code != 0:
            logging.info(f"Fingerprint request returned code {out.code}")
            out.type = "fail"
            self.cache.set(cache_key, out)
            return out

        track_result = result['metadata']['music'][0]
        external_metadata = getattr(track_result.get('external_metadata'), 'spotify', {})
        spotify_id = external_metadata.get('track', {}).get('id')
        if spotify_id:
            out.type = "spotify"
            out.results = {"spotifyid": spotify_id}
            logging.debug(f"Fingerprint request returned ID : {spotify_id}")
            self.cache.set(cache_key, out)
            return out

        album = track_result.get('album', {}).get('name')
        label = track_result.get('label')
        date = track_result.get('release_date', '')
        date = date.split('-')[0] if date else ''
        track = track_result.get('title')
        genres_o = track_result.get('genres', [])
        genres = []
        for g in genres_o:
            logging.debug(g)
            logging.debug(type(g))
            if isinstance(g, dict):
                genres.append(g.get('name'))
            else:
                try:
                    j = json.loads(g)
                    genres.append(j.get('name'))
                except TypeError:
                    genres.append(g)  # Is a normal string
        genres = ';'.join(genres)

        artists = [ftfy(z.get('name')) for z in track_result.get('artists', [])]

        out.type = "track"
        out.results = Track(
            track_name=track,
            track_year=date,
            track_artists=artists,
            album_artists=artists,
            album_genres=genres,
            album_name=album
        )
        logging.debug(f"Fingerprint request returns: {out.results}")

        self.cache.set(cache_key, out)
        return out


class MBFingerprinter(Fingerprinter):
    def __init__(self, mbid):
        musicbrainzngs.set_useragent("python-MPORG", "0.1", contact="juserysthee@gmail.com")
        self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "audiocache_M"))
        self.api_key = mbid
        musicbrainzngs.set_rate_limit(False)

    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        cache_key = str(path_to_fingerprint)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logging.info(f"Using cached result for {path_to_fingerprint}")
            return cached_result
        try:
            logging.info(f"Starting fingerprintng for {path_to_fingerprint}")
            duration, fingerprint = fingerprint_file(str(path_to_fingerprint))
            result = lookup(self.api_key, fingerprint, duration, meta='recordings')
        except Exception as e:
            logging.exception(f"Error recognizing fingerprint: {e}")
            return FingerprintResult(code="error", type="fail")

        out = FingerprintResult()
        recordings = result.get('recordings', [])
        if not recordings:
            logging.debug(f"Fingerprint request returned no results")
            out.type = "fail"
            return out

        recording = recordings[0]
        release_id = recording.get('release', {}).get('id')
        if not release_id:
            logging.debug(f"Fingerprint request returned no release ID")
            out.type = "fail"
            return out

        try:
            release = musicbrainzngs.get_release_by_id(release_id, includes=['artists', 'recordings'])
        except musicbrainzngs.WebServiceError as exc:
            logging.exception(f"Error fetching release info from MusicBrainz: {exc}")
            out.type = "fail"
            return out

        external_metadata = recording.get('externalids', {}).get('spotify', {})
        spotify_id = external_metadata.get('uri', '').split(':')[-1]
        if spotify_id:
            out.type = "spotify"
            out.results = {"spotifyid": spotify_id}
            logging.debug(f"Fingerprint request returned ID: {spotify_id}")
            return out

        recording_info = next(
            (x for x in release['medium-list'][0]['track-list'] if x['recording']['id'] == recording['id']), None)
        if not recording_info:
            logging.debug(f"Fingerprint request returned no recording info")
            out.type = "fail"
            return out

        track = recording_info['title']
        album = release['title']
        artists = [ftfy(x['name']) for x in recording['artist-credit']]
        album_artists = [ftfy(x['name']) for x in release['artist-credit']]
        album_genres = ";".join(self._get_album_genres(release))

        out.type = "track"
        out.results = Track(
            track_name=track,
            track_year=release.get('date', '')[:4],
            track_artists=artists,
            album_artists=album_artists,
            album_genres=album_genres,
            album_name=album
        )
        logging.debug(f"Fingerprint request returns: {out.results}")
        return out

    @staticmethod
    def _get_album_genres(release: dict) -> list[str]:
        tags = release.get('tag-list', [])
        return [x['name'] for x in tags if x.get('count', 0) > 1]


@dataclass
class FingerprintResult:
    code: str = None
    type: str = None
    results: Track | dict = None
