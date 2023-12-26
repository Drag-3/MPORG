import json
import subprocess
from tempfile import TemporaryDirectory
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
    version: str
    dependencies: list[str]
    modules: list[{str, str}]
    dir: Path
    readme: bool = False
    url: str = None


class PluginType(Enum):
    FINGERPRINTER = "FingerprinterPlugins"
    SEARCHER = "SearcherPlugins"
    LYRICS = "LyricsPlugins"


default_plugin_urls = {
    PluginType.FINGERPRINTER: "https://raw.githubusercontent.com/"
                              "Drag-3/MPORG/master/plugins/FingerprinterPlugins/MBFingerprinter/plugin.json",
}


def get_plugin_info(url: str, temp=False):
    """
    Get the plugin info from the plugin.json file
    :param temp:
    :param url:  URL to the plugin.json file
    :return:
    """
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.json()

    logging.debug(f"Plugin JSON: {content}")
    name = content.get("name")
    plugin_type = content.get("type") + "s"
    version = content.get("version")
    readme_url = content.get("readme")
    dependencies = content.get("dependencies")
    modules = content.get("modules")
    json_url = content.get("json")

    if temp:
        plugin_dir = TemporaryDirectory()
    else:
        plugin_dir = get_plugin_dir(PluginType(plugin_type), name)
    logging.debug(f"Plugin dir: {plugin_dir}")

    if not plugin_dir.exists():
        plugin_dir.mkdir(0o777, parents=True, exist_ok=True)

    with open(plugin_dir / "plugin.json", "w") as f:
        f.write(resp.text)

    if readme_url:  # Write the README.md file if it exists
        with open(plugin_dir / "README.md", "w") as f:
            f.write(requests.get(readme_url).text)

    return PluginInfo(name, plugin_type, version, dependencies, modules, plugin_dir, readme_url is not None, json_url)


def install_plugin_dependencies(plugin: PluginInfo):
    """
    Install the dependencies for the plugin
    :param plugin:
    :return:
    """
    logging.info(f"Installing dependencies for {plugin.name} v{plugin.version}")
    for package in plugin.dependencies:
        ret = subprocess.run(["pip", "install", package]).returncode
        if ret != 0:
            logging.error(f"Error installing {package}")
            raise Exception(f"Error installing {package} dependency")
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


def install_plugin_to_temp(source: str) -> Path | None:
    """
    Install a plugin to a temporary directory
    :param source: URL to the plugin.json file
    :return Path: Path to the temporary directory
    """
    plugin = get_plugin_info(source, temp=True)
    try:
        logging.info(f"Installing plugin: {plugin.name} v{plugin.version}")
        if plugin.readme:
            display_markdown(plugin.dir / "README.md")
            rich.print(
                f"Please read the README.md file for {plugin.name} and install any dependencies before continuing. [Enter] to continue, or any other key to cancel")
            user_quit = input()
            if user_quit:
                # Installation is Aborted!
                logging.info(f"Install of {plugin.name} aborted")
                rich.print("[bold red]ABORTED[/bold red]")
                delete_plugin(plugin.dir)
                return None

        install_plugin_dependencies(plugin)
        install_plugin_modules(plugin)
        logging.info(f"Plugin {plugin.name} installed successfully.")
        return plugin.dir
    except Exception as e:
        logging.exception(f"Error installing plugin: {e}")
        logging.info(f"Deleting plugin {plugin.name}")
        delete_plugin(plugin.dir)
        return None

def install_plugin(source: str):
    """
    Install a plugin from a URL
    :param source: URL to the plugin.json file
    :return bool:  True if the plugin was installed successfully, False if the plugin was not installed
    """
    plugin = get_plugin_info(source)
    try:
        logging.info(f"Installing plugin: {plugin.name} v{plugin.version}")
        if plugin.readme:
            display_markdown(plugin.dir / "README.md")
            rich.print(
                f"Please read the README.md file for {plugin.name} and install any dependencies before continuing. [Enter] to continue, or any other key to cancel")
            user_quit = input()
            if user_quit:
                # Installation is Aborted!
                logging.info(f"Install of {plugin.name} aborted")
                rich.print("[bold red]ABORTED[/bold red]")
                delete_plugin(plugin.dir)
                return False

        install_plugin_dependencies(plugin)
        install_plugin_modules(plugin)
        logging.info(f"Plugin {plugin.name} installed successfully.")
        return True
    except Exception as e:
        logging.exception(f"Error installing plugin: {e}")
        logging.info(f"Deleting plugin {plugin.name}")
        delete_plugin(plugin.dir)
        return False


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
            return

        # If the directory exists, check if the plugin.json file exists
        plugin_json_file = plugin_dir / "plugin.json"
        if not plugin_json_file.exists():
            logging.info(f"Plugin {plugin_name} exists but is missing plugin.json file.")
            # If the plugin.json file does not exist, install the plugin
            install_plugin(url)
            return

        plugin_pattern = "*Plugin.py"
        # If the plugin.json file exists, check if the main entrypoint module exists
        if not any(plugin_dir.glob(plugin_pattern)):
            logging.info(f"Plugin {plugin_name} exists but is missing main entrypoint module.")
            # If the main entrypoint module does not exist, install the plugin
            install_plugin(url)


def setup_and_check_plugins():
    if not PLUGIN_DIR.exists():
        PLUGIN_DIR.mkdir(0o777, parents=True, exist_ok=True)

    # Verify default plugins
    check_default_plugins()
    logging.info("Default plugins verified.")


def check_plugin_updates(force = False):
    """
    Check for updates to installed plugins
    :return:
    """
    plugins = get_installed_plugins()
    for plugin in plugins:
        installed_version = plugin.version
        current_version = requests.get(plugin.url).json().get("version")
        if installed_version != current_version or force:
            logging.info(f"Plugin {plugin.name} has an update available.")
            rich.print(f"Plugin [bold]{plugin.name}[/bold] has an update available.")
            rich.print(f"Installed: {installed_version}. New Version: {current_version}")
            rich.print("Press [Enter] to update, or any other key to skip.")
            user_input = input()
            if not user_input:
                #Need a way to verify update is successful and rollback if not. As of now it would keep failed updates.
                logging.info(f"Updating plugin {plugin.name}")
                # Install Plugin to a temporary directory
                temp_dir = install_plugin_to_temp(plugin.url)
                if temp_dir: # If the plugin was installed successfully
                    # Delete the old plugin directory
                    delete_plugin(plugin.dir)
                    # Move the new plugin directory to the old plugin directory's location
                    temp_dir.rename(plugin.dir)
                    logging.info(f"Plugin {plugin.name} updated successfully.")
                else:
                    logging.error(f"Error updating plugin {plugin.name}. Previous version retained.")
            else:
                logging.info(f"Skipping update for plugin {plugin.name}")


def get_installed_plugins():
    """
    Return an array of installed plugins, and their versions once added
    :return: list[PluginInfo]
    """
    plugins = []
    for plugin_type in PluginType:
        for plugin_dir in PLUGIN_DIR.glob(f"{plugin_type.value}/*"):
            plugin_json_file = plugin_dir / "plugin.json"
            if plugin_json_file.exists():
                with open(plugin_json_file, "r") as f:
                    plugin_json = json.loads(f.read())
                    plugins.append(PluginInfo(**plugin_json, dir=plugin_dir))
    return plugins


def display_markdown(md_file: Path):
    with open(md_file, 'r', encoding='utf-8') as file:
        console = rich.get_console()
        console.print(Markdown(file.read()))


if __name__ == "__main__":
    # display_markdown("/home/justin/PycharmProjects/MP3ORG/plugins/FingerprinterPlugins/MBFingerprinter/README.md")
    print(get_installed_plugins())
    check_plugin_updates()
