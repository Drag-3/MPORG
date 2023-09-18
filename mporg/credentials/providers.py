import json
import logging

import requests

import mporg

logging.getLogger("__main__." + __name__)
logging.propagate = True


class CredentialProvider:
    """
    CredentialProvider is an abstract class that defines the interface for credential providers.
    """
    SPEC = {}

    def __init__(self, credential_file):
        self.credential_file = credential_file

    def verify_spec(self, credentials):
        """
        Verify that the credentials match the specification.
        :param credentials:
        :return:
        """
        for key, value in self.SPEC.items():
            if not value(credentials.get(key, "")):
                logging.warning(f"Invalid {key}.")
                return False
        return True

    def verify_credentials(self, credentials):
        """
        Verify that the credentials are valid.
        :param credentials:
        :return:
        """
        raise NotImplementedError(
            "Subclasses must implement verify_credentials(), Return True if verification "
            "impossible or unnecessary."
        )

    def _load_from_file(self):
        """
        Load credentials from file.
        :return:
        """
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
        """
        Get credentials from the user.
        :return:
        """
        raise NotImplementedError("Subclasses must implement get_credentials()")

    def store_credentials(self, credentials):
        """
        Store credentials to file.
        :param credentials:
        :return:
        """
        with open(self.credential_file, "w", encoding="utf-8") as file:
            json.dump(credentials, file)


class SpotifyCredentialProvider(CredentialProvider):
    SPEC = {"cid": lambda x: len(x) > 0, "secret": lambda x: len(x) > 0} # cid = client id, secret = client secret
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


if __name__ == "__main__":
    spotify = SpotifyCredentialProvider(mporg.CONFIG_DIR / "spotify.json")

    print(spotify.get_credentials())
