import logging
from pathlib import Path

import diskcache
import musicbrainzngs
import requests
from acoustid import fingerprint_file, lookup, FingerprintGenerationError
from ftfy import ftfy

from mporg import CONFIG_DIR, VERSION
from mporg.audio_fingerprinter import Fingerprinter, FingerprintResult
from mporg.credentials.providers import CredentialProvider
from mporg.types import Track


class MBFingerprinter(Fingerprinter):
    def __init__(self, config):
        musicbrainzngs.set_useragent(app="python-MPORG", version=VERSION, contact="juserysthee@gmail.com")
        self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "audiocache_M"))
        self.cache.expire(60 * 60 * 12)  # Set the cache to expire in 12 hours
        self.api_key = config.get('api')
        musicbrainzngs.set_rate_limit(False)

    def fingerprint(self, path_to_fingerprint: Path) -> 'FingerprintResult':
        cache_key = str(path_to_fingerprint)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logging.info(f"Using cached result for {path_to_fingerprint}")
            return cached_result
        try:
            logging.info(f"Starting fingerprinting for {path_to_fingerprint}")
            duration, fingerprint = fingerprint_file(str(path_to_fingerprint))
            api_result = lookup(self.api_key, fingerprint, duration, meta='recordings')
        except FingerprintGenerationError as e:
            logging.info(f"Error recognizing fingerprint: {e}")
            return FingerprintResult(code=9, type="fail")

        out = FingerprintResult()
        result = api_result.get('results', [])
        if not result:
            logging.debug(f"Fingerprint request returned no results")
            out.type = "fail"
            return out

        recordings = result[0].get('recordings', [])
        if not recordings:
            logging.debug(f"Fingerprint request returned no results")
            out.type = "fail"
            return out

        recording = recordings[0]
        release_id = recording.get('id')
        if not release_id:
            logging.debug(f"Fingerprint request returned no release ID")
            out.type = "fail"
            return out

        try:
            musicbrainzngs.set_useragent(app="python-MPORG", version=VERSION, contact="juserysthee@gmail.com")
            m_response = musicbrainzngs.get_recording_by_id(release_id,
                                                            includes=['url-rels', 'artists', 'tags', 'releases'])
        except musicbrainzngs.WebServiceError as exc:
            logging.info(f"Error fetching release info from MusicBrainz: {exc}")
            out.type = "fail"
            out.code = 3
            return out

        recording_info = m_response.get('recording', {})
        if not recording_info:
            logging.info("Musicbrainz did not return any recording info")
            out.type = "fail"
            out.code = 7
            self.cache.set(cache_key, out)
            return out

        url_relations = recording_info.get('url-relation-list', [])
        for relation in url_relations:
            url = relation.get('target', '')
            if r'open.spotify.com/track/' in url:
                # Spotify Track. ID is in it
                spotify_id = url.split('/')[-1]
                out.type = "spotify"
                out.results = {"spotifyid": spotify_id}
                logging.debug(f"Fingerprint request returned ID: {spotify_id}")
                out.code = 0
                self.cache.set(cache_key, out)
                return out

        release_info = [r for r in recording_info.get('release-list', []) if isinstance(r, dict)]

        if not release_info:
            logging.info("Musicbrainz did not return any album information")
            out.type = "fail"
            out.code = 9
            self.cache.set(cache_key, out)
            return out

        for release in release_info:
            album = release.get('title', None)
            date = release.get('date', '0').split('-')[0]
            album_id = release.get('id', '')
            if all((album, date, album_id)):
                break

        track = recording_info['title']
        artist_credit = [a for a in recording_info['artist-credit'] if isinstance(a, dict)]

        artists = [ftfy(x.get('artist', {}).get('name', {})) for x in artist_credit]
        genres = []
        for artist in artist_credit:
            t_list = artist.get('artist', {}).get('tag-list', [])
            genres += t_list

        album_genres = ";".join(self._get_album_genres({'tag-list': genres}))

        album_artists = artists
        if not all((track, artists, album_artists, album)) or date == '0':
            logging.info("Musicbrainz did not return enough metadata")
            out.type = "fail"
            out.code = 15
            self.cache.set(cache_key, out)
            return out

        out.type = "track"
        out.code = 0
        out.results = Track(
            track_name=track,
            track_year=date,
            track_artists=tuple(artists),
            album_artists=tuple(album_artists),
            album_genres=album_genres,
            album_name=album,
            track_id=release_id,
            album_id=album_id
        )
        logging.debug(f"Fingerprint request returns: {out.results}")
        self.cache.set(cache_key, out)
        return out

    @staticmethod
    def _get_album_genres(release: dict) -> list[str]:

        tags = release.get('tag-list', [])
        t_names = set()
        for tag in tags:
            if int(tag.get('count', 0)) >= 1:
                t_names.add(tag.get('name'))
        return list(t_names)


class AcoustIDCredentialProvider(CredentialProvider):
    SPEC = {'api': lambda x: len(x) > 0}
    PNAME = "AcoustID"
    CONFIG_NAME = "acoustid.json"

    def get_credentials(self):
        credentials = self._load_from_file()
        if credentials and self.verify_spec(credentials) and self.verify_credentials(credentials):
            return credentials

        print("Getting AcoustID Credentials. Enter q to skip this fingerprinter..")
        while not credentials or not self.verify_spec(credentials) or not self.verify_credentials(credentials):
            api_key = input("Enter your AcoustID API Key: ")
            if api_key.lower() == "q":
                return None
            credentials = {"api": api_key}

        self.store_credentials(credentials)
        return credentials

    def verify_credentials(self, credentials):
        url = 'https://api.acoustid.org/v2/lookup'
        params = {
            'client': credentials.get('api'),
            'format': 'json',
            'duration': 30,
            'fingerprint': 'dummy'
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()
            if data.get('code') != 4:  # Code 4 is invalid api key
                logging.top("AcoustID credentials are valid.")
                return True
        except requests.exceptions.RequestException as e:
            logging.error("Error Connecting to AcoustID:", str(e))
            return False
        logging.warning('AcoustID Api key is incorrect')
        return False
