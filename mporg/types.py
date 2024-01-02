import logging
from dataclasses import dataclass
from pathlib import Path

import mutagen
import requests
from mutagen import File
from mutagen.asf import ASF, ASFUnicodeAttribute
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3NoHeaderError, ID3, COMM, APIC, PictureType
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4Cover
from mutagen.wave import WAVE


@dataclass(frozen=True)
class Track:
    """
    Dataclass for storing track information
    """
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
    art_url: str = None
    art_data: bytes = None

    def __post_init__(self):
        if self.art_url and not self.art_data or not isinstance(self.art_data, bytes):
            self.art_data = requests.get(self.art_url).content



def register_comment_key():
    def getter(id3, key):
        return [(frame.lang, frame.desc, frame.text[0]) for frame in id3.getall('COMM')]

    def setter(id3, key, value):
        lang, desc, text = value
        id3.add(COMM(encoding=3, lang=lang, desc=desc, text=[text]))

    def deleter(id3, info=None):
        id3.delall('COMM')
        # If it is possible I would like to delete specific comments, but I don't know how to do that yet

    EasyID3.RegisterKey('comment', getter, setter, deleter)


def register_picture_key():
    def getter(id3, key):
        return [(frame.mime, frame.desc, frame.type, frame.data) for frame in
                id3.getall('APIC')]  # Concat data if printing

    def setter(id3, key, value):
        mimetype, desc, ptype = value
        id3.add(APIC(encoding=3, mime=mimetype, type=ptype, desc=desc, data=bytes(value)))

    def deleter(id3):
        id3.delall('APIC')

    EasyID3.RegisterKey('picture', getter, setter, deleter)



class Tagger:
    """
    Wrapper class for mutagen objects, to provide consistent api for any filetype
    Take care to only use valid tags for each type
    """

    EASYID3_MAP = {
        "artist": "artist",
        "albumartist": "albumartist",
        "album": "album",
        "title": "title",
        "date": "date",
        "tracknumber": "tracknumber",
        "genre": "genre",
        "comment": "comment",
        "picture": "picture",
        # Add more mappings as needed
    }

    EASYMP4_MAP = {
        "artist": "artist",
        "albumartist": "albumartist",
        "album": "album",
        "title": "title",
        "date": "date",
        "tracknumber": "tracknumber",
        "genre": "genre",
        "comment": "comment",
        "picture": "covr",
    }

    FLAC_MAP = {
        "artist": "ARTIST",
        "albumartist": "ALBUMARTIST",
        "album": "ALBUM",
        "title": "TITLE",
        "date": "DATE",
        "tracknumber": "TRACKNUMBER",
        "genre": "GENRE",
        "comment": "COMMENT",
        "picture": "picture",  # Pictures are not stored with the rest of the tags, so I will handle it in a separate function
    }

    OGG_MAP = {
        "artist": "ARTIST",
        "albumartist": "ALBUMARTIST",
        "album": "ALBUM",
        "title": "TITLE",
        "date": "DATE",
        "tracknumber": "TRACKNUMBER",
        "genre": "GENRE",
        "comment": "COMMENT",
        "picture": "picture",  # Pictures are not stored with the rest of the tags, so I will handle it in a separate function
    }

    WAV_MAP = EASYID3_MAP

    def __init__(self, file: Path):
        # Register Non-Standard Keys for Easy
        register_comment_key()
        EasyID3.RegisterTextKey("initialkey", "TKEY")
        EasyID3.RegisterTextKey("source", "WOAS")
        EasyMP4.RegisterTextKey("source", "source")
        EasyMP4.RegisterTextKey("initialkey", "----:com.apple.iTunes:initialkey")

        # Determine mutagen object to use
        self.extension = file.suffix
        if self.extension in [".mp3", ".wav"]:
            try:
                self.tagger = EasyID3(file)
            except ID3NoHeaderError:
                self.tagger = File(file, easy=True)
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

    def set_tag(self, file_type, file_obj, tag_name, value, **kwargs):
        if file_type == 'easyid3':
            mapped_tag = Tagger.EASYID3_MAP[tag_name]
        elif file_type == 'easymp4':
            mapped_tag = Tagger.EASYMP4_MAP[tag_name]
        elif file_type == 'flac':
            mapped_tag = Tagger.FLAC_MAP[tag_name]
        elif file_type == 'ogg':
            mapped_tag = Tagger.OGG_MAP[tag_name]
        elif file_type == 'wav':
            mapped_tag = Tagger.WAV_MAP[tag_name]
        else:
            raise ValueError(f"Invalid file type {file_type}")

        file_obj[mapped_tag] = value

    def __getitem__(self, item):
        return self._postprocess_get(self.tagger.__getitem__(item))

    def get(self, key, default=None):
        return self._postprocess_get(self.tagger.get(key, default))

    def _postprocess_get(self, result):
        if self.extension.lower() == ".wma":
            if isinstance(result, list):
                # Convert each item in the list to string as ASF/WMA uses special Values
                result = [str(item) for item in result]
            elif isinstance(result, ASFUnicodeAttribute):
                # If it's an ASFUnicodeAttribute, extract the string value
                result = str(result)

        if isinstance(result, list) and len(
                result) == 1:  # If There is only one item in the list and it has a semicolon, split it
            result_str = result[0]
            if ";" in result_str:
                result = [item.strip() for item in result_str.split(";") if item.strip()]  # Remove empty strings
        return result

    def set(self, key, value, **kwargs):
        if self.extension.lower() == ".mp3":
            match key:
                case "comment":
                    desc = kwargs.get("desc", "")
                    lang = kwargs.get("lang", "XXX")
                    self.tagger[key] = (lang, desc, value)
                    return
                case "picture":
                    mime = kwargs.get("mime", "image/jpeg")
                    desc = kwargs.get("desc", "")
                    ptype = kwargs.get("type", PictureType.COVER_FRONT)
                    self.tagger[key] = (mime, desc, ptype, value)
                    return
                case _:
                    if isinstance(value, list):
                        self.tagger[key] = value
                    else:
                        self.tagger[key] = [value]
                    return
        elif self.extension.lower() == ".m4a":
            match key:
                case "picture":
                    self.tagger[key] = MP4Cover(value, MP4Cover.FORMAT_JPEG)
        elif self.extension.lower() == ".wma":
            pass
        elif self.extension.lower() == ".flac":
            match key:
                case "picture":
                    pic = Picture()
                    pic.data = value
                    pic.type = kwargs.get("type", 3)
                    pic.mime = kwargs.get("mime", "image/jpeg")
                    pic.desc = kwargs.get("desc", "")
                    pic.width = kwargs.get("width", 0)
                    pic.height = kwargs.get("height", 0)
                    self.tagger.add_picture(pic)
                    return
                case _:
                    self.tagger[key] = value
                    return
        elif self.extension.lower() == ".ogg":
            match key:
                case "picture":
                    pic = Picture()
                    pic.data = value
                    pic.type = kwargs.get("type", 3)
                    pic.mime = kwargs.get("mime", "image/jpeg")
                    pic.desc = kwargs.get("desc", "")
                    pic.width = kwargs.get("width", 0)
                    pic.height = kwargs.get("height", 0)
                    self.tagger["METADATA_BLOCK_PICTURE"] = pic.write().decode("latin-1")
                    return
        if key and value:
            return self.tagger.__setitem__(key, value)
        else:  # If key or value is None, do not set
            return

    def __setitem__(self, key, value):
        self.set(key, value)

    def _postprocess_set_value(self, key, value):
        if isinstance(value, str):
            if ";" in value:
                value = [item.strip() for item in value.split(";") if item.strip()]
            else:
                value = [value]

        return value

    def add_tags(self):
        self.tagger.add_tags()

    def save(self):
        self.tagger.save()

    def pop(self, key, *args, **kwargs):
        self.tagger.pop(key)

    def __str__(self):
        return str(self.tagger)


if __name__ == "__main__":
    # Test Tagger
    from pprint import pprint

    test_file = Path(
        "/home/justin/Music/ZSpotify Music/RHYTHM HEAVEN FEVER/Arcade Player - Construction, Red (From Rhythm.mp3")

    tagger = Tagger(test_file)
    # tagger.pop("comment")
    pprint(tagger["comment"])
    tagger.save()
    print(tagger)
