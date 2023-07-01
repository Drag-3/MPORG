import logging
from dataclasses import dataclass
from pathlib import Path

import mutagen
from mutagen.asf import ASF
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.wave import WAVE


@dataclass
class Track:
    track_name: str = None
    track_number: int = None
    track_year: str = None
    track_key: str = None
    track_bpm: str = None
    track_disk: int = None
    track_artists: list = None
    album_name: str = None
    album_artists: list = None
    album_year: str = None
    album_size: int = None
    track_url: str = None
    album_genres: str = None
    track_id: str = None
    album_id: str = None


def register_comment(lang='\0\0\0', desc=''):
    "Register the comment tag"
    frameid = ':'.join(('COMM', desc, lang))

    def getter(id3, _key):
        frame = id3.get(frameid)
        return None if frame is None else list(frame)

    def setter(id3, _key, value):
        id3.add(mutagen.id3.COMM(
            encoding=3, lang=lang, desc=desc, text=value))

    def deleter(id3, _key):
        del id3[frameid]

    EasyID3.RegisterKey('comment', getter, setter, deleter)


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
        elif extension.lower() == ".flac":
            self.tagger = FLAC(file)
        elif extension.lower() in [".ogg", ".oga"]:
            self.tagger = mutagen.File(file)  # Cannot tell if Opus Vorbis or other based on extension alone.
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