# MPORG

MPORG (short for MP3 ORGanizer) is a Python package designed to organize music files in a given directory.

[![Python application](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml/badge.svg)](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://opensource.org/licenses/GPL-3.0)

## Table of Contents
- [Project Description](#project-description)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

## Project Description
The project aims to organize music files. It uses mutagen to get stored metadata in order to query the Spotify API, and if that fails, it uses audio fingerprinting (currently via ACRCloud and AcoustID/MusicBrainz). This will hopefully make it easier to organize music libraries in a consistent manner.

## Installation
### Normal Installation


To install this project for normal use:

1. **WINDOWS ONLY**: Download and install Visual Studio 2010 (VC++ 10.0) SP1 from [this link](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2010-vc-100-sp1-no-longer-supported). This is a mandatory step as the project relies on it to function correctly on Windows.
   ![img_1.png](img_1.png)

2. Install the project using pip:
   ```bash
   pip install git+https://github.com/Drag-3/MPORG.git
   ```

3. Install chromaprint and its dependencies:
   - On Linux:
     - Install chromaprint using your distribution's package manager. For example:
       ```bash
       apt install chromaprint
       ```
     - If you choose to install chromaprint from the acoustid [Website](https://acoustid.org/chromaprint), ensure that you add fpcalc to your PATH. This is required for the program to detect and use fpcalc properly.
   - On Windows:
     - If you haven't already, install chromaprint from the acoustid [Website](https://acoustid.org/chromaprint).
     - Make sure to add fpcalc to your PATH.

   Note: Installing ffmpeg is also necessary for both Linux and Windows installations.

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

3. **WINDOWS DEVICES ONLY**: Before using the requirements file, ensure that you have Visual Studio 2010 (VC++ 10.0) SP1 installed. If you haven't installed it yet, you can download it from [Microsoft](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2010-vc-100-sp1-no-longer-supported). This step is necessary for ACRCloud to work correctly.

   ![img.png](img_1.png)

4. Install chromaprint and its dependencies, following the instructions mentioned in the "Normal Installation" section.

5. Install the required dependencies:
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
- `-a`, `--acrcloud`: Use Acrcloud for audio fingerprinting.
- `-m`, `--music_brainz`: Use Musicbrainz for audio fingerprinting.
- `-f`, `--fingerprint`: Use all fingerprinters (same as `-am`).

### Examples
- To run MPORG with a specific store path and search path:
  ```bash
  mporg /path/to/store /path/to/search
  ```

- To run MPORG with custom options:
  ```bash
  mporg -l 2 -am
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


For audio fingerprinting, MPORG relies on ACRCloud and AcoustID. Here's how to set them up:

1. Sign up for ACRCloud's [service](https://console.acrcloud.com). Please note that ACRCloud is a paid API.
2. To acquire an AcoustID API key, register your application with [AcoustID](https://acoustid.org/new-application). The AcoustID and MusicBrainz APIs are free to use.


## Contributing
Pull Requests are always welcome. For major changes, please open an issue discussing what changes you would like to make.

## Credits
MPORG was created by Drag (Justin Erysthee).

## License
MPORG is licensed under the GPL-3.0 license.


*This README is applicable for version 0.1a2.*
