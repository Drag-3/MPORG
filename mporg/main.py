import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from mporg import VERSION, CONFIG_DIR
from mporg.audio_fingerprinter import get_fingerprinter
from mporg.credentials.credentials_manager import CredentialManager
from mporg.logging_utils.logging_setup import setup_logging
from mporg.organizer import MPORG
from mporg.plugins import PLUGIN_DIR
from mporg.plugins.util import PluginType
from mporg.plugins.plugin_loader import PluginLoader
from mporg.spotify_searcher import SpotifySearcher

import mporg.plugins.util


def main():
    if not PLUGIN_DIR.exists():
        mporg.plugins.PLUGIN_DIR.mkdir(0o777, parents=True, exist_ok=True)
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show the version of MPORG and exit.", action="store_true")
    arg_parser.add_argument("-l", "--log_level", help="Logging level for the console screen", type=int, default=3)

    arg_parser.add_argument("-f", "--fingerprint", help="Use specifified Fingerprinter")
    arg_parser.add_argument("-af", "--all_fingerprint", help="Use all fingerprinter plugins")

    arg_parser.add_argument("-p", "--pattern_extension", help="Extension(s) to copy over, space separated",
                            default=[], nargs="*")
    arg_parser.add_argument("-y", "--lyrics", help="Attempt to get lyrics and store with file", action="store_true")

    arg_parser.add_argument("store_path", default=Path.home() / os.path.join("Music", "TuneTagLibrary"),
                            help="Root of area to store organized files", nargs='?')
    arg_parser.add_argument("search_path", default=Path.cwd(), help="Source dir to look for mp3 files in.", nargs='?')

    args = arg_parser.parse_args()

    setup_logging(args.log_level)
    logging.debug(args)

    if args.version:
        print(VERSION)
        sys.exit(0)

    loader = PluginLoader()
    if args.all_fingerprint:
        loader.load_all_fingerprinters()
    else:
        to_load = args.fingerprint
        try:
            loader.load_plugin(PluginType.FINGERPRINTER, to_load)
        except Exception:
            pass

    cred_manager = CredentialManager()
    for plugin in loader.fingerprinters.values():
        cred_manager.credential_providers.append(plugin.provider(CONFIG_DIR / plugin.provider.CONFIG_NAME))

    credentials = cred_manager.get_credentials()
    spotify_creds = credentials.pop('Spotify')

    spotify_searcher = SpotifySearcher(spotify_creds["cid"], spotify_creds["secret"])

    fingerprinters = [get_fingerprinter(x[0], x[1]) for x in credentials.items() if x[1] is not None]

    logging.info("All good, starting Organizing")
    org = MPORG(Path(args.store_path), Path(args.search_path), spotify_searcher, fingerprinters, args.pattern_extension,
                args.lyrics)
    org.organize()


if __name__ == "__main__":
    main()
