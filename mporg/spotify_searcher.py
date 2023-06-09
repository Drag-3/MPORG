import logging
from dataclasses import dataclass
from urllib.error import HTTPError

import diskcache
import spotipy
import spotipy as sy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
from mporg import CONFIG_DIR

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


@dataclass(frozen=True)
class Track:
    track_name: str = None
    track_number: int = None
    track_year: str = None
    track_key: str = None
    track_bpm: str = None
    track_disk: int = None
    track_artists: tuple[str, ...] = None
    album_name: str = None
    album_artists: tuple[str, ...] = None
    album_year: str = None
    album_size: int = None
    track_url: str = None
    album_genres: str = None
    track_id: str = None
    album_id: str = None


class SpotifySearcher:
    def __init__(self, cid: str, secret: str):
        try:
            auth_path = CONFIG_DIR / ".sp_auth_cache"
            auth_cache = sy.CacheFileHandler(auth_path)
            self.client_cred = SpotifyClientCredentials(client_id=cid, client_secret=secret, cache_handler=auth_cache)
            self.spot = sy.Spotify(auth_manager=self.client_cred, requests_timeout=45, retries=5)

            self.spot.user_playlists("spotify")  # Check if credentials are sufficient
            self.cache = diskcache.Cache(directory=str(CONFIG_DIR / "spotifycache"))
            self.cache.expire(60 * 60 * 12)  # Set the cache to expire in 12 hours
        except SpotifyOauthError as e:
            logging.exception(e)
            raise e

    def search(self, name: str = None, artist: str = None, spot_id: str = None) -> None | Track:
        cache_key = f"{name}-{artist}-{spot_id}"
        if cache_key in self.cache:
            # If the response is already in the cache, return it
            logging.info("Returning cached spotify response")
            return self.cache[cache_key]
        if not name and not spot_id:
            logging.warning("No name or ID provided.")
            return None

        if spot_id:
            logging.debug("Searching with Spotify ID")
            result = self.spot.track(spot_id)
            track_info = self._get_track_info(result)
            self.cache[cache_key] = track_info  # Cache the response
            return track_info

        # Refine the search query to include only tracks that match the artist name and track name
        logging.debug("Searching with Track name and artist")
        query = f'{artist[0] if isinstance(artist, list) else artist} {name}'
        results = self.spot.search(q=query, type="track", limit=50)

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
            audio = self.spot.audio_analysis(item["id"])
        except HTTPError:
            audio = dict()
        try:
            genres = [genre for artist in item["artists"] for genre in self.spot.artist(artist["id"])["genres"]]
        except HTTPError:
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
