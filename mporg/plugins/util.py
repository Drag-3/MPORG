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
    PluginType.FINGERPRINTER: "https://raw.githubusercontent.com/"
                              "Drag-3/MPORG/dev/plugins/plugins/FingerprinterPlugins/MBFingerprinter/plugin.json",
}


def get_plugin_info(url: str):
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.json()

    name = content.get("name")
    type = content.get("type") + "s"
    dependancies = content.get("dependencies")
    modules = content.get("modules")

    plugin_dir = get_plugin_dir(PluginType(type), name)

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


def get_plugin_dir(plugin_type, plugin_name):
    if plugin_type == PluginType.FINGERPRINTER:
        return PLUGIN_DIR / "FingerprinterPlugins" / plugin_name
    elif plugin_type == PluginType.SEARCHER:
        return PLUGIN_DIR / "SearcherPlugins" / plugin_name
    elif plugin_type == PluginType.LYRICS:
        return PLUGIN_DIR / "LyricsPlugins" / plugin_name
    else:
        raise ValueError("Invalid plugin type")


def check_default_plugins():
    for plugin_type, url in default_plugin_urls.items():
        # Determine the plugin name from the URL
        plugin_name = url.split("/")[-2]

        # Create the plugin directory path
        plugin_dir = get_plugin_dir(plugin_type, plugin_name)

        # Check if the plugin directory exists
        if not plugin_dir.exists():
            # If the directory does not exist, install the plugin
            install_plugin(url)
        else:
            # If the directory exists, check if the plugin.json file exists
            plugin_json_file = plugin_dir / "plugin.json"
            if not plugin_json_file.exists():
                # If the plugin.json file does not exist, install the plugin
                install_plugin(url)


def setup_and_check_plugins():
    if not PLUGIN_DIR.exists():
        PLUGIN_DIR.mkdir(0o777, parents=True, exist_ok=True)

    # Verify default plugins
    check_default_plugins()


if __name__ == "__main__":
    install_default_plugins()
