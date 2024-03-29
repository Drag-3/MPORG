# Changelog

## [0.2a3] - 2023-12-26
### Added
- **Update to Tagger for COMM Languages**: Tagger now searches COMM fields with additional language values: "XXX", "\0\0\0", and "eng".

### Changed
- **MPORG Language Standardization**: MPORG will now save comment tags using "XXX" by default, aligning with the standard for non-language-specific comments. This is a non-breaking change as the Tagger still reads old "\0\0\0" tags.
- **Update to `plugin.json` Files**: Introduced a "version" field in `plugin.json` files. The program will now compare the installed plugin version with the remote version upon execution, notifying users of any changes.

### Fixed
- **README.md Update**: Updated `README.md` to reflect the new "version" field in `plugin.json` files.
- **File Organization Robustness**: Addressed an issue in `organizer.py` where the absence of a comment field could halt the file organization process.

### Maintenance
- **Recommendation for URL Comments**: Advised the deletion of old URL comments to prevent confusion with apps that might be distracted by the presence of multiple comment formats.

### Known Bugs
- No new bugs reported.

## [0.2a2] - 2023-09-18
### Added
- Nada

### Changed
- Moved ACRCloud functionality to plugin as planned. Removed dependencies for base program.

### Fixed
- README plugin description
## [0.2a1] - 2023-09-18
### Added
- Plugins: Users can now add their own fingerprinters. This allows them to use their own API keys and services. See the [README](README.md) for more information.
- Added `--install-plugin` option: Users can now install plugins from the command line by entering the url of the plugin.

### Changed
- Moved AcoustID and MusicBrainz to a default plugin.
- `-f` `--fingerprinter` option now takes a list of plugins names. Instead of using all fingerprinters. That is now done with `-af` `--all-fingerprinters`.
- Removed `-a` and `-m` options. With the addition of plugins, these options are no longer needed, as fingerprinters can be added and removed as needed and then called with `-f` or `-af`.

### Fixed
- Fixed pyproject.toml to include all dependencies in the requirements.txt file. Previously it had a hardcoded out of date list of dependencies causing pip install to fail.

## [0.1a3] - 2023-07-28
After every update I recommend deleting the caches in order to make sure you use the live version.
### Added
- Added .flac, .ogg, .oga support: The program now supports additional audio file formats, including FLAC, OGG, and OGA.
- Added `-y` `--lyrics` option: Users can now use the -y or --lyrics option to find and save lyrics along with the music files.
- Added `-p` `--pattern` option: This option allows users to restrict file types when organizing files. For example, they can separate .mp3 and .flac files into different folders.
- Check for Spotify URL in metadata: The program now checks if a Spotify URL is available in the metadata of a track. If found, it directly fetches the track instead of attempting a keyword search.

### Changed
- Replaced Spotipy with requests trying to fix a rate-limiting bug. Currently not sure if spotipy was the problem, but I am too lazy to change it back for now.
- Program should not skip invalid files ie .txt, and not waste a thread validating them there

### Fixed
- Tests should now work again :)
- Program now ignores when unneeded info (genre, audio info) are not taken from spotify. The fields will get default values.
- The sanitization and path building functions are now platform aware, So that in a Unix system we can potentially have a path up to 4096 chars while windows is limited to 254.

### New Known Bugs
- [Bug with LyricsSearcher]
- In the Fingerprinters sometimes the response is not valid json. This currently halts organization for this track, which skips the copying process. Later, make it return None instead of raising an error to fall back to metadata.

### Direction
- Add an option to delete old files once organized
- Plugin support ? So that users can add their own fingerprinters.
- If plugin support is added, move acrcloud to a plugin. This would simply the installation and make it so the base program is totally free.

## [0.1a2]

### Added
- Added credentials package and moved credentials handling logic into it.
- Added CHANGELOG
- Add Progress Bar for Scanning files, since it seemed a little empty

### Changed
- Moved file processing from multiprocessing to multithreading
- Replaced the verbose option `-V` with the log level option `-l`.
- Updated README to reflect the recent changes.
- Modified unit tests to correctly mock multithreading.
- Changed version number.

### Fixed
- Bugs with multithreading
- Console Logging and Progress Bar

### Known Bugs
- fpcalc sometimes fails with random exit codes, might be because of corrupt files, or a threading problem?

## [0.1a1]
### Added
- Added README
- Added Tests
- Added CI
### Changed
- Use multiprocessing for file processing logic
- Moved logs into config dir

### Fixed
- Fixed MusicBrainz and AcoustID functionality
- Linux directory permission bugs (You need execute to `cd`)

## [Unversioned]
### Added
- Add WAVE and ASF Support
- Add Progress Bars

### Changed
- Moved spotify auth cache into config dir to fix permissions issue
- Update pyacrcloud, Use version from GitHub for windows, and pip for linux

### Fixed
- Spotipy issue
- ACRCloud issue [tentatively]

### Known Bugs
- The Logging interferes with the progress bar and makes it look ugly
- Sometimes acrcloud.exr_tool fails with cryptic errors

## [Pre - Release]


### Added
- Everything

### Fixed
- So many bugs

### Known Bugs
- AcoustId and MusicBrainz will not work, Will fix later
- ACRCloud does not work on Linux due to differing versions, will look into
- On linux spotipy complains of cannot read/write from .cache


(*I'll add bugs as I find them*)