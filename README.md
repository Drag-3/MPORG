# MPORG

MPORG (short for MP3 ORGanizer) is a Python package designed to organize music files in a given directory.

[![Python application](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml/badge.svg)](https://github.com/Drag-3/MP3ORG/actions/workflows/python-app.yml)
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
1. **WINDOWS ONLY**: Download Visual Studio 2010 (VC++ 10.0) SP1 from [this link](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2010-vc-100-sp1-no-longer-supported).
   ![img_1.png](img_1.png)
2. Install the project using pip:
   ```bash
   pip install git+https://github.com/Drag-3/MP3ORG.git
   ```
### Dev Installation
To install for editing or modification:
1. Clone this repo:
   
   ```bash
   git clone https://github.com/Drag-3/MP3ORG.git
   ```
2. Navigate to the cloned directory:
   
   ```bash
   cd mporg
   ```
3. **WINDOWS DEVICES ONLY**: Install Visual Studio 2010 (VC++ 10.0) SP1 for ACRCloud to work. You can download it from [Microsoft](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2010-vc-100-sp1-no-longer-supported). This must be done before using the requirements file.
   
   ![img.png](img_1.png)
4. Install the required dependencies:
   
   ```bash
   pip install -r requirements.txt OR pip install -r requirements_tests.txt
   ```
   
## Usage
Upon a normal run, MPORG will search the search-path for music files, and copy organized files to the store-path:
```bash
mporg -[vhVfam] <store-path> <search-path>
```
If the search-path is not provided, MPORG will search the directory the script was run from (pwd):
```bash
mporg -[vhVfam] <store-path>
```
If run with no arguments, MPORG will save organized music to $HOME/Music/TuneTagLibrary:
```bash
mporg -[vhVfam]
```

You can also specify command line options to customize the behavior of the script.
Below are the available options:
- `-v` or `-version`: Show the version of MPORG.
- `-V` or `-verbose`: Print detailed output during execution.
- `-a` or `-acrcloud`: Use Acrcloud for audio fingerprinting.
- `-m` or `-music_brainz`: Use Musicbrainz for audio fingerprinting.
- `-f` or `-fingerprint`: Use all fingerprinters (same as `-am`).

You can also run the following command to see all available options and their descriptions:
```bash
mporg -h
```

## Configuration
Upon start, MPORG will prompt for the credentials it will use if they are not saved.

MPORG uses the Spotify API to look up track and artist information, so you will have to set up a Spotify developer account in order to get a client ID and secret.

You can obtain those here at the [Spotify Developer Website](https://developer.spotify.com/).

For audio fingerprinting, MPORG uses ACRCloud and AcoustID.

You can gain ACRCloud credentials by signing up for their [service](https://console.acrcloud.com). Keep in mind it is a paid API.

You can get an AcoustID API key by registering an application with [AcoustID](https://acoustid.org/new-application). The AcoustID and MusicBrainz APIs are free to use.

## Contributing
Pull Requests are always welcome. For major changes, please open an issue discussing what changes you would like to make.

## Credits
MPORG was created by Drag (Justin Erysthee).

## License
MPORG is licensed under the GPL-3.0 license.


*This README is good for version 0.1a1*
