import os

import spotipy.oauth2
from mutagen.easyid3 import EasyID3
from pathlib import Path
import spotipy as sy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
from pprint import pprint
from dataclasses import dataclass
from urllib import parse
import shutil
from getopt import getopt
import sys
from argparse import ArgumentParser
import glob
import json


def encode(url: str):
    return parse.quote(url.encode('utf8'))


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

}

INVALID_PATH_CHARS = r'\/:*?.<>|"'


class SpotifySearcher:
    pass


class MP3ORG:

    def __init__(self, store: Path, search: Path, searcher: SpotifySearcher, v=False):
        self.search = search
        self.store = store
        self.v = v
        self.sh = searcher

        EasyID3.RegisterTextKey("comment", "COMM")
        EasyID3.RegisterTextKey("initialkey", "TKEY")
        EasyID3.RegisterTextKey("source", "WOAS")

    def organize(self):
        """
        Iterate Over files in search directory, Then Create needed dirs in store
        Then move the files to the correct dir
        :return:
        """
        files = glob.iglob(str(self.search), recursive=True)

        for root, subdirs, files in os.walk(self.search):
            for file in files:
                try:
                    metadata = EasyID3(Path(root) / file)
                    artist = metadata.get('artist')
                    title = metadata.get('title')
                    if not title:
                        results = self.sh.search(None, artist)
                    else:
                        results = self.sh.search("".join(title), artist)  # Try to search spotify for correct metadata
                    print(results)
                    print(metadata.get('artist'), metadata.get('albumartist'), metadata.get('date'), metadata.get('album'), metadata.get('tracknumber'), metadata.get('title'))
                    if results:
                        album_artist = ", ".join(results.album_artists)
                        track_artist = ", ".join(results.track_artists)
                        location = self.store / ''.join([i for i in album_artist if i not in INVALID_PATH_CHARS]) / f"{results.album_year} - {''.join(i for i in results.album_name if i not in INVALID_PATH_CHARS)}" / f"{results.track_number}. - {''.join(i for i in track_artist if i not in INVALID_PATH_CHARS)} - {''.join(i for i in results.track_name if i not in INVALID_PATH_CHARS)}.mp3"
                        print(location)
                    else:  # Could Not find on spotify, try another service, or audio fingerprinting in future

                        if not title or not artist or not metadata.get('albumartist') or not metadata.get('album'):  # We Don't have enough info to tag (If I had Audio Analysis use it here)
                            location = self.store / "_TaggingImpossible" / file

                        else:  # Create path based on embedded path
                            album_artist = ", ".join(metadata.get('albumartist'))
                            track_artist = ", ".join(metadata.get('artist'))
                            year = "".join(metadata.get('date', ""))
                            album = "".join(metadata.get('album', ""))
                            track = "".join(metadata.get('title', ""))
                            track_num = "".join(metadata.get('tracknumber', ["1"]))
                            location = self.store / "".join(i for i in album_artist if
                                                        i not in INVALID_PATH_CHARS) / f"{year} - {''.join(i for i in album if i not in INVALID_PATH_CHARS)}" / f"{track_num}. - {''.join(i for i in track_artist if i not in INVALID_PATH_CHARS)} - {''.join(i for i in track if i not in INVALID_PATH_CHARS)}.mp3"
                        print(location)
                    if not os.path.exists(location):
                        try:
                            shutil.copy(Path(root) / file, location)
                        except IOError as io_err:
                            os.makedirs(os.path.dirname(location), exist_ok=True)
                            shutil.copy(Path(root) / file, location)
                    if results:  # Update Metadata with info from Spotify api
                        metadata = EasyID3(location)
                        metadata['title'] = results.track_name
                        metadata['artist'] = ";".join(results.track_artists)
                        metadata['album'] = results.album_name
                        metadata['date'] = results.album_year
                        metadata['tracknumber'] = str(results.track_number)
                        metadata['discnumber'] = str(results.track_disk)
                        metadata['comment'] = results.track_url
                        metadata['source'] = results.track_url
                        metadata['albumartist'] = results.album_artists
                        metadata['bpm'] = str(results.track_bpm)
                        metadata['initialkey'] = results.track_key
                        metadata['genre'] = results.album_genres
                        metadata.save()
                except ValueError as e:
                    # File is not a valid mp3, or does not have any id3 tags, skip it
                    if self.v:
                        print(f"{e} | {file} is not a valid mp3 file or does not have id3 tags")
                    continue


class SpotifySearcher:
    def __init__(self, cid, secret, v=False):
        self.client_cred = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        self.spot = sy.Spotify(auth_manager=self.client_cred, requests_timeout=45, retries=5)

        self.spot.user_playlists("spotify")  # Check is credentials are sufficient
        self.v = v

    def search(self, name, artist):
        if not name:  # As of Now tracks without a title do not work cause we compare against the title
            return None

        match = False
        offset = 0
        result = None
        pass
        query = f'artist:{artist} track:{name}'
        page = self.spot.search(q=query, limit=20, offset=offset)
        while True:
            for track in page['tracks']['items']:
                q_name = "".join(i for i in track['name'] if i not in r'\/:*?<>|"')
                if q_name == name:
                    print("FOUND")
                    match = True
                    result = track
                    break
                else:
                    if self.v:
                        print(f"{q_name} != {name} {q_name != name}")
            if not match:  # Check next page if it is available
                offset += 1
                if self.v:
                    print(page)
                    print(f"No match on page {page['tracks']['href'].split('&')[-2].split('=')[-1]}")
                if page['tracks']['next']:
                    page = self.spot.next(page['tracks'])
                    if self.v:
                        print(f"Trying page {page['tracks']['next'].split('&')[-2].split('=')[-1]}")
                else:
                    break
            else:
                break

        if not match:
            print("No Match")
            return None
        # Get Further Metadata with Spotify Api
        audio = self.spot.audio_analysis(result['id'])
        genres = []
        for artist in track['artists']:
            g = self.spot.artist(artist['id'])['genres']
            print(g)
            genres.extend(g)

        return Track(
            track_name=result['name'],
            track_number=int(result['track_number']),
            track_year=result['album']["release_date"].split('-')[0],  # YYYY-MM-DD
            track_disk=int(result['disc_number']),
            track_artists=[artist['name'] for artist in result['artists']],
            track_bpm=audio['track']['tempo'],
            track_key=PITCH_CODES[audio['track']['key']],

            album_name=result['album']['name'],
            album_year=result['album']["release_date"].split('-')[0],  # YYYY-MM-DD
            album_size=int(result['album']['total_tracks']),
            album_artists=[artist['name'] for artist in result['album']['artists']],
            album_genres=";".join(genres),

            track_url=result['external_urls']['spotify']

        )


@dataclass
class Track:
    track_name: str
    track_number: int
    track_year: str
    track_key: str
    track_bpm: str
    track_disk: int
    track_artists: list
    album_name: str
    album_artists: list
    album_year: str
    album_size: int
    track_url: str
    album_genres: str


def get_credentials(save_file):
    cid = input("Enter Spotify Client ID: ")

    secret = input("Enter Spotify Client Secret: ")
    creds = {"cid": cid,
             "secret": secret}

    save_file.seek(0)
    save_file.truncate()  # Erase old data

    json.dump(creds, save_file)
    save_file.flush()

    return creds


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show Version", action="store_true")
    arg_parser.add_argument("-V", "--verbose", help="Print", action="store_true")
    arg_parser.add_argument("store_path", help="Root of area to store organized files")
    arg_parser.add_argument("search_path", help="Source dir to look for mp3 files in. Is not recursive")

    args = arg_parser.parse_args()
    print(args)

    if args.version:
        print("V.0.1.0.1.1.0")
        sys.exit(0)

    import json
    usr_home = Path.home()
    config_folder = usr_home / ".MP3ORG"
    credential_path = config_folder / "credentials.json"
    if not os.path.exists(config_folder):
        os.mkdir(config_folder)
    if not os.path.exists(credential_path):
        credential_path.touch(0o666)

    # Attempt to get cred from file
    with open(credential_path, 'r+') as cred:
        try:
            data = json.load(cred)
        except json.decoder.JSONDecodeError:
            # The Json file is empty or invalid, so ask user for new
            data = get_credentials(cred)

        while True:
            try:
                searcher = SpotifySearcher(data["cid"], data["secret"], args.verbose)
                break
            except SpotifyOauthError:
                # Creds are Invalid so ask for new ones
                print("Stored Credentials are not valid, ask for new ones")
                data = get_credentials(cred)

    org = MP3ORG(Path(args.store_path), Path(args.search_path), searcher, args.verbose)
    org.organize()


if __name__ == "__main__":
    main()
