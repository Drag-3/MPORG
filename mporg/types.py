import logging
from dataclasses import dataclass
from pathlib import Path

import mutagen
from mutagen.asf import ASF, ASFUnicodeAttribute
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.wave import WAVE


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


class Tagger:
    """
    Wrapper class for mutagen objects, to provide consistent api for any filetype
    Take care to only use valid tags for each type
    """

    def __init__(self, file: Path):
        # Register Non-Standard Keys for Easy
        register_comment()
        EasyID3.RegisterTextKey("initialkey", "TKEY")
        EasyID3.RegisterTextKey("source", "WOAS")
        EasyMP4.RegisterTextKey("source", "source")
        EasyMP4.RegisterTextKey("initialkey", "----:com.apple.iTunes:initialkey")

        # Determine mutagen object to use
        self.extension = file.suffix
        if self.extension.lower() == ".mp3":
            try:
                self.tagger = EasyID3(file)
            except ID3NoHeaderError:
                self.tagger = mutagen.File(file, easy=True)
                self.tagger.add_tags()

        elif self.extension.lower() == ".m4a":
            self.tagger = EasyMP4(file)
        elif self.extension.lower() == ".wav":
            self.tagger = WAVE(file)
        elif self.extension.lower() in [".wma"]:
            self.tagger = ASF(file)
        elif self.extension.lower() == ".flac":
            self.tagger = FLAC(file)
        elif self.extension.lower() in [".ogg", ".oga"]:
            self.tagger = mutagen.File(file)  # Cannot tell if Opus Vorbis or other based on extension alone.
        else:
            logging.warning(f"{file} has invalid extension {self.extension}")
            raise ValueError("Invalid Extension")

    def get(self, key, value=None):
        result = self.tagger.get(key, value)
        if self.extension.lower() == ".wma":
            if isinstance(result, list):
                # Convert each item in the list to string as ASF/WMA uses special Values
                result = [str(item) for item in result]
            elif isinstance(result, ASFUnicodeAttribute):
                # If it's an ASFUnicodeAttribute, extract the string value
                result = str(result)

        return result

    def __getitem__(self, item):
        result = self.tagger.__getitem__(item)
        if self.extension.lower() == ".wma":
            if isinstance(result, list):
                # Convert each item in the list to string as ASF/WMA uses special Values
                result = [str(item) for item in result]
            elif isinstance(result, ASFUnicodeAttribute):
                # If it's an ASFUnicodeAttribute, extract the string value
                result = str(result)

        return result

    def __setitem__(self, key, value):
        self.tagger.__setitem__(key, value)

    def add_tags(self):
        self.tagger.add_tags()

    def save(self):
        self.tagger.save()


def register_comment(lang='\0\0\0', desc=''):
    """Register the comment tag"""
    frame_id = ':'.join(('COMM', desc, lang))

    def getter(id3, _key):
        frame = id3.get(frame_id)
        return None if frame is None else list(frame)

    def setter(id3, _key, value):
        id3.add(mutagen.id3.COMM(
            encoding=3, lang=lang, desc=desc, text=value))

    def deleter(id3, _key):
        del id3[frame_id]

    EasyID3.RegisterKey('comment', getter, setter, deleter)
