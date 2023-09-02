import json
import logging
import random
import threading
import time
from datetime import datetime, timedelta, date

import diskcache
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mporg import CONFIG_DIR
from mporg.types import Track

PITCH_CODES = {
    0: 'C',
    1: 'C♯/D♭',
    2: "D",
    3: 'D♯/E♭',
    4: 'E',
    5: 'E♯/F♭',
    6: 'G',
    7: 'G♯/A♭',
    8: 'A',
    9: 'A♯/B♭',
    10: 'B',
    11: 'B♯/C♭',
    12: 'N/A'
}

logging.getLogger('__main.' + __name__)
logging.propagate = True


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


locks = {}


class SpotifySearcher:
    def __init__(self, cid: str, secret: str):
        self.cid = cid
        self.secret = secret

        self.auth_path = CONFIG_DIR / ".sp_auth_cache"

        self.auth_lock = threading.Lock()
        self.auth_path_lock = threading.Lock()

        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

        self.token_info = self.load_auth()
        if self.token_info:
            self.session.headers.update(
                {'Authorization': f'{self.token_info["token_type"]} {self.token_info["access_token"]}'})

        self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "spotifycache"))
        self.cache.expire(60 * 60 * 12)  # Set the cache to expire in 12 hours
        self.semaphores = {
            'search': threading.Semaphore(3),
            'tracks': threading.Semaphore(3),
            'audio-analysis': threading.Semaphore(2),
            'artists': threading.Semaphore(2)
        }

    def load_auth(self):
        try:
            with self.auth_path_lock, open(self.auth_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
                info['expires'] = datetime.fromisoformat(info['expires'])
                return info
        except FileNotFoundError:
            return None

    def save_auth(self, data):
        with self.auth_path_lock, open(self.auth_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=json_serial)

    def authenticate(self, cid, secret):
        AUTH_URL = "https://accounts.spotify.com/api/token"
        auth_resp = requests.post(AUTH_URL, {"grant_type": "client_credentials",
                                             "client_id": cid,
                                             "client_secret": secret})
        auth_resp_json = auth_resp.json()
        access_token = auth_resp_json['access_token']
        token_type = auth_resp_json['token_type']

        expiration = auth_resp_json['expires_in']
        expiration_date_time = datetime.now() + timedelta(seconds=expiration)
        self.session.headers.update({'Authorization': f'{token_type} {access_token}'})

        return {'token_type': token_type, 'access_token': access_token, 'expires': expiration_date_time}

    def update_token(self):
        logging.info("Updating Token")
        new_token_info = self.authenticate(self.cid, self.secret)
        self.session.headers.update(
            {'Authorization': f'{new_token_info["token_type"]} {new_token_info["access_token"]}'})
        self.token_info = new_token_info
        self.save_auth(new_token_info)

    def token_expired(self):
        remaining = self.token_info.get('expires') - datetime.now()
        secs = remaining.total_seconds()
        return secs < 45

    def validate_token(self):
        if self.token_info is None or self.token_expired():
            with self.auth_lock:
                if self.token_info is None or self.token_expired():
                    self.update_token()

    def search(self, name: str = None, artist: str = None, spot_id: str = None) -> None | Track:
        cache_key = f"{name}-{artist}-{spot_id}"
        if cache_key in self.cache:
            # If the response is already in the cache, return it
            logging.info("Returning cached Spotify response")
            return self.cache[cache_key]
        if not name and not spot_id:
            logging.warning("No name or ID provided.")
            return None

        if spot_id:
            logging.debug("Searching with Spotify ID")
            result = self._get_item_base('tracks', spot_id)
            track_info = self._get_track_info(result)
            self.cache[cache_key] = track_info  # Cache the response
            return track_info

        # Refine the search query to include only tracks that match the artist name and track name
        logging.debug("Searching with Track name and artist")
        query = f'{artist[0] if isinstance(artist, list) else artist} {name}'
        results = self._get_item('search', q=query, type="track", limit=25)

        # Check each result to see if it matches the search criteria
        for item in results["tracks"]["items"]:
            if self._check_item_match(item, name, artist):
                logging.info("Match found")
                track_info = self._get_track_info(item)
                self.cache[cache_key] = track_info  # Cache the response
                return track_info

        logging.info("No match found")
        self.cache[cache_key] = None
        return None

    def _get_item(self, endpoint: str, **params):
        self.validate_token()
        with self.semaphores[endpoint]:
            response = self.session.get(f'https://api.spotify.com/v1/{endpoint}', params=params, timeout=20)
            if response.status_code == 429:
                retry_after = int(response.headers.get('retry-after', '1'))
                logging.warning(f" {endpoint} Rate limited. Waiting for {retry_after} seconds before retrying.")
                time.sleep(retry_after + random.randint(3, 7))
            elif response.status_code != 200:
                response.raise_for_status()
            return response.json()

    def _get_item_base(self, endpoint: str, value):
        self.validate_token()
        with self.semaphores[endpoint]:
            response = self.session.get(f"https://api.spotify.com/v1/{endpoint}/{value}", timeout=20)

            if response.status_code == 429:
                retry_after = int(response.headers.get('retry-after', '1'))
                logging.warning(f" {endpoint} Rate limited. Waiting for {retry_after} seconds before retrying.")
                time.sleep(retry_after + random.randint(3, 7))
            elif response.status_code != 200:
                response.raise_for_status()
            return response.json()

    @staticmethod
    def _check_item_match(item: dict, name: str | list, artist: str | list) -> bool:
        if item["name"].lower() == name.lower():
            if isinstance(artist, str):
                if any(artist.lower() in a["name"].lower() for a in item["artists"]):
                    return True
            elif isinstance(artist, list):
                if all(a["name"].lower() in artist for a in item["artists"]):
                    return True
        return False

    def _get_track_info(self, item: dict) -> Track:
        logging.debug("Searching additional metadata")
        try:
            audio = self._get_item_base('audio-analysis', item["id"])
        except requests.HTTPError:
            audio = dict()
        try:
            genres = [genre for artist in item["artists"] for genre in
                      self._get_item_base('artists', artist["id"])["genres"]]
        except requests.HTTPError:
            genres = []

        return Track(
            track_name=item['name'],
            track_number=int(item['track_number']),
            track_year=item['album']["release_date"].split('-')[0],  # YYYY-MM-DD
            track_disk=int(item['disc_number']),
            track_artists=tuple([artist['name'] for artist in item['artists']]),
            track_bpm=audio.get('track', {}).get('tempo'),
            track_key=PITCH_CODES[audio.get('track', {}).get('key', 12)],

            album_name=item['album']['name'],
            album_year=item['album']["release_date"].split('-')[0],  # YYYY-MM-DD
            album_size=int(item['album']['total_tracks']),
            album_artists=tuple([artist['name'] for artist in item['album']['artists']]),
            album_genres=";".join(genres),

            track_url=item['external_urls']['spotify']
        )
