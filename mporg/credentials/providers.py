import json
import logging

import requests
from acrcloud.recognizer import ACRCloudRecognizer

import mporg

logging.getLogger("__main__." + __name__)
logging.propagate = True


class CredentialProvider:
    SPEC = {}

    def __init__(self, credential_file):
        self.credential_file = credential_file

    def verify_spec(self, credentials):
        for key, value in self.SPEC.items():
            if not value(credentials.get(key, "")):
                logging.warning(f"Invalid {key}.")
                return False
        return True

    def verify_credentials(self, credentials):
        raise NotImplementedError(
            "Subclasses must implement verify_credentials(), Return True if verification "
            "impossible"
        )

    def _load_from_file(self):
        data = {}
        try:
            with open(self.credential_file, "r+", encoding="utf-8") as cred:
                try:
                    data = json.load(cred)
                except json.decoder.JSONDecodeError:
                    logging.debug("The JSON file is empty or invalid")
        except FileNotFoundError:
            logging.info("Credentials File not found")
        return data

    def get_credentials(self):
        raise NotImplementedError("Subclasses must implement get_credentials()")

    def store_credentials(self, credentials):
        with open(self.credential_file, "w", encoding="utf-8") as file:
            json.dump(credentials, file)


class SpotifyCredentialProvider(CredentialProvider):
    SPEC = {"cid": lambda x: len(x) > 0, "secret": lambda x: len(x) > 0}
    PNAME = "Spotify"

    def get_credentials(self):
        # Try to get and verify credentials
        credentials = self._load_from_file()
        if (
            credentials
            and self.verify_spec(credentials)
            and self.verify_credentials(credentials)
        ):
            return credentials

        # Ask user for Spotify credentials
        logging.top("Getting Spotify Credentials.")
        while (
            not credentials
            or not self.verify_spec(credentials)
            or not self.verify_credentials(credentials)
        ):
            cid = input("Enter your Spotify Client ID: ")
            secret = input("Enter your Spotify Client Secret: ")
            credentials = {"cid": cid, "secret": secret}
        self.store_credentials(credentials)

        return credentials

    def verify_credentials(self, credentials):
        url = "https://accounts.spotify.com/api/token"
        client_id = credentials.get("cid")
        client_secret = credentials.get("secret")
        headers = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            auth_response = requests.post(url, headers)
            auth_response.raise_for_status()
            logging.top("Spotify credentials are valid.")
            return True
        except requests.exceptions.RequestException as e:
            logging.warning("Spotify credentials are invalid:", str(e))
            return False


class ACRCloudCredentialProvider(CredentialProvider):
    SPEC = {
        "host": lambda x: ".acrcloud.com" in x,
        "access_key": lambda x: len(x) > 0,
        "access_secret": lambda x: len(x) > 0,
    }
    PNAME = "ACRCloud"

    def get_credentials(self):
        # Try to get and verify credentials
        credentials = self._load_from_file()
        if (
            credentials
            and self.verify_spec(credentials)
            and self.verify_credentials(credentials)
        ):
            return credentials

        # Ask user for ACRCloud credentials
        print("Getting ACRCloud Credentials. Enter q to skip this fingerprinter..")
        while (
            not credentials
            or not self.verify_spec(credentials)
            or not self.verify_credentials(credentials)
        ):
            host = input("Enter the ACRCloud host: ")
            if host.lower() == "q":
                return None

            key = input("Enter your ACRCloud access key: ")
            if key.lower() == "q":
                return None

            secret = input("Enter your ACRCloud access secret: ")
            if secret.lower() == "q":
                return None

            credentials = {
                "access_key": key,
                "access_secret": secret,
                "secret": secret,
                "debug": False,
                "timeout": 10,
            }

        return credentials

    def verify_credentials(self, credentials):
        config = credentials
        recognizer = ACRCloudRecognizer(config)

        try:
            # Use a dummy fingerprint
            dummy_fingerprint = {"sample": b"A"}

            # Use the do_recogize() method to verify credentials
            result = recognizer.do_recogize(
                config.get("host"),
                dummy_fingerprint,
                "fingerprint",
                config.get("access_key"),
                config.get("access_secret"),
                10,
            )

            result = json.loads(result)
            if (
                result["status"]["code"] == 1001
                and result["status"]["msg"] == "No result"
            ):
                logging.top("ACRCloud credentials are valid.")
                return True
            else:
                logging.warning(
                    "ACRCloud credentials are invalid:", result["status"]["msg"]
                )
                return False
        except Exception as e:
            logging.warning(
                "Error occurred while verifying ACRCloud credentials:", str(e)
            )
            return False



if __name__ == "__main__":
    spotify = SpotifyCredentialProvider(mporg.CONFIG_DIR / "spotify.json")
    acrcloud = ACRCloudCredentialProvider(mporg.CONFIG_DIR / "acrcloud.json")

    print(spotify.get_credentials())
    print(acrcloud.get_credentials())
