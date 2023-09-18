import json
import logging
from pathlib import Path

import diskcache
from acrcloud.recognizer import ACRCloudRecognizer
from ftfy import ftfy

from mporg import CONFIG_DIR
from mporg.audio_fingerprinter import Fingerprinter, FingerprintResult
from mporg.credentials.providers import CredentialProvider
from mporg.types import Track


class ACRCloudFingerprinter(Fingerprinter):
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


class ACRCloudCredentialProvider(CredentialProvider):
    SPEC = {
        "host": lambda x: ".acrcloud.com" in x,  # host must contain .acrcloud.com
        "access_key": lambda x: len(x) > 0,  # access_key must not be empty
        "access_secret": lambda x: len(x) > 0,  # access_secret must not be empty
    }
    PNAME = "ACRCloud"
    CONFIG_NAME = "acoustid.json"

    def get_credentials(self):
        # Try to get and verify credentials
        credentials = self._load_from_file()
        if (
            credentials
            and self.verify_spec(credentials)
            and self.verify_credentials(credentials)
        ):
            return credentials

        # Ask user for ACRCloud credentials
        print("Getting ACRCloud Credentials. Enter q to skip this fingerprinter..")
        while (
            not credentials
            or not self.verify_spec(credentials)
            or not self.verify_credentials(credentials)
        ):
            host = input("Enter the ACRCloud host: ").strip().lower()
            if host == "q":
                return {}

            key = input("Enter your ACRCloud access key: ").strip().lower()
            if key == "q":
                return {}

            secret = input("Enter your ACRCloud access secret: ").strip().lower()
            if secret == "q":
                return {}

            credentials = {
                "host": host,
                "access_key": key,
                "access_secret": secret,
                "secret": secret,
                "debug": False,
                "timeout": 10,
            }

        return credentials

    def verify_credentials(self, credentials):
        config = credentials
        recognizer = ACRCloudRecognizer(config)

        try:
            #
            dummy_fingerprint = {"sample": b"A"}  #Use a dummy fingerprint because ACRCloud requires a sample

            # Use the do_recogize() method to verify credentials
            result = recognizer.do_recogize(
                config.get("host"),
                dummy_fingerprint,
                "fingerprint",
                config.get("access_key"),
                config.get("access_secret"),
                10,
            )

            result = json.loads(result)
            if (
                result["status"]["code"] == 1001
                and result["status"]["msg"] == "No result"  # The key and secret are valid if the result is "No result"
            ):
                logging.top("ACRCloud credentials are valid.")
                return True
            else:
                logging.warning(
                    f"ACRCloud credentials are invalid: {result['status']['msg']}"
                )
                return False
        except Exception as e:
            logging.warning(
                "Error occurred while verifying ACRCloud credentials:", str(e)
            )
            return False
