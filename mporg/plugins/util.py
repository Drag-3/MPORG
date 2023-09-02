import os
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from mporg.credentials.providers import CredentialProvider


@dataclass
class PluginInfo:
    plugin: object
    provider: CredentialProvider


class PluginType(Enum):
    FINGERPRINTER = "FingerprinterPlugins"
    SEARCHER = "SearcherPlugins"
    LYRICS = "LyricsPlugins"


default_plugin_urls = {
    "fingerprinter": "https://raw.githubusercontent.com/Drag-3/MPORG/dev/plugins/plugins/FingerprinterPlugins"
                     "/MBFingerprinterPlugin.py",
}


if __name__ == "__main__":
    download_plugins(default_plugin_urls.values(), "")