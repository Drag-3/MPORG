# MPORG

MPORG (short for MP3 ORGanizer) is a python package designed to organize music files in a given directory.

## Table of Contents
- [Project Description](#project-description)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

# Project Description
The project aims to organize music files. It uses mutagen to query the Spotify api using stored metadata, and if that fails, uses Audio fingerprinting. (Currently via ACRCloud and AcoustID/MusicBrainz).
This will hopefully make it easier to organize my music libraries in a consistent manner.

## Installation
To install this project and edit it...
1. Clone this repo:
   ```bash
   git clone https://github.com/Drag-3/MP3ORG.git
   ```
2. Navigate to the cloned repo.
    ```bash
    cd mporg
    ```
3. Install the required dependencies:
    ```bash
   pip install -r requirements.txt
    ```