import enum
import logging
import os
import random
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import ExitStack, contextmanager
from math import ceil
from pathlib import Path
from threading import Lock

import mutagen
from lyrics_searcher.api import search_lyrics_by_file
from tqdm import tqdm

from mporg.audio_fingerprinter import Fingerprinter, FingerprintResult
from mporg.spotify_searcher import SpotifySearcher
from mporg.types import Track, Tagger

INVALID_PATH_CHARS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", ".", "\x00"]
SUPPORTED_FILETYPES = [".mp3", ".wav", ".flac", ".ogg", ".wma", ".m4a", ".oga"]
logging.getLogger("__main__." + __name__)
logging.propagate = True


@contextmanager
def acquire(lock: threading.Lock, blocking=True, timeout=None):
    held = lock.acquire(blocking=blocking, timeout=timeout)
    if held:
        try:
            yield lock
        finally:
            lock.release()
    else:
        raise TimeoutError(f"Timeout occurred while waiting for lock '{lock}'")


def wait_if_locked(timeout):
    """
    Tries to acquire a lock within a specified timeout before running decorated function
    :param int timeout: Timeout to wait for (in seconds)
    :return:
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            locks = set(arg for arg in args if isinstance(arg, type(Lock())))

            func_args = tuple(arg for arg in args if arg not in locks)

            if locks is None:
                raise ValueError("No Lock objects found in arguments.")

            with ExitStack() as stack:
                for lock in locks:
                    stack.enter_context(acquire(lock, timeout=timeout))
                result = func(*func_args, **kwargs)

            return result

        return wrapper

    return decorator


class TagType(enum.Enum):
    SPOTIFY = 0
    FINGERPRINTER = 1
    METADATA = 2


def file_generator(search: Path) -> (Path, Path):
    for root, _, files in os.walk(search):
        for file in files:
            yield Path(root), Path(file)


def get_file_count(path, pbar=None):
    """
    Recursively get the count of files in a directory, including files in subdirectories
    :param Path path: Path to start searching
    :param tqdm pbar: tqdm pbar to use for displaying progress
    :return:
    """
    file_count = 0
    if pbar is None:
        pbar = tqdm(desc="Scanning Search Directory", unit=" file")

    for entry in os.scandir(path):
        if entry.is_file():
            file_count += 1
            pbar.update(1)
        elif entry.is_dir():
            file_count += get_file_count(Path(entry.path), pbar)
    return file_count


def pool_callback(result, pbar):
    pbar.update()
    if result:
        logging.warning(result)


def save_metadata(tagger: Tagger):
    """
    Saves the metadata of a Tagger object, attempting to mitigate exceptions
    :param Tagger tagger: Tagger object to save
    :return: None
    """
    retries = 3
    for _ in range(retries):
        try:
            tagger.save()
            break
        except mutagen.MutagenError:
            time.sleep(random.randint(1, 3))
        except Exception as e:
            logging.exception(f"EXP - Saving Metadata: {e} -> {tagger.tagger}")
    else:
        try:
            tagger.save()
        except mutagen.MutagenError as e:
            logging.exception(f"Unhandled MutagenError {e}")


class MPORG:
    """
    Main class for organizing files
    """
    def __init__(
        self,
        store: Path,
        search: Path,
        searcher: SpotifySearcher,
        fingerprinters: list[Fingerprinter],
        pattern: list,
        lyrics: bool,
    ):
        self.search = search
        self.store = store
        self.sh = searcher
        self.af = fingerprinters
        self.file_locks = {}
        self.executor = ThreadPoolExecutor()
        self.pattern = pattern
        self.get_lyrics = lyrics
        self.lyric_semaphore = threading.Semaphore(5)

    def process_file(self, args):
        """
        Process a single file
        :param args:  Tuple of root and file
        :return str:  Error Messages
        """
        root, file = args
        try:
            logging.info(f"Organizing: {str(root / file)}")
            path = root / file
            try:
                metadata = Tagger(path)
            except mutagen.MutagenError:
                metadata = {}
            except Exception as e:
                logging.exception(f"EXP - Loading Metadata: {e} {path}")
                raise e

            results, tags_from = self.get_metadata(metadata, path)
            location = self.get_location(results, tags_from, metadata, file)

            source_lock = self.get_lock(path)
            destination_lock = self.get_lock(location)
            self.copy_file(source_lock, destination_lock, path, location)

            lock = self.get_lock(location)
            if tags_from == TagType.SPOTIFY:
                self.update_metadata_from_spotify(lock, location, results)
            elif tags_from == TagType.FINGERPRINTER:
                self.update_metadata_from_fingerprinter(lock, location, results)

            if self.get_lyrics:
                with self.lyric_semaphore:
                    self.save_lyrics(location)

            return None
        except ValueError as e:
            # logging.exception(e)
            return f"Error processing file {file}: {e}"
        except Exception as e:
            logging.exception(e)
            return f"Unknown Exception processing file {os.path.join(root, file)}\n EXP {e}"

    def organize(self):
        """
        Organize all files in the search directory
        :return:
        """
        logging.top("Organizing files...")
        file_count = get_file_count(self.search)

        with tqdm(desc="Organizing", total=file_count, unit="file", miniters=0) as pbar:
            futures = []
            for root, file in file_generator(self.search):
                if file.suffix.lower() not in SUPPORTED_FILETYPES:  # Skip all unrecognized files straight away
                    logging.info(f"{str(file)} has unsupported type")
                    pbar.update(1)
                    continue
                if (
                    not self.pattern or self.pattern
                    and any(item in file.suffix for item in self.pattern)
                ):  # Check pattern
                    future = self.executor.submit(self.process_file, (root, file))
                    future.add_done_callback(lambda f: pool_callback(f.result(), pbar))
                    futures.append(future)
                else:
                    logging.info(f"{str(file)} does not match any pattern {self.pattern}")
                    pbar.update(1)
            wait(futures)

        logging.top("Organizing files finished.")

    def get_metadata(self, metadata: Tagger, file: Path):
        """
        Try to get metadata from Spotify, Audio Fingerprinting, or fall back to metadata provided by the file
        :param metadata: tagger object with original metadata of file
        :param file: Path of origin file
        :return: Tuple of metadata results and the source of the metadata
        """
        url_locs = []
        for url in (metadata.get("comment"), metadata.get("commentNULL"), metadata.get("commentENG"), metadata.get("source"), metadata.get("url")):
            url_locs.append(url)

        if spot_id := get_valid_spotify_url(url_locs):
            logging.info(f"A spotify Url was found in {file} metadata. Searching via id")
            spotify_results = self.get_fingerprint_spotify_metadata(spot_id)
            return spotify_results, TagType.SPOTIFY
        artist = ["".join(u.replace("\x00", "").split("/"))
            for u in metadata.get("artist", "")]  # Replace Null Bytes
        title = [u.replace("\x00", "") for u in metadata.get("title", "")]
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
                        fingerprint_results.results.get("spotifyid")
                    )
                    if spotify_results:
                        logging.info(
                            f"Metadata found using audio fingerprinting and Spotify for ID:"
                            f" {fingerprint_results.results.get('spotifyid')}"
                        )
                        logging.debug(spotify_results)
                        return spotify_results, TagType.SPOTIFY
                else:
                    logging.info(
                        f"Metadata found using audio fingerprinting: {fingerprint_results.results.track_name}"
                        f" by {fingerprint_results.results.track_artists}"
                    )
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

    def get_location(
        self, results: Track, tags_from: TagType, metadata: Tagger, file: Path
    ) -> Path:
        """
        Determine the correct location to move the file based on metadata results and source
        :param Path file: Path for original file
        :param results: Track Object containing Metadata
        :param tags_from: Source of Tags
        :param metadata: # Tagger object containing origin file tags
        :return: The path of the destination file
        """
        ext = file.suffix
        if tags_from == TagType.SPOTIFY:
            return self.spotify_location(results, ext)
        elif tags_from == TagType.FINGERPRINTER:
            return self.fingerprinter_location(results, ext)
        elif tags_from == TagType.METADATA:
            return self.metadata_location(metadata, ext, file)

    def spotify_location(self, results: Track, ext: str) -> Path:
        album_artist, album_name, track_artist, track_name = _sanitize_results(
            self.store, results
        )

        return (
            self.store
            / album_artist
            / f"{results.album_year} - {album_name.strip()}"
            / f"{results.track_number}. - {track_artist} - {track_name}{ext}"
        )

    def fingerprinter_location(self, results: Track, ext: str) -> Path:
        album_artist, album_name, track_artist, track_name = _sanitize_results(
            self.store, results
        )

        return (
            self.store
            / album_artist
            / (
                f"{results.track_year} - " + f"{album_name}"
                if results.track_year
                else f"{album_name}"
            )
            / f"{track_artist} - {track_name}{ext}"
        )

    def metadata_location(
        self, metadata: Tagger, file_extension: str, file: Path
    ) -> Path:
        title = metadata.get("title")
        artist = metadata.get("artist")
        album = metadata.get("album")

        if not all((title, artist, album)):
            logging.warning(
                f"Cannot find enough metadata to organize '{str(file)}' ..."
            )
            return self.store / "_TaggingImpossible" / file

        track_artist = ", ".join(artist).strip()
        year = "".join(metadata.get("date", "")).strip()
        album = "".join(metadata.get("album", "")).strip()
        track = "".join(metadata.get("title", "")).strip()
        track_num = "".join(metadata.get("tracknumber", ["1"]))
        artist = [a.replace("/", ", ").strip() for a in metadata.get("artist", [])]
        # MP4 files get artists as '/' separated strings, split them apart here
        # If the artist name actually has '/', sorry

        if (
            title
            and artist
            and metadata.get("album")
            and not metadata.get("albumartist")
        ):
            album_artist = ", ".join(artist).strip()  # Use artist instead
        else:
            album_artist = ", ".join(metadata.get("albumartist", [])).strip()

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
            if isinstance(
                track_num, str
            ):  # Prob in form num / total so remove the /total
                parts.append(
                    f"{int(_remove_invalid_path_chars(track_num.split('/')[0]))}."
                )
            else:
                parts.append(f"{track_num}.")
        if track_artist and track_artist != "Unknown":
            parts.append(_remove_invalid_path_chars(track_artist))
        if track:
            parts.append(_remove_invalid_path_chars(track))

        path /= f'{" - ".join(parts)}{file_extension}'
        return path

    @wait_if_locked(10)
    def copy_file(self, source: Path, destination: Path) -> None:
        """
        Copy the file from the source location to the destination location
        :param source:
        :param destination:
        :return:
        """
        if not os.path.exists(destination):
            logging.info(f"Copying {source} to {destination}")

            retries = 3  # Maximum number of retries
            for _ in range(retries):
                try:
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

    @wait_if_locked(10)
    def update_metadata_from_spotify(self, location: Path, results: Track) -> None:
        """
        Update file metadata with Spotify results
        :param Path location: location of file to update
        :param Track results: Track information returned by Spotify
        :return: None
        :raises Exception: Error getting or saving track info
        """

        try:
            metadata = Tagger(location)
        except Exception as e:
            logging.exception(f"Error getting metadata for update {e} ")
            raise e
        metadata.set("title", results.track_name)
        metadata.set("artist", results.track_artists)
        metadata.set("album", results.album_name)
        metadata.set("date", results.album_year)
        metadata.set("tracknumber", str(results.track_number))
        metadata.set("comment", results.track_url, lang="XXX", desc="Spotify URL")
        metadata.set("source", results.track_url)
        metadata.set("albumartist", results.album_artists)
        try:
            metadata.set("bpm", results.track_bpm)
        except TypeError:
            pass
        try:
            metadata.set("initialkey", results.track_key)
        except TypeError:
            pass

        metadata.set("genre", results.album_genres)

        # TODO: Add album art for all types


        save_metadata(metadata)

    @wait_if_locked(10)
    def update_metadata_from_fingerprinter(
        self, location: Path, results: Track
    ) -> None:
        """
        Update file metadata with the fingerprinter's results
        :param Path location: location of file to update
        :param Track results: Track information returned by the fingerprinter
        :return: None
        :raises Exception: Error getting or saving track info
        """
        try:
            metadata = Tagger(location)
        except Exception as e:
            logging.exception(f"Error getting metadata for update {e} ")
            raise e
        metadata.set("title", results.track_name)
        metadata.set("artist", results.track_artists)
        metadata.set("albumartist", results.album_artists)
        try:
            metadata.set("album", results.album_name)
        except ValueError:
            pass
        try:
            metadata.set("date", results.album_year)
        except ValueError:
            pass
        try:
            metadata.set("tracknumber", str(results.track_number))
        except ValueError:
            pass

        save_metadata(metadata)

    def save_lyrics(self, location: Path):
        """
        Search for a songs lyrics. Save the lyrics alongside the file if it is found
        :param Path location: Path to file to search for lyrics for
        :return: None
        :raises Timout Error: - Timout Occurred writing lyrics
        :raises Exception: - An Unspecified Error occurred obtaining lyrics
        """
        # Get Lyrics if available
        lock = self.get_lock(location)

        retry_limit = 5
        retry_delay = 2  # seconds

        lyrics = None
        t = None
        for _ in range(retry_limit):
            try:
                logging.info(f"Searching for lyrics for {location}")
                t, lyrics = search_lyrics_by_file(location, lrc=True)
                break
            except Exception as e:
                logging.info(f"{e}, {_}")
                time.sleep(retry_delay)
                if _ >= retry_limit - 1:
                    raise e
                continue

        if not lyrics:
            return None

        logging.info(f"Lyrics found for {location}. Type {t}.")
        lyric_file = location.parent
        filename = location.stem
        destination = lyric_file / (filename + "." + t)

        destination_lock = self.get_lock(destination)

        if (lyric_file / (filename + ".txt")).exists() or (
            lyric_file / (filename + ".lrc")
        ).exists():
            txt = lyric_file / (filename + ".txt")
            lrc = lyric_file / (filename + ".lrc")
            existing = (txt, lrc)

            for file in existing:
                if file.exists():
                    logging.info(
                        f"A lyrics file already exists for {location}, check if current."
                    )
                    with open(file, "r", encoding="utf-8") as f:
                        if not lyrics == f.read():
                            logging.info(f"Deleting {file}")
                            try:
                                file.unlink()
                            except Exception as e:
                                logging.exception(e)
                                logging.error("Error Unlinking file. Try to Ignore")
                        else:
                            logging.info(f"{file} is current")
                            return

        for _ in range(retry_limit):
            try:
                logging.info(f"Writing Lyrics file: {destination}")
                with acquire(destination_lock, timeout=30):
                    with open(destination, "w", encoding="utf-8") as f:
                        f.write(lyrics)

                return  # File operations completed successfully, exit the function

            except TimeoutError:
                # Lock acquisition timed out
                time.sleep(retry_delay)
                continue

                # Retry limit reached for destination lock, file operations failed
        logging.error(f"Failed to acquire destination lock for {destination}")

        # Retry limit reached for location lock, file operations failed
        # logging.error(f"Failed to acquire location lock for {location}")


def _remove_invalid_path_chars(s: str) -> str:
    """Helper function to remove invalid characters from a string."""
    return "".join(c for c in s if c not in INVALID_PATH_CHARS)


def _sanitize_results(root: Path, results: Track) -> (str, str, str, str):
    """
    # Sanitize the strings and limit the total length of the sanitized results to a size which fits in MATH_PATH
    # for the current system. (Works for Unix & Windows)
    # Keep in mind the max FILENAME is 255 chars for Unix though the max PATH is 4096, so unless the root is massive
    # 99% of the path should be unused
    :param results: Track object to parse
    :return: tuple of sanitized and truncated album_artist, album_name, track_artist, track_name
    """

    # Get Path max and File max

    if sys.platform == "linux":  # Use Linux stuff:
        path_max = os.pathconf("/", "PC_PATH_MAX")
    else:  # Assume Windows as it has a lower path max
        from ctypes.wintypes import MAX_PATH

        path_max = MAX_PATH

    path_max -= 5  # Buffer for ceil function
    path_max -= len(str(root))  # Subtract length of store root from the max.

    max_segment = 255 // 2 - 7

    # Calculate maximum lengths for artist and name segments
    segment_max = ceil(path_max * 0.20)
    artist_max = min(max_segment, segment_max)

    segment_max = ceil(path_max * 0.30)
    name_max = min(max_segment, segment_max)

    """
    Paths are organized as such
    [Store root][Artist][Album info][Track info]
    
    Then give 20% to each artist block
    and 30% to the album and track block
    """
    album_artist = ", ".join(results.album_artists)
    track_artist = ", ".join(results.track_artists)

    track_artist = _remove_invalid_path_chars(track_artist)[:artist_max].strip()
    album_artist = _remove_invalid_path_chars(album_artist)[:artist_max].strip()

    album_name = _remove_invalid_path_chars(results.album_name)[:name_max].strip()
    track_name = _remove_invalid_path_chars(results.track_name)[:name_max].strip()

    # Calculate the total length of the sanitized results
    total_length = (
        len(album_artist) + len(track_artist) + len(album_name) + len(track_name)
    )

    # If the total length exceeds path_max, truncate the longest string(s)
    if total_length > path_max:
        while total_length > path_max:
            if len(album_name) > len(track_name):
                album_name = album_name[:-1].strip()
            else:
                track_name = track_name[:-1].strip()
            total_length = (
                len(album_artist)
                + len(track_artist)
                + len(album_name)
                + len(track_name)
            )

    return album_artist, album_name, track_artist, track_name


def get_valid_spotify_url(strings):
    spotify_track_url = "https://open.spotify.com/track/"

    for string in strings:
        if string and spotify_track_url in "".join(string):
            track_id = "".join(string).replace(spotify_track_url, "")
            track_id = track_id.split("?")[0]  # Remove any trailing params
            return track_id

    return None
