import os
from dataclasses import dataclass
from enum import Enum

import requests

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
    "fingerprinter": "https://github.com/yourusername/yourpluginrepo/plugin1.zip",
}


def download_plugins(plugin_urls, destination_folder):
    os.makedirs(destination_folder, exist_ok=True)
    for url in plugin_urls:
        response = requests.get(url)
        if response.status_code == 200:
            plugin_filename = url.split("/")[-1]
            plugin_path = os.path.join(destination_folder, plugin_filename)
            with open(plugin_path, "wb") as f:
                f.write(response.content)
