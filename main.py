import os
import sys
from argparse import ArgumentParser
import json
from pathlib import Path

from audio_fingerprinter import ACRFingerprinter, MBFingerprinter
from spotify_searcher import SpotifySearcher, SpotifyOauthError
from organizer import MPORG
import logging
from logging.handlers import RotatingFileHandler
import validators



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


class ColoredFormatter(logging.Formatter):
    """
    A formatter that adds color to the log output.
    """

    def format(self, record):
        if record.levelno == logging.DEBUG:
            record.levelname = f"\033[34m{record.levelname}\033[0m"
        elif record.levelno == logging.INFO:
            record.levelname = f"\033[32m{record.levelname}\033[0m"
        elif record.levelno == logging.WARNING:
            record.levelname = f"\033[33m{record.levelname}\033[0m"
        elif record.levelno == logging.ERROR:
            record.levelname = f"\033[31m{record.levelname}\033[0m"
        elif record.levelno == logging.CRITICAL:
            record.levelname = f"\033[35m{record.levelname}\033[0m"
        return super().format(record)


class ColorHandler(logging.StreamHandler):
    # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
    GRAY8 = "38;5;8"
    GRAY7 = "38;5;7"
    ORANGE = "33"
    RED = "31"
    WHITE = "0"

    def emit(self, record):
        # Don't use white for any logging, to help distinguish from user print statements
        level_color_map = {
            logging.DEBUG: self.GRAY8,
            logging.INFO: self.GRAY7,
            logging.WARNING: self.ORANGE,
            logging.ERROR: self.RED,
        }

        csi = f"{chr(27)}["  # control sequence introducer
        color = level_color_map.get(record.levelno, self.WHITE)

        print(f"{csi}{color}m{self.format(record)}{csi}m")


def set_logging(v: bool):
    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if v else logging.INFO)

    # Create a formatter
    c_formatter = ColoredFormatter('%(asctime)s - %(module)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s - %(message)s')
    # Create a file handler and set the formatter
    file_handler = RotatingFileHandler('MPORG.log', maxBytes=1000000, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if v else logging.INFO)
    file_handler.setFormatter(formatter)

    # Create a console handler and set the formatter
    console_handler = ColorHandler()
    console_handler.setLevel(logging.DEBUG if v else logging.WARNING)
    console_handler.setFormatter(c_formatter)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def get_credentials(use_acr: bool = False, use_mb: bool = False):
    usr_home = Path.home()
    config_folder = usr_home / ".MP3ORG"
    credential_path = config_folder / "credentials.json"
    acrcloud_path = config_folder / "acrcloud.json"
    acoustid_path = config_folder / "acoustid.json"

    if not config_folder.exists():
        os.mkdir(config_folder)
        logging.debug(f"Creating {config_folder}")

    if not credential_path.exists():
        credential_path.touch(0o666)
        logging.debug(f"Creating {credential_path}")

    if not acrcloud_path.exists():
        acrcloud_path.touch(0o666)
        logging.debug(f"Creating {acrcloud_path}")

    if not acoustid_path.exists():
        acoustid_path.touch(0o666)
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
        elif validators.url(host):
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

    data = {"host": host, "key": key, "secret": secret, "debug": False, "timeout": 10}
    try:
        acrcred.seek(0)
        acrcred.truncate()
        json.dump(data, acrcred)
    except Exception as e:
        logging.exception(f"Error writing to file: {e}")

    return data


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--version", help="Show Version", action="store_true")
    arg_parser.add_argument("-V", "--verbose", help="Print", action="store_true")
    arg_parser.add_argument("-a", "--acrcloud", help="Use Acrcloud", action="store_true")
    arg_parser.add_argument("-m", "--music_brainz", help="Use Musicbrainz", action="store_true")
    arg_parser.add_argument("-f", "--fingerprint", help="Use all fingerprinters. (Same as -am)", action="store_true")

    arg_parser.add_argument("store_path", default=Path.home() / os.path.join("Music", "TuneTagLibrary"),
                            help="Root of area to store organized files")
    arg_parser.add_argument("search_path", default=Path.cwd(),  help="Source dir to look for mp3 files in.")

    args = arg_parser.parse_args()
    set_logging(args.verbose)
    logging.debug(args)

    if args.version:
        print("V.0.1.0.1.1.0")
        sys.exit(0)

    spotify_creds, acrcloud_creds, mbid = get_credentials(use_acr=args.acrcloud or args.fingerprint,
                                                          use_mb=args.music_brainz or args.fingerprint)
    spotify_searcher = SpotifySearcher(spotify_creds["cid"], spotify_creds["secret"])

    fingerprinters = []
    if args.acrcloud or args.fingerprint:
        fingerprinters.append(ACRFingerprinter(acrcloud_creds))
    if args.music_brainz or args.fingerprint:
        fingerprinters.append(MBFingerprinter(mbid))


    logging.info("All good, starting Organizing")
    org = MPORG(Path(args.store_path), Path(args.search_path), spotify_searcher, fingerprinters)
    org.organize()


if __name__ == "__main__":
    main()
