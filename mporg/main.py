import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from mporg import VERSION
from mporg.audio_fingerprinter import ACRFingerprinter, MBFingerprinter, get_fingerprinter
from mporg.credentials.credentials_manager import CredentialManager
from mporg.logging_utils.logging_setup import setup_logging
from mporg.organizer import MPORG
from mporg.spotify_searcher import SpotifySearcher


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show the version of MPORG and exit.", action="store_true")
    arg_parser.add_argument("-l", "--log_level", help="Logging level for the console screen", type=int, default=3)
    arg_parser.add_argument("-a", "--acrcloud", help="Use Acrcloud for audio fingerprinting.", action="store_true")
    arg_parser.add_argument("-m", "--music_brainz", help="Use Musicbrainz for audio fingerprinting.",
                            action="store_true")
    arg_parser.add_argument("-f", "--fingerprint", help="Use all fingerprinters (same as -am).", action="store_true")
    arg_parser.add_argument("-p", "--pattern_extension", help="Extension(s) to copy over, space separated",
                            default=[], nargs="*")
    arg_parser.add_argument("-y", "--lyrics", help="Attempt to get lyrics and store with file", action="store_true")

    arg_parser.add_argument("store_path", default=Path.home() / os.path.join("Music", "TuneTagLibrary"),
                            help="Root of area to store organized files", nargs='?')
    arg_parser.add_argument("search_path", default=Path.cwd(), help="Source dir to look for mp3 files in.", nargs='?')

    args = arg_parser.parse_args()

    setup_logging(args.log_level)
    logging.debug(args)

    print(args.pattern_extension)

    if args.version:
        print(VERSION)
        sys.exit(0)

    cred_manager = CredentialManager()
    credentials = cred_manager.get_credentials(use_acr=args.acrcloud or args.fingerprint,
                                               use_mb=args.music_brainz or args.fingerprint)
    spotify_creds = credentials.pop('Spotify')

    spotify_searcher = SpotifySearcher(spotify_creds["cid"], spotify_creds["secret"])

    fingerprinters = [get_fingerprinter(x[0], x[1]) for x in credentials.items() if x[1] is not None]

    logging.info("All good, starting Organizing")
    org = MPORG(Path(args.store_path), Path(args.search_path), spotify_searcher, fingerprinters, args.pattern_extension,
                args.lyrics)
    org.organize()


if __name__ == "__main__":
    main()
