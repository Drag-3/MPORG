import logging
import os
from pprint import pprint

from mporg import CONFIG_DIR
from mporg.credentials.providers import SpotifyCredentialProvider, ACRCloudCredentialProvider, \
    AcoustIDCredentialProvider

logging.getLogger('__main__.' + __name__)
logging.propagate = True


class CredentialManager:
    def __init__(self):
        self.credential_providers = [
            SpotifyCredentialProvider(CONFIG_DIR / 'spotify.json'),
            #ACRCloudCredentialProvider(CONFIG_DIR / "acrcloud.json"),
            #AcoustIDCredentialProvider(CONFIG_DIR / "acoustid.json")
        ]

    def create_directories_and_files(self):
        if not CONFIG_DIR.exists():
            os.mkdir(CONFIG_DIR)
            logging.debug(f"Creating {CONFIG_DIR}")

        for provider in self.credential_providers:
            if not provider.credential_file.exists():
                provider.credential_file.touch(0o666)
                logging.debug(f"Creating {provider.credential_file}")

    def get_credentials(self, use_acr=False, use_mb=False):
        self.create_directories_and_files()

        credentials = {}

        for provider in self.credential_providers:

            provider_credentials = provider.get_credentials()

            credentials[provider.PNAME] = provider_credentials

        return credentials


if __name__ == '__main__':
    manager = CredentialManager()
    print(manager.get_credentials())

