import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from mporg import VERSION
from mporg.audio_fingerprinter import ACRFingerprinter, MBFingerprinter
from mporg.credentials.credentials_manager import CredentialManager
from mporg.logging_utils.logging_setup import setup_logging
from mporg.organizer import MPORG
from mporg.spotify_searcher import SpotifySearcher


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show the version of MPORG and exit.", action="store_true")
    arg_parser.add_argument("-l", "--log_level", help="Logging level for the console screen", type=int, default=3)
    arg_parser.add_argument("-a", "--acrcloud", help="Use Acrcloud for audio fingerprinting.", action="store_true")
    arg_parser.add_argument("-m", "--music_brainz", help="Use Musicbrainz for audio fingerprinting.", action="store_true")
    arg_parser.add_argument("-f", "--fingerprint", help="Use all fingerprinters (same as -am).", action="store_true")

    arg_parser.add_argument("store_path", default=Path.home() / os.path.join("Music", "TuneTagLibrary"),
                            help="Root of area to store organized files", nargs='?')
    arg_parser.add_argument("search_path", default=Path.cwd(), help="Source dir to look for mp3 files in.", nargs='?')

    args = arg_parser.parse_args()

    setup_logging(args.log_level)
    logging.debug(args)

    if args.version:
        print(VERSION)
        sys.exit(0)

    cred_manager = CredentialManager()
    credentials = cred_manager.get_credentials(use_acr=args.acrcloud or args.fingerprint,
                                                          use_mb=args.music_brainz or args.fingerprint)
    spotify_creds = credentials.get('Spotify')
    acrcloud_creds = credentials.get("ACRCloud")
    mbid = credentials.get('AcoustID')

    spotify_searcher = SpotifySearcher(spotify_creds["cid"], spotify_creds["secret"])

    fingerprinters = []
    if args.acrcloud or args.fingerprint:
        fingerprinters.append(ACRFingerprinter(acrcloud_creds))
    if args.music_brainz or args.fingerprint:
        fingerprinters.append(MBFingerprinter(mbid['api']))

    logging.info("All good, starting Organizing")
    org = MPORG(Path(args.store_path), Path(args.search_path), spotify_searcher, fingerprinters)
    org.organize()


if __name__ == "__main__":
    main()
