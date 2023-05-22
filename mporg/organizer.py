import enum
import logging
import os
import random
import threading
from contextlib import ExitStack
from functools import wraps
from threading import Lock
import time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
import shutil

from mutagen.id3 import ID3NoHeaderError
from tqdm import tqdm

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.wave import WAVE
from mutagen.asf import ASF

from mporg.spotify_searcher import SpotifySearcher, Track
from mporg.audio_fingerprinter import Fingerprinter, FingerprintResult

INVALID_PATH_CHARS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", ".", "\x00"]
logging.getLogger('__main__.' + __name__)
logging.propagate = True


def wait_if_locked(timeout):
    def decorator(func):
        def wrapper(*args, **kwargs):
            lock = None
            func_args = args

            for arg in args:
                if isinstance(arg, type(Lock())):
                    lock = arg
                    func_args = tuple(arg for arg in args if arg is not lock)
                    break

            if lock is None:
                raise ValueError("No Lock object found in arguments.")

            acquired = lock.acquire(timeout=timeout)

            if acquired:
                try:
                    result = func(*func_args, **kwargs)
                finally:
                    lock.release()

            else:
                raise TimeoutError(f"Timeout occurred while waiting for lock '{lock}'")

            return result

        return wrapper

    return decorator


class Tagger:
    """
    Wrapper class for mutagen objects, to provide consistent api for any filetype
    Take care to only use valid tags for each type
    """

    def __init__(self, file: Path):
        # Register Non-Standard Keys for Easy
        EasyID3.RegisterTextKey("comment", "COMM")
        EasyID3.RegisterTextKey("initialkey", "TKEY")
        EasyID3.RegisterTextKey("source", "WOAS")
        EasyMP4.RegisterTextKey("source", "source")
        EasyMP4.RegisterTextKey("initialkey", "----:com.apple.iTunes:initialkey")

        # Determine mutagen object to use
        extension = file.suffix
        if extension.lower() == ".mp3":
            try:
                self.tagger = EasyID3(file)
            except ID3NoHeaderError:
                self.tagger = mutagen.File(file, easy=True)
                self.tagger.add_tags()

        elif extension.lower() == ".m4a":
            self.tagger = EasyMP4(file)
        elif extension.lower() == ".wav":
            self.tagger = WAVE(file)
        elif extension.lower() in [".wma"]:
            self.tagger = ASF(file)
        else:
            logging.warning(f"{file} has invalid extension {extension}")
            raise ValueError("Invalid Extension")

    def get(self, key, value=None):
        return self.tagger.get(key, value)

    def __getitem__(self, item):
        return self.tagger.__getitem__(item)

    def __setitem__(self, key, value):
        self.tagger.__setitem__(key, value)

    def add_tags(self):
        self.tagger.add_tags()

    def save(self):
        self.tagger.save()


class TagType(enum.Enum):
    SPOTIFY = 0
    FINGERPRINTER = 1
    METADATA = 2


def file_generator(search):
    for root, _, files in os.walk(search):
        for file in files:
            yield root, file


def get_file_count(path):
    file_count = 0
    for entry in os.scandir(path):
        if entry.is_file():
            file_count += 1
        elif entry.is_dir():
            file_count += get_file_count(entry.path)
    return file_count


def pool_callback(result, pbar):
    pbar.update()
    if result:
        logging.warning(result)


def save_metadata(tagger: Tagger):
    retries = 3
    for _ in range(retries):
        try:
            tagger.save()
            break
        except mutagen.MutagenError:
            time.sleep(random.randint(1, 3))
    else:
        try:
            tagger.save()
        except mutagen.MutagenError as e:
            logging.exception(f"Unhandled MutagenError {e}")


class MPORG:

    def __init__(self, store: Path, search: Path, searcher: SpotifySearcher, fingerprinters: list[Fingerprinter]):
        self.search = search
        self.store = store
        self.sh = searcher
        self.af = fingerprinters
        self.file_locks = {}
        self.executor = ThreadPoolExecutor()

    def process_file(self, args):
        root, file = args
        try:
            logging.info(f"Organizing: {os.path.join(root, file)}")
            path = Path(os.path.join(root, file))
            try:
                metadata = Tagger(path)
            except mutagen.MutagenError:
                metadata = {}

            ext = file.split('.')[-1]
            results, tags_from = self.get_metadata(metadata, path)
            location = self.get_location(results, tags_from, metadata, ext, file)

            self.copy_file(path, location)

            lock = self.get_lock(location)
            if tags_from == TagType.SPOTIFY:
                self.update_metadata_from_spotify(lock, location, results)
            elif tags_from == TagType.FINGERPRINTER:
                self.update_metadata_from_fingerprinter(lock, location, results)

            return None
        except ValueError as e:
            #logging.exception(e)
            return f"Error processing file {file}: {e}"
        except Exception as e:
            #logging.exception(e)
            return f"Unknown Exception processing file {os.path.join(root, file)}\n EXP {e}"

    def organize(self):
        logging.top('Organizing files...')
        file_count = get_file_count(self.search)

        with tqdm(total=file_count, unit="file", miniters=0) as pbar:
            futures = []
            for root, file in file_generator(self.search):
                future = self.executor.submit(self.process_file, (root, file))
                future.add_done_callback(lambda f: pool_callback(f.result(), pbar))
                futures.append(future)

            wait(futures)

        logging.top('Organizing files finished.')

    def get_metadata(self, metadata: Tagger, file: Path):
        """
        Try to get metadata from Spotify, Audio Fingerprinting, or fall back to metadata provided by the file
        :param metadata: tagger object with original metadata of file
        :param file: Path of origin file
        :return: Tuple of metadata results and the source of the metadata
        """
        artist = [str(u).replace('\x00', '') for u in metadata.get('artist', '')]  # Replace Null Bytes
        title = [str(u).replace('\x00', '') for u in metadata.get('title', '')]
        if len(artist) == 1:
            artist = "".join(artist)
        if len(title) == 1:
            title = "".join(title)

        logging.info(f"Attempting to get metadata for {title} by {artist}")
        spotify_results = self.search_spotify(title, artist)
        if spotify_results:
            logging.info(f"Metadata found on Spotify for {title} by {artist}")
            logging.debug(spotify_results)
            return spotify_results, TagType.SPOTIFY
        if self.af:
            fingerprint_results = self.get_fingerprint_metadata(file)
            if fingerprint_results:
                if fingerprint_results.type == "spotify":
                    spotify_results = self.get_fingerprint_spotify_metadata(
                        fingerprint_results.results.get("spotifyid"))
                    if spotify_results:
                        logging.info(f"Metadata found using audio fingerprinting and Spotify for ID:"
                                     f" {fingerprint_results.results.get('spotifyid')}")
                        logging.debug(spotify_results)
                        return spotify_results, TagType.SPOTIFY
                else:
                    logging.info(f"Metadata found using audio fingerprinting: {fingerprint_results.results.track_name}"
                                 f" by {fingerprint_results.results.track_artists}")
                    logging.debug(fingerprint_results.results)
                    return fingerprint_results.results, TagType.FINGERPRINTER
        else:
            logging.debug("No Fingerprinters provided. Fingerprinting disabled")

        logging.info(f"No Metadata found for {file}")
        return None, TagType.METADATA

    def search_spotify(self, title: str, artist: str) -> Track:
        results = None
        if title and artist:
            results = self.sh.search(name="".join(title), artist=artist)
            logging.info(f"Spotify Results: {results}")
        return results

    def get_fingerprint_metadata(self, file: Path) -> FingerprintResult | None:
        for fingerprinter in self.af:
            results = fingerprinter.fingerprint(file)
            if results.code == 0:
                return results
        return None

    def get_fingerprint_spotify_metadata(self, spotify_id: str) -> Track | None:
        results = self.sh.search(spot_id=spotify_id)
        if results:
            return results
        return None

    def get_location(self, results: Track, tags_from: TagType, metadata: Tagger, ext: str, file: str) -> Path:
        """
        Determine the correct location to move the file based on metadata results and source
        :param file: Filename of original file
        :param results: Track Object containing Metadata
        :param tags_from: Source of Tags
        :param metadata: # Tagger object containing origin file tags
        :param ext: # Extension of original file
        :return: The path of the destination file
        """
        if tags_from == TagType.SPOTIFY:
            return self.spotify_location(results, ext)
        elif tags_from == TagType.FINGERPRINTER:
            return self.fingerprinter_location(results, ext)
        elif tags_from == TagType.METADATA:
            return self.metadata_location(metadata, ext, file)

    def spotify_location(self, results: Track, ext: str) -> Path:
        album_artist, album_name, track_artist, track_name = _sanitize_results(results)

        return self.store / album_artist / \
            f"{results.album_year} - {album_name.strip()}" / \
            f"{results.track_number}. - {track_artist} - {track_name}.{ext}"

    def fingerprinter_location(self, results: Track, ext: str) -> Path:
        album_artist, album_name, track_artist, track_name = _sanitize_results(results)

        return self.store / album_artist / \
            (f"{results.track_year} - " + f"{album_name}" if results.track_year else f"{album_name}") / \
            f"{track_artist} - {track_name}.{ext}"

    def metadata_location(self, metadata: Tagger, file_extension: str, file_name: str) -> Path:
        title = metadata.get("title")
        artist = metadata.get("artist")
        album = metadata.get("album")

        if not all((title, artist, album)):
            logging.warning(f"Cannot find enough metadata to organize '{file_name}' ...")
            return self.store / "_TaggingImpossible" / file_name

        track_artist = ", ".join(artist).strip()
        year = "".join(metadata.get('date', "")).strip()
        album = "".join(metadata.get('album', "")).strip()
        track = "".join(metadata.get('title', "")).strip()
        track_num = "".join(metadata.get('tracknumber', ["1"]))
        artist = [a.replace("/", ", ").strip() for a in metadata.get('artist', [])]
        # MP4 files get artists as '/' separated strings, split them apart here
        # If the artist name actually has '/', sorry

        if title and artist and metadata.get('album') and not metadata.get('albumartist'):
            album_artist = ", ".join(artist).strip()  # Use artist instead
        else:
            album_artist = ", ".join(metadata.get('albumartist', [])).strip()

        # Build path using pathlib
        path = self.store / _remove_invalid_path_chars(album_artist)
        if year:
            if isinstance(year, str):
                path /= f"{_remove_invalid_path_chars(year)} - {_remove_invalid_path_chars(album)}"
            else:
                path /= f"{year} - {_remove_invalid_path_chars(album)}"
        else:
            path /= _remove_invalid_path_chars(album)

        parts = []
        # Build filename
        if track_num:
            if isinstance(track_num, str):  # Prob in form num / total so remove the /total
                parts.append(f"{int(_remove_invalid_path_chars(track_num.split('/')[0]))}.")
            else:
                parts.append(f"{track_num}.")
        if track_artist and track_artist != "Unknown":
            parts.append(_remove_invalid_path_chars(track_artist))
        if track:
            parts.append(_remove_invalid_path_chars(track))

        path /= f'{" - ".join(parts)}.{file_extension}'
        return path

    def copy_file(self, source: Path, destination: Path) -> None:
        """
        Copy the file from the source location to the destination location
        :param source:
        :param destination:
        :return:
        """
        if not os.path.exists(destination):
            logging.info(f"Copying {source} to {destination}")

            if source not in self.file_locks:
                self.file_locks[source] = Lock()
            if destination not in self.file_locks:
                self.file_locks[destination] = Lock()
            if destination.parent.absolute() not in self.file_locks:
                self.file_locks[destination.parent.absolute()] = Lock()

            locks = (self.file_locks[source],
                     self.file_locks[destination.parent.absolute()],
                     self.file_locks[destination])
            retries = 3  # Maximum number of retries
            for _ in range(retries):
                try:
                    with ExitStack() as stack:
                        for lock in locks:
                            stack.enter_context(lock)
                        os.makedirs(os.path.dirname(destination), exist_ok=True, mode=0o777)
                        shutil.copyfile(source, destination)
                    break  # Copying succeeded, exit the loop
                except (OSError, IOError) as e:
                    logging.warning(f"Error copying file: {e}")
                    time.sleep(1)  # Wait for 1 second before retrying
            else:
                logging.error(f"Failed to copy file after {retries} retries: {source}")
        else:
            logging.info(f"Destination file already exists:{source} -> {destination}")

    def get_lock(self, path: Path) -> Lock:
        if path not in self.file_locks:
            self.file_locks[path] = Lock()

        return self.file_locks[path]

    @wait_if_locked(5)
    def update_metadata_from_spotify(self, location: Path, results: Track) -> None:
        """
        Update file metadata with Spotify results
        :param location:
        :param results:
        :return:
        """

        metadata = Tagger(location)
        metadata['title'] = results.track_name
        metadata['artist'] = ";".join(results.track_artists)
        metadata['album'] = results.album_name
        metadata['date'] = results.album_year
        metadata['tracknumber'] = str(results.track_number)
        metadata['discnumber'] = str(results.track_disk)
        metadata['comment'] = results.track_url
        metadata['source'] = results.track_url
        metadata['albumartist'] = results.album_artists
        metadata['bpm'] = str(int(results.track_bpm))
        try:
            metadata['initialkey'] = results.track_key
        except TypeError:
            pass
        metadata['genre'] = results.album_genres

        save_metadata(metadata)

    @wait_if_locked(5)
    def update_metadata_from_fingerprinter(self, location: Path, results: Track) -> None:

        metadata = Tagger(location)
        metadata['title'] = results.track_name
        metadata['artist'] = ";".join(results.track_artists)
        metadata['albumartist'] = results.album_artists
        try:
            metadata['album'] = results.album_name
        except ValueError:
            pass
        try:
            metadata['date'] = results.track_year
        except ValueError:
            pass
        try:
            metadata['genre'] = results.album_genres
        except ValueError:
            pass

        save_metadata(metadata)


def _remove_invalid_path_chars(s: str) -> str:
    """Helper function to remove invalid characters from a string."""
    return ''.join(c for c in s if c not in INVALID_PATH_CHARS)


def _sanitize_results(results: Track) -> (str, str, str, str):
    """
    # Sanitize the strings and limit the total length of the sanitized results to ~190 characters
    # to ensure compatibility with both Windows (256-character limit) and Linux (4096-character limit) path lengths.
    # Leave room for a 66-character root directory.
    :param results:
    :return: tuple of sanitized and truncated album_artist, album_name, track_artist, track_name
    """
    album_artist = ", ".join(results.album_artists)
    track_artist = ", ".join(results.track_artists)

    track_artist = _remove_invalid_path_chars(track_artist)[:30].strip()
    album_artist = _remove_invalid_path_chars(album_artist)[:30].strip()

    album_name = _remove_invalid_path_chars(results.album_name)[:50].strip()
    track_name = _remove_invalid_path_chars(results.track_name)[:50].strip()

    # Calculate the total length of the sanitized results
    total_length = len(album_artist) + len(track_artist) + len(album_name) + len(track_name)

    # If the total length exceeds 190 characters, truncate the longest string(s)
    if total_length > 190:
        while total_length > 190:
            if len(album_name) > len(track_name):
                album_name = album_name[:-1].strip()
            else:
                track_name = track_name[:-1].strip()
            total_length = len(album_artist) + len(track_artist) + len(album_name) + len(track_name)

    return album_artist, album_name, track_artist, track_name
