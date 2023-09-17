# MBFingerprinter  
## Description  
This plugin serves as a FingerprinterPlugin that uses the Chromaprint Library, the Acoustid Service, and the MusicBrainz Service in order to fingerprint and gather metadata on unknown music files.

*Install-Instructions*  

This plugin requires some non python dependancies. The Chromaprint Library along with fpcalc and ffmpeg must be installed on the users system. Specific Instructions are below.

To install the non python dependencies:
- Install FFmpeg:
    - On Linux:
        - Install ffmpeg using your distibution's package manager.
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

```
Thoughts
If I can provide plugin READMEs as md files or txt files, How can I render md files upon download?
Need to research some packages that can do that if possible.
Also how would I render it? The terminal may not be feasible, but this is a terminal application...
Packages to render markdown in terminal ? Would have to be cross platform hopefully... or I would have to change imports and deps based on device type
Reseach ig ----> Will use rich. I've already used it in earlier applications and it seems to work well enough cross platform.


Link to README will be included in plugin.json as "README: https://example.com"

Once that is complete add a command to display a plugin readme for an installed plugin, or for non installed plgins
For an installed plugin it will find and render the readme.
For an non installed plugin it will download plugin.json to temp storage, then download the readme to temp storage, then render the readme.
To preserve ram have a directory tree in temp storage...

Now while installing a plugin I want the readme to be displayed, Specifically to show the user any non python depenancies required and how to install them
The user will read and then press a button and installation will continue.

Having all of this sould make it easier for plugins to 'just work' as they do with plugins with no non-python dependancies.
```