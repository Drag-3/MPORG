import json
import logging
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

import diskcache
from acrcloud.recognizer import ACRCloudRecognizer
from ftfy import ftfy

from mporg import CONFIG_DIR
from mporg.types import Track

logging.getLogger('__main.' + __name__)
logging.propagate = True


class Fingerprinter:
    """
    Abstract class for fingerprinting audio files
    """
    @abstractmethod
    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        pass


class ACRFingerprinter(Fingerprinter):
    def __init__(self, config: dict):
        self.acrcloud = ACRCloudRecognizer(config)
        self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "audiocache_A"))
        # Acrcloud is paid, so I will not set the cache to expire as of now

    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        cache_key = str(path_to_fingerprint)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logging.info(f"Using cached result for {path_to_fingerprint}")
            return cached_result
        try:
            logging.info(f"Starting fingerprintng for {path_to_fingerprint}")
            result = self.acrcloud.recognize_by_file(str(path_to_fingerprint), 0)
        except Exception as e:
            logging.exception(f"Error recognizing fingerprint: {e}")
            return FingerprintResult(code=9, type="fail")

        out = FingerprintResult()
        if isinstance(result, str):  # For SOME reason recognize by file does NOT call json.loads
            result = json.loads(result)
        try:
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
                track_artists=tuple(artists),
                album_artists=tuple(artists),
                album_genres=genres,
                album_name=album
            )
            logging.debug(f"Fingerprint request returns: {out.results}")

            self.cache.set(cache_key, out)
            return out
        except Exception as e:
            logging.warning(f"Error when attempting to fingerprint. {e}")
            out.code = 999
            out.type = "fail"
            return out


@dataclass
class FingerprintResult:
    code: int = None
    type: str = None
    results: Track | dict = None
