# MBFingerprinter  
## Description  
This plugin serves as a FingerprinterPlugin that uses the Chromaprint Library, the Acoustid Service, and the MusicBrainz Service in order to fingerprint and gather metadata on unknown music files.

## Install-Instructions

This plugin requires some non python dependencies. The [Chromaprint Library](https://acoustid.org/chromaprint) along with fpcalc and [ffmpeg](https://ffmpeg.org/) must be installed on the users system. Specific Instructions are below.

To install the non python dependencies:
- Install FFmpeg:
    - On Linux:
        - Install ffmpeg using your distribution's package manager.
        ```bash
            apt install ffmpeg
        ```
        ```bash
            pacman -S ffmpeg
        ```
    - On Windows:
        - If you have winget installed you can use winget as it is the easier option
        ```bash
            winget install Gyan.FFmpeg
        ```
        - Otherwise, install ffmpeg from its [site](https://ffmpeg.org). Remember to add ffmpeg to your system PATH.

- Install Chromaprint:
   - On Linux:
       - Install chromaprint using your distribution's package manager. For example:
       ```bash
           apt install libchromaprint-dev libchromaprint-tools
       ```
       ```bash
           pacman -S chromaprint
       ```
       ```bash
           zypper install chromaprint-fpcalc
       ```
       - If you choose to install chromaprint from the acoustid [Website](https://acoustid.org/chromaprint), ensure that you add fpcalc to your PATH. This is required for the program to detect and use fpcalc properly.
   - On Windows:
       - If you haven't already, install chromaprint from the acoustid [Website](https://acoustid.org/chromaprint).


## Credentials Required
This plugin requires an AcoustID API Key. To acquire an AcoustID API key, register your application at the [AcoustID](https://acoustid.org/new-application) site. The AcoustID and MusicBrainz APIs are free to use.  
When running this plugin for the first time you will be prompted to enter your API Key. This will be stored in the config file and will not be prompted for it again.

## Credits
This plugin was written by Drag-3.