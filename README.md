# MPORG

MPORG (short for MP3 ORGanizer) is a Python package designed to organize music files in a given directory.

[![Python application](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml/badge.svg)](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://opensource.org/licenses/GPL-3.0)

## Table of Contents
- [Project Description](#project-description)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Plugins](#plugins)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

## Project Description
The project aims to organize music files. It uses mutagen to get stored metadata in order to query the Spotify API, and if that fails, it uses audio fingerprinting (currently via ACRCloud and AcoustID/MusicBrainz). This will hopefully make it easier to organize music libraries in a consistent manner.

## Installation
### Normal Installation


To install this project for normal use:
- Install the project using pip:
   ```bash
   pip install git+https://github.com/Drag-3/MPORG.git
   ```

### Dev Installation

To install the project for editing or modification:

1. Clone this repository:
   ```bash
   git clone https://github.com/Drag-3/MPORG.git
   ```

2. Navigate to the cloned directory:
   ```bash
   cd mporg
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This will ensure all the necessary packages for running the program are installed.

   If you need to run the test suite, use the following command instead:
   ```bash
   pip install -r requirements_tests.txt
   ```
   This will install additional dependencies required for running the tests.
   
## Usage
### Basic Usage
To run MPORG with default options, use the following command:
```bash
mporg [store-path] [search-path]
```
- If the `store-path` is not provided, MPORG will save organized music to `$HOME/Music/TuneTagLibrary`.
- If the `search-path` is not provided, MPORG will search the current directory.

### Command Line Options
You can specify the following command line options to customize the behavior of MPORG:

- `-v`, `--version`: Show the version of MPORG and exit.
- `-l`, `--log_level`: Logging level for the console screen. Specify an integer value.
- `-af`, `--all_fingerprint`: Use all installed fingerprinter plugins.
- `-f`, `--fingerprint`: Use specified fingerprinter.
- `-p`, `--pattern_extension`: Extension(s) to copy over, space separated.
- `-y`, `--lyrics`: Attempt to get lyrics and store with file.
- `--install-plugins`: Install specified plugins, space separated.

*Note*: The `--all_fingerprint` and `--fingerprint` options are mutually exclusive. If both are specified, the `--all_fingerprint` option will be used.
*Note*: Separate optional arguments from positional arguments with `--`. For example:
```bash
mporg -l 2 -af -- /path/to/store /path/to/search
```

### Examples
- To run MPORG with a specific store path and search path:
  ```bash
  mporg /path/to/store /path/to/search
  ```

- To run MPORG with custom options:
  ```bash
  mporg -l 2 -af
  ```
  ```bash
  mporg -f MB l 1 -p flac oga wma -y -- "C:\Users\Me\Music\Downloaded_New" "C:\Users\Me\Music\My Music\Library"
  ```
  

### Additional Help
To see all available options and their descriptions, run the following command:
```bash
mporg -h
```

## Configuration
Upon start, MPORG will prompt for the credentials it will use if they are not saved.

To utilize MPORG's features, you need to set up a Spotify developer account to obtain a client ID and secret. Follow these steps:

1. Visit the [Spotify Developer Website](https://developer.spotify.com/) to create an account.
2. Obtain your client ID and secret from the developer dashboard.


For audio fingerprinting, MPORG relies on plugins. Please refer to the README of the plugin you are using for instructions on how to obtain credentials.


## Plugins
MPORG supports plugins for fingerprints. With future plans to support lyrics and more. Plugins will allow the project to better fit your independent needs.

### Creating Plugins
To create a plugin, you need three main things:
- A repo or other service to host your plugin.
- A `plugin.json` file to describe your plugin.
- A `*Plugin.py` file to contain your plugin's code.

#### `plugin.json`
The `plugin.json` file is used to describe your plugin. It contains the following fields:
- `name`: The name of your plugin.
- `type`: The type of plugin. Currently, only `FingerprinterPlugin` is supported.
- `dependencies`: A list of dependencies required for your plugin to function. This is a list of strings. And it can include git URLs, PyPI package names, and local file paths.
- `modules`: A list of modules to import. This is a list of dicts. One of these must be the entry point for your plugin. Each dict must contain a `name` field and an `url` field. The `name` field is the desired filename of the module. The `url` field is the URL to the module. This will be a direct url to the file. For example, if you are hosting your plugin on GitHub, the URL will be in the format `https://raw.githubusercontent.com/<username>/<repo>/<branch>/<path/to/file>`. The `name` field will be the filename of the file at the end of the URL. For example, if the URL is `https://raw.githubusercontent.com/Drag-3/MPORG/main/mporg/plugins/acrcloud/ACRCloudPlugin.py`, the `name` field will be `ACRCloudPlugin.py`.
- `readme`: An optional URL to a README file for your plugin. This will be displayed to the user when they install your plugin. In the README information about non python dependencies should be included. In order for the user to install them before plugin installation. 

##### Example
```json
{
    "name": "MyFingerprintPlugin",
    "type": "FingerprinterPlugin",
    "version": "1.0.0",
    "dependencies": ["dependency1", "dependency2"],
    "readme": "https://github.com/user/my-fingerprint-plugin/raw/main/README.md",
    "modules": [
        {
            "name": "MyFingerprintPlugin.py",
            "url": "https://github.com/user/my-fingerprint-plugin/raw/main/MyFingerprintPlugin.py"
        }
    ]
}
```

#### `*Plugin.py`
The `*Plugin.py` file is the entry point for your plugin. The plugin type determines what class you must implement. Currently, only `FingerprinterPlugin` is supported.
- `FingerprinterPlugin`: This plugin type must include a `fingerprint` method. This method must take a file path as an argument and return a `Track` object.
The *Plugin.py file can optionally also contain a class derived from `CredentialProvider`. This class must implement the `get_credentials` method. This method must return a dictionary containing the credentials required for your plugin to function. It may also optionally implement a `verify_credentials` method. This method must return a boolean value indicating whether the credentials are valid.
Any amount of imports or setup can be made as long as these two methods are implemented.

##### Example
```python
#MyFingerprinterPlugin.py
from mporg.audio_fingerprinter import Fingerprinter, FingerprintResult
from mporg.credentials.providers import CredentialProvider

class MyFingerprintPlugin(Fingerprinter):
    def fingerprint(self, file_path):
        # Do fingerprinting here
        return FingerprintResult() # Return a FingerprintResult object with information about the file

class MyCredentialProvider(CredentialProvider):
    def __getcredentials(self):
        # Get credentials here
        return {"key": "value"} # Return a dictionary containing the credentials

    def verify_credentials(self, credentials: dict):
        # Verify credentials here
        return True # Return a boolean indicating whether the credentials are valid
```

#### Plugin Repos
Plugin repos are simply git repositories that contain plugins. They must contain a `plugin.json` file and a `*Plugin.py` file. They may also contain any other files or folders required for the plugin to function. The files can be in any directory structure. The plugin repo can be hosted on any service that supports git.

### Using Plugins
To use a plugin, you must first install it. This can be done by running the following command:
```bash
mporg --install-plugins [plugin1 url] [plugin2 url] ...
```
This will install the specified plugins. The plugins will be installed in the `$HOME/.mporg/plugins` directory. This directory will be created if it does not exist.
Currently only fingerprinter plugins are supported. To use a fingerprinter plugin, you must specify it in the command line options. This can be done by using the `-f` or `--fingerprint` option. For example:
```bash
mporg -f MyFingerprintPlugin
```
otherwise you can use `-af` to use all installed fingerprinter plugins:
```bash
mporg -af
```

### Plugin Guidelines
- Plugins can be hosted on any site that offers text storage and retrieval. This includes GitHub, GitLab, and Pastebin. However, GitHub is the recommended site for hosting plugins.
- Plugins must be hosted in a public repository. This is to ensure that MPORG can access the plugin.
- Plugin names should be unique. This is to prevent conflicts between plugins.
- Plugin names should be descriptive. This is to make it easier for users to identify plugins. For example, a plugin that uses ACRCloud for fingerprinting should be named `ACRCloudFingerprinterPlugin`.

### Notes
- Mporg will not automatically update plugins. If you want to update a plugin, you must reinstall it.
- Mporg will attempt to validate plugins before installing them. If a plugin fails validation, it will not be installed. This is not a guarantee that the plugin will work. Plugins may still fail to work even if they pass validation so please test your plugins before publishing them.
## Contributing
Pull Requests are always welcome. For major changes, please open an issue discussing what changes you would like to make.

## Credits
MPORG was created by Drag (Justin Erysthee).

## License
MPORG is licensed under the GPL-3.0 license.


*This README is applicable for version 0.2a2.*
