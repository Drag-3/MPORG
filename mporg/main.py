import logging
import os
import sys
import json
from argparse import ArgumentParser
from pathlib import Path

from mporg import CONFIG_DIR, VERSION
from mporg.organizer import MPORG
from mporg.audio_fingerprinter import ACRFingerprinter, MBFingerprinter
from mporg.spotify_searcher import SpotifySearcher
from mporg.logging_utils.logging_setup import setup_logging


def get_credentials(use_acr: bool = False, use_mb: bool = False):
    credential_path = CONFIG_DIR / "credentials.json"
    acrcloud_path = CONFIG_DIR / "acrcloud.json"
    acoustid_path = CONFIG_DIR / "acoustid.json"

    if not CONFIG_DIR.exists():
        os.mkdir(CONFIG_DIR)
        logging.debug(f"Creating {CONFIG_DIR}")

    if not credential_path.exists():
        credential_path.touch(0o666)
        logging.debug(f"Creating {credential_path}")

    if not acrcloud_path.exists():
        acrcloud_path.touch(0o666)
        logging.debug(f"Creating {acrcloud_path}")

    if not acoustid_path.exists():
        acoustid_path.touch(0o700)
        logging.debug(f"Creating {acoustid_path}")

    acrdata = None
    mbdata = None
    # Attempt to get Spotify creds from file
    with open(credential_path, 'r+') as cred:
        try:
            spodata = json.load(cred)
        except json.decoder.JSONDecodeError:
            logging.debug("The JSON file is empty or invalid")
            spodata = get_spotify_credentials(cred)
    if use_acr:
        # Attempt to get ACRCloud creds from file
        with open(acrcloud_path, 'r+') as acrcred:
            try:
                acrdata = json.load(acrcred)
            except json.decoder.JSONDecodeError:
                logging.debug("The JSON file is empty or invalid")
                acrdata = get_acrcloud_credentials(acrcred)
    if use_mb:
        # Attempt to get AcoustID Api Key from file
        with open(acoustid_path, 'r+') as acoust:
            try:
                mbdata = json.load(acoust)
            except json.decoder.JSONDecodeError:
                logging.debug("The JSON file is empty or invalid")
                mbdata = get_acoustid_credentials(acoust)

    # Return both sets of credentials
    return spodata, acrdata, mbdata


def get_acoustid_credentials(cred):
    print("Getting AcoustID Credentials. Enter q to skip this fingerprinter..")
    while True:
        api_key = input("Enter your AcoustID API Key: ")
        if api_key.lower() == "q":
            return None
        elif len(api_key) > 0:
            break
        else:
            print("Invalid access key. Please try again.")

    data = {"api": api_key}

    try:
        cred.seek(0)
        cred.truncate()
        json.dump(data, cred)
    except Exception as e:
        logging.exception(f"Error writing to file: {e}")

    return data


def get_spotify_credentials(cred):
    # Ask user for Spotify credentials
    print("Getting Spotify Credentials.")

    cid = input("Enter your Spotify Client ID: ")
    secret = input("Enter your Spotify Client Secret: ")
    data = {"cid": cid, "secret": secret}

    try:
        cred.seek(0)
        cred.truncate()
        json.dump(data, cred)
    except Exception as e:
        logging.exception(f"Error writing to file: {e}")
    return data


def get_acrcloud_credentials(acrcred):
    # Ask user for ACRCloud credentials
    print("Getting ACRCloud Credentials. Enter q to skip this fingerprinter..")
    while True:
        host = input("Enter the ACRCloud host: ")
        if host.lower() == "q":
            return None
        elif ".acrcloud.com" in host:
            break
        else:
            print("Invalid URL. Please try again.")

    while True:
        key = input("Enter your ACRCloud access key: ")
        if key.lower() == "q":
            return None
        elif len(key) > 0:
            break
        else:
            print("Invalid access key. Please try again.")

    while True:
        secret = input("Enter your ACRCloud access secret: ")
        if secret.lower() == "q":
            return None
        elif len(secret) > 0:
            break
        else:
            print("Invalid access secret. Please try again.")

    data = {"host": host, "key": key, "access_key": key, "access_secret": secret, "secret": secret, "debug": False,
            "timeout": 10}
    try:
        acrcred.seek(0)
        acrcred.truncate()
        json.dump(data, acrcred)
    except Exception as e:
        logging.exception(f"Error writing to file: {e}")

    return data


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show the version of MPORG.", action="store_true")
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

    spotify_creds, acrcloud_creds, mbid = get_credentials(use_acr=args.acrcloud or args.fingerprint,
                                                          use_mb=args.music_brainz or args.fingerprint)
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
