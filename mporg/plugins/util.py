import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from mporg.credentials.providers import CredentialProvider
from mporg.plugins import PLUGIN_DIR


@dataclass
class Plugin:
    plugin: object
    provider: CredentialProvider


@dataclass
class PluginInfo:
    name: str
    type: str
    dependancies: list[str]
    modules: list[{str, str}]
    dir: Path


class PluginType(Enum):
    FINGERPRINTER = "FingerprinterPlugins"
    SEARCHER = "SearcherPlugins"
    LYRICS = "LyricsPlugins"


default_plugin_urls = {
    "fingerprinter": "https://raw.githubusercontent.com/"
                     "Drag-3/MPORG/dev/plugins/plugins/FingerprinterPlugins/MBFingerprinter/plugin.json",
}


def get_plugin_info(url: str):
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.json()

    name = content.get("name")
    type = content.get("type")
    dependancies = content.get("dependencies")
    modules = content.get("modules")

    if type == "FingerprinterPlugin":
        plugin_dir = PLUGIN_DIR / os.path.join("FingerprinterPlugins", name)
    elif type == "SearcherPlugin":
        plugin_dir = PLUGIN_DIR / os.path.join("SearcherPlugins", name)
    elif type == "LyricsPlugin":
        plugin_dir = PLUGIN_DIR / os.path.join("LyricsPlugins", name)
    else:
        raise ValueError("Invalid plugin type")

    if not plugin_dir.exists():
        plugin_dir.mkdir(0o777, parents=True, exist_ok=True)

    with open(plugin_dir / "plugin.json", "w") as f:
        f.write(resp.text)

    return PluginInfo(name, type, dependancies, modules, plugin_dir)


def install_plugin_dependancies(plugin: PluginInfo):
    for package in plugin.dependancies:
        subprocess.run(["pip", "install", package])


def install_plugin_modules(plugin: PluginInfo):
    for package in plugin.modules:
        content = requests.get(package.get("url")).text

        with open(plugin.dir / package.get("name"), "w") as f:
            f.write(content)


def install_plugin(source: str):
    plugin = get_plugin_info(source)
    install_plugin_dependancies(plugin)
    install_plugin_modules(plugin)


def install_default_plugins():
    for url in default_plugin_urls.values():
        install_plugin(url)


if __name__ == "__main__":
    install_default_plugins()
