import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import rich

import requests
from rich.markdown import Markdown

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
    readme: bool = False


class PluginType(Enum):
    FINGERPRINTER = "FingerprinterPlugins"
    SEARCHER = "SearcherPlugins"
    LYRICS = "LyricsPlugins"


default_plugin_urls = {
    PluginType.FINGERPRINTER: "https://raw.githubusercontent.com/"
                              "Drag-3/MPORG/dev/plugins/plugins/FingerprinterPlugins/MBFingerprinter/plugin.json",
}


def get_plugin_info(url: str):
    """
    Get the plugin info from the plugin.json file
    :param url:  URL to the plugin.json file
    :return:
    """
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.json()

    logging.debug(f"Plugin JSON: {content}")
    name = content.get("name")
    plugin_type = content.get("type") + "s"
    readme_url = content.get("readme")
    dependancies = content.get("dependencies")
    modules = content.get("modules")

    plugin_dir = get_plugin_dir(PluginType(plugin_type), name)
    logging.debug(f"Plugin dir: {plugin_dir}")

    if not plugin_dir.exists():
        plugin_dir.mkdir(0o777, parents=True, exist_ok=True)

    with open(plugin_dir / "plugin.json", "w") as f:
        f.write(resp.text)

    if readme_url:  # Write the README.md file if it exists
        with open(plugin_dir / "README.md", "w") as f:
            f.write(requests.get(readme_url).text)

    return PluginInfo(name, plugin_type, dependancies, modules, plugin_dir, readme_url is not None)


def install_plugin_dependencies(plugin: PluginInfo):
    """
    Install the dependencies for the plugin
    :param plugin:
    :return:
    """
    logging.info(f"Installing dependencies for {plugin.name}")
    for package in plugin.dependancies:
        subprocess.run(["pip", "install", package])
        logging.debug(f"Installed {package}")


def install_plugin_modules(plugin: PluginInfo):
    """
    Install the modules for the plugin
    :param plugin:
    :return:
    """
    main_entrypoint_found = False
    logging.info(f"Installing modules for {plugin.name}")
    for package in plugin.modules:
        content = requests.get(package.get("url")).text
        module_name = package.get("name")

        with open(plugin.dir / module_name, "w") as f:
            f.write(content)

        if module_name.endswith("Plugin.py"):
            main_entrypoint_found = True

    if not main_entrypoint_found:
        logging.error("Error: No main entrypoint module (*Plugin.py) found in the plugin modules.")
        logging.info(f"Deleting plugin {plugin.name}")
        delete_plugin(plugin.dir)


def install_plugin(source: str):
    """
    Install a plugin from a URL
    :param source: URL to the plugin.json file
    :return bool:  True if the plugin was installed successfully, False if the plugin was not installed
    """
    plugin = get_plugin_info(source)
    logging.info(f"Installing plugin: {plugin.name}")
    if plugin.readme:
        display_markdown(plugin.dir / "README.md")
        rich.print(f"Please read the README.md file for {plugin.name} and install any dependencies before continuing. [Enter] to continue, or any other key to cancel")
        user_quit = input()
        if user_quit:
            # Installation is Aborted!
            logging.info(f"Install of {plugin.name} aborted")
            rich.print("[bold red]ABORTED[/bold red]")
            return False

    install_plugin_dependencies(plugin)
    install_plugin_modules(plugin)
    logging.info(f"Plugin {plugin.name} installed successfully.")
    return True


def delete_plugin(plugin_dir: Path):
    """
    Delete a plugin directory
    :param plugin_dir:
    :return:
    """
    try:
        if plugin_dir.exists():
            if plugin_dir.is_file():
                plugin_dir.unlink()
            else:
                for item in plugin_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    else:
                        delete_plugin(item)
                plugin_dir.rmdir()
    except Exception as e:
        logging.exception(f"Error deleting plugin: {e}")


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
            logging.info(f"Plugin {plugin_name} does not exist.")
            # If the directory does not exist, install the plugin
            install_plugin(url)
        else:
            # If the directory exists, check if the plugin.json file exists
            plugin_json_file = plugin_dir / "plugin.json"
            if not plugin_json_file.exists():
                logging.info(f"Plugin {plugin_name} exists but is missing plugin.json file.")
                # If the plugin.json file does not exist, install the plugin
                install_plugin(url)


def setup_and_check_plugins():
    if not PLUGIN_DIR.exists():
        PLUGIN_DIR.mkdir(0o777, parents=True, exist_ok=True)

    # Verify default plugins
    check_default_plugins()
    logging.info("Default plugins verified.")


def display_markdown(md_file: Path):

    with open(md_file, 'r', encoding='utf-8') as file:
        console = rich.get_console()
        console.print(Markdown(file.read()))

# TODO: Provide a way to diplay an plugin's Version, and automatically check for updates
# When installing a plugin, it will check if the plugin is already installed, and if so, check if the version is the same.
# If the version is the same it will ask if you want to reinstall the plugin, if the version is different it will ask if you want to update the plugin.


if __name__ == "__main__":
    display_markdown("/home/justin/PycharmProjects/MP3ORG/plugins/FingerprinterPlugins/MBFingerprinter/README.md")
