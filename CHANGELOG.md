# Changelog

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


*I'll add bugs as I find them*)