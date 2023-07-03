import logging
import os
import threading
import unittest
from math import ceil
from unittest.mock import patch, call, Mock, MagicMock, ANY
from pathlib import Path
import sys
from parameterized import parameterized

import mporg.main
import mporg.organizer as mp
from mporg.logging_utils.logging_setup import setup_logging

from tests import utils
from tests.utils import MockThreadPoolExecutor


class TestMPORGHelpers(unittest.TestCase):
    if sys.platform == "linux":  # Use Linux stuff:
        path_max = os.pathconf('/', "PC_PATH_MAX")
    else:  # Assume Windows as it has a lower path max
        from ctypes.wintypes import MAX_PATH
        path_max = MAX_PATH
    path_max -= 5  # Buffer for ceil function
    path_max -= 4
    max_segment = 255 // 2 - 7

    # Calculate maximum lengths for artist and name segments
    segment_max = ceil(path_max * 0.20)
    artist_max = min(max_segment, segment_max)

    segment_max = ceil(path_max * 0.30)
    name_max = min(max_segment, segment_max)

    long_message = "x" * path_max

    @parameterized.expand([
        ("No Invalid", "qwerty", "qwerty"),
        ("One Invalid", "qwe?rty", "qwerty"),
        ("Multiple Invalid", "q<w:e\\r|t*y\x00", "qwerty"),
        ("Only Invalid", "<>:/\\|?*.\x00", "")
    ])
    def test_remove_invalid_path_chars(self, name, input_str, expected_output):
        self.assertEqual(mp._remove_invalid_path_chars(input_str), expected_output)

    @parameterized.expand([
        ("Within Limits",
         mp.Track(album_artists=("Artist1", "Artist2",),
                  track_artists=("Artist3",),
                  album_name="Album Name",
                  track_name="Track Name"),
         ("Artist1, Artist2", "Album Name", "Artist3", "Track Name")),
        ("Long Album Name",
         mp.Track(album_artists=("Artist1", "Artist2",),
                  track_artists=("Artist3",),
                  album_name=long_message + "This is above",
                  track_name="Track Name"),
         ("Artist1, Artist2", 'x' * name_max, "Artist3", "Track Name")),
        ("Long Track Name",
         mp.Track(album_artists=("Artist1", "Artist2",),
                  track_artists=("Artist3",),
                  album_name="Album Name",
                  track_name=long_message + "This is above"),
         ("Artist1, Artist2", "Album Name", "Artist3", 'x' * name_max)),
        ("Long Track and Album",
         mp.Track(album_artists=tuple(["Artist1" * path_max]),  # Much larger thna path max
                  track_artists=("Artist2" * path_max,),
                  album_name=long_message,  # 10 characters
                  track_name=long_message),  # 10 characters
         (("Artist1" * 24)[:artist_max],  # 30 characters
          "x" * name_max,  # 10 characters
          ("Artist2" * 20)[:artist_max],  # 30 characters
          "x" * name_max  # 10 characters
          ))

    ])
    def test_sanitize_results(self, name, track, expected_tuple):
        self.assertEqual(mp._sanitize_results(Path('Test'), track), expected_tuple)


class TestMPORG(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.org = mp.MPORG(Path("store"), Path("search"), MagicMock(), [MagicMock()], MagicMock(), MagicMock())

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)
        logging.shutdown()

    def test_get_metadata_with_spotify_results(self):
        metadata = utils.MockTagger(Path("song.mp3"), {'title': ["Song 1"], "artist": ["Artist 1"]})
        self.org.search_spotify = MagicMock(return_value=mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.org.get_fingerprint_metadata = MagicMock()
        self.org.get_fingerprint_spotify_metadata = MagicMock()

        file = MagicMock()
        results, source = self.org.get_metadata(metadata, file)

        self.assertEqual(results, mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.assertEqual(source, mp.TagType.SPOTIFY)
        self.org.search_spotify.assert_called_once_with('Song 1', 'Artist 1')
        self.org.get_fingerprint_metadata.assert_not_called()
        self.org.get_fingerprint_spotify_metadata.assert_not_called()

    def test_get_metadata_with_fingerprint_results(self):
        metadata = utils.MockTagger(Path("song.mp3"), {'title': ["Song 1"], "artist": ["Artist 1"]})
        self.org.search_spotify = MagicMock(return_value=None)
        self.org.get_fingerprint_metadata = MagicMock(
            return_value=mp.FingerprintResult(0, 'suc', mp.Track(track_name="Song 1", track_artists=("Artist 1",))))
        self.org.get_fingerprint_spotify_metadata = MagicMock()

        file = MagicMock()
        results, source = self.org.get_metadata(metadata, file)

        self.assertEqual(results,
                         mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.assertEqual(source, mp.TagType.FINGERPRINTER)
        self.org.search_spotify.assert_called_once_with('Song 1', 'Artist 1')
        self.org.get_fingerprint_metadata.assert_called_once_with(file)
        self.org.get_fingerprint_spotify_metadata.assert_not_called()

    def test_search_spotify(self):
        self.org.sh.search = MagicMock(return_value=mp.Track(track_name="Song 1", track_artists=("Artist 1",)))

        title = 'Song 1'
        artist = 'Artist 1'
        results = self.org.search_spotify(title, artist)

        self.assertEqual(results, mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.org.sh.search.assert_called_once_with(name='Song 1', artist='Artist 1')

    def test_search_spotify_without_results(self):
        self.org.sh.search = MagicMock(return_value=None)

        title = 'Song 1'
        artist = 'Artist 1'
        results = self.org.search_spotify(title, artist)

        self.assertEqual(results, None)
        self.org.sh.search.assert_called_once_with(name='Song 1', artist='Artist 1')

    def test_get_fingerprint_metadata(self):
        fingerprinter = self.org.af[0] = MagicMock()
        fingerprinter.fingerprint.return_value = mp.FingerprintResult(code=0)

        file = MagicMock()
        results = self.org.get_fingerprint_metadata(file)

        self.assertEqual(results, mp.FingerprintResult(0))
        fingerprinter.fingerprint.assert_called_once_with(file)

    def test_get_fingerprint_metadata_without_results(self):
        fingerprinter = self.org.af[0] = MagicMock()
        fingerprinter.fingerprint = MagicMock(return_value=mp.FingerprintResult(code=77))

        file = MagicMock()
        results = self.org.get_fingerprint_metadata(file)

        self.assertEqual(results, None)
        fingerprinter.fingerprint.assert_called_once_with(file)

    def test_get_fingerprint_metadata_spotify_results(self):
        fingerprinter = self.org.af[0] = MagicMock()
        fingerprinter.fingerprint = MagicMock(return_value=mp.FingerprintResult(code=0,
                                                                                type="spotify",
                                                                                results={'spotifyid': 12345}))
        sh = self.org.sh = MagicMock()
        sh.search.side_effect = [None, mp.Track(track_name="Song 1", track_artists=("Artist 1",))]

        tag = utils.MockTagger(Path("song.mp3"), {'title': ["Song 1"], "artist": ["Artist 1"]})

        file = MagicMock()
        results, tagType = self.org.get_metadata(tag, file)

        self.assertEqual(results, mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.assertEqual(tagType, mp.TagType.SPOTIFY)
        fingerprinter.fingerprint.assert_called_once_with(file)

    def test_get_fingerprint_metadata_finger_results(self):
        fingerprinter = self.org.af[0] = MagicMock()
        fingerprinter.fingerprint = MagicMock(return_value=mp.FingerprintResult(code=0,
                                                                                type="fingerprinter",
                                                                                results=mp.Track(track_name="Song 1",
                                                                                                 track_artists=("Artist 1",))))
        sh = self.org.sh = MagicMock()
        sh.search.return_value = None

        tag = utils.MockTagger(Path("song.mp3"), {'title': ["Song 1"], "artist": ["Artist 1"]})

        file = MagicMock()
        results, tagType = self.org.get_metadata(tag, file)

        self.assertEqual(results, mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.assertEqual(tagType, mp.TagType.FINGERPRINTER)
        fingerprinter.fingerprint.assert_called_once_with(file)

    def test_get_metadata_disabled_fingerprinter_no_spotify(self):
        self.org.af = None

        sh = self.org.sh = MagicMock()
        sh.search.return_value = None

        tag = utils.MockTagger(Path("song.mp3"), {'title': ["Song 1"], "artist": ["Artist 1"]})

        file = MagicMock()
        results, tagType = self.org.get_metadata(tag, file)

        self.assertEqual(results, None)
        self.assertEqual(tagType, mp.TagType.METADATA)

    def test_get_fingerprint_spotify_metadata(self):
        self.org.sh.search = MagicMock(return_value=mp.Track(track_name="Song 1", track_artists=("Artist 1",)))

        spotify_id = '12345'
        results = self.org.get_fingerprint_spotify_metadata(spotify_id)

        self.assertEqual(results, mp.Track(track_name="Song 1", track_artists=("Artist 1",)))
        self.org.sh.search.assert_called_once_with(spot_id='12345')

    def test_get_fingerprint_spotify_metadata_without_results(self):
        self.org.sh.search = MagicMock(return_value=None)

        spotify_id = '54321'
        results = self.org.get_fingerprint_spotify_metadata(spotify_id)

        self.assertEqual(results, None)
        self.org.sh.search.assert_called_once_with(spot_id='54321')

    def test_get_location_spotify(self):
        # Test get_location function with TagType.SPOTIFY

        results = mp.Track(album_artists=("Drag",), album_name="mporgTests",
                           track_artists=("Drag",), track_name="spotTest",
                           track_number=1, album_year="2023")

        tags_from = mp.TagType.SPOTIFY
        metadata = utils.MockTagger(Path("song.mp3"))
        file = Path("song.mp3") #Change Tests to use paths

        expected_path = Path("store/Drag/2023 - mporgTests/1. - Drag - spotTest.mp3")
        actual_path = self.org.get_location(results, tags_from, metadata, file)
        self.assertEqual(actual_path, expected_path)

    @parameterized.expand([
        ("All Data", mp.Track(album_artists=("Drag",), album_name="mporgTests",
                              track_artists=("Drag",), track_name="fingerTest",
                              track_number=1, track_year="2023"),
         Path("store/Drag/2023 - mporgTests/Drag - fingerTest.mp3")),
        ("No Track Year", mp.Track(album_artists=("Drag",), album_name="mporgTests",
                                   track_artists=("Drag",), track_name="fingerTest"),
         Path("store/Drag/mporgTests/Drag - fingerTest.mp3"))
    ])
    def test_get_location_with_fingerprinter_tags(self, name, results, expected_path):
        """Test get_location function with TagType.FINGERPRINTER"""
        tags_from = mp.TagType.FINGERPRINTER
        metadata = utils.MockTagger(Path("song.mp3"))
        file = Path("song.mp3")

        actual_path = self.org.get_location(results, tags_from, metadata, file)
        self.assertEqual(actual_path, expected_path)

    @parameterized.expand([
        ("Not Enough Metadata", {'artist': ['Drag'], 'album': 'mporgTests', 'date': '2023', 'tracknumber': '1'},
         Path("store/_TaggingImpossible/song.mp3")),
        ("No Year", {'title': 'metaTest', 'artist': ['Drag'], 'album': 'mporgTests', 'tracknumber': '1'},
         Path("store/Drag/mporgTests/1. - Drag - metaTest.mp3")),
        ("No Track", {'title': 'metaTest', 'artist': ['Drag'], 'album': 'mporgTests', 'date': '2023'},
         Path("store/Drag/2023 - mporgTests/1. - Drag - metaTest.mp3")),
        ("Unknown Artist", {'title': 'metaTest', 'artist': ['Unknown'], 'album': 'mporgTests',
                            'albumartist': ['Drag'], 'date': '2023', 'tracknumber': '2'},
         Path("store/Drag/2023 - mporgTests/2. - metaTest.mp3"))
    ])
    def test_get_location_with_metadata_tags(self, name, metadata, expected_path):
        """Test get_location function with TagType.METADATA"""
        results = mp.Track()
        tags_from = mp.TagType.METADATA
        dummy_tagger = utils.MockTagger(Path("song.mp3"), metadata)
        file = Path("song.mp3")

        actual_path = self.org.get_location(results, tags_from, dummy_tagger, file)
        self.assertEqual(actual_path, expected_path)

    @patch('os.makedirs')
    @patch('shutil.copyfile')
    def test_copy_file(self, mock_copyfile, mock_mkdirs):
        source = Path('source.txt')
        destination = Path('destination.txt')

        self.org.copy_file(source, destination)

        mock_copyfile.assert_called_once_with(source, destination)
        mock_mkdirs.assert_called_once_with(os.path.dirname(destination), exist_ok=True, mode=0o777)

    @patch('mporg.organizer.Tagger')
    def test_update_metadata_from_spotify(self, mock_tagger):
        location = Path('song.mp3')
        results = mp.Track(track_name='Test Track', track_artists=('Test Artist',), album_name='Test Album',
                           album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                           album_artists=('Test Artist',), track_bpm='120', track_key='C',
                           album_genres='Rock')

        self.org.update_metadata_from_spotify(threading.Lock(), location, results)

        mock_tagger.assert_called_once_with(location)
        mock_tagger.return_value.assert_has_calls([
            call.__setitem__('title', 'Test Track'),
            call.__setitem__('artist', 'Test Artist'),
            call.__setitem__('album', 'Test Album'),
            call.__setitem__('date', '2023'),
            call.__setitem__('tracknumber', '1'),
            call.__setitem__('discnumber', '1'),
            call.__setitem__('comment', 'http://example.com'),
            call.__setitem__('source', 'http://example.com'),
            call.__setitem__('albumartist', ('Test Artist',)),
            call.__setitem__('bpm', '120'),
            call.__setitem__('initialkey', 'C'),
            call.__setitem__('genre', 'Rock')
        ])

        mock_tagger.return_value.save.assert_called_once()

    @patch('mporg.organizer.Tagger')
    def test_update_metadata_from_fingerprinter(self, mock_tagger):
        location = Path('song.mp3')
        results = mp.Track(track_name='Test Track', track_artists=('Test Artist',), album_name='Test Album',
                           album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                           album_artists=('Test Artist',), track_bpm='120', track_key='C',
                           album_genres='Rock', track_year='2023')

        self.org.update_metadata_from_fingerprinter(threading.Lock(), location, results)

        mock_tagger.assert_called_once_with(location)
        mock_tagger.return_value.assert_has_calls([
            call.__setitem__('title', 'Test Track'),
            call.__setitem__('artist', 'Test Artist'),
            call.__setitem__('albumartist', ('Test Artist',)),
            call.__setitem__('album', 'Test Album'),
            call.__setitem__('date', '2023'),
            call.__setitem__('genre', 'Rock')
        ])

        mock_tagger.return_value.save.assert_called_once()


class TestMPORGWithMocks(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        setup_logging(0)

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.search = Path("search")
        self.store = Path("store")
        self.searcher = MagicMock()
        self.fingerprinter = [MagicMock()]
        self.lyrics = MagicMock()
        self.pattern = MagicMock()

        # Instantiate MPORG with the mock objects
        self.mporg = mp.MPORG(self.store, self.search, self.searcher,
                              self.fingerprinter, self.pattern, self.lyrics)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)
        logging.shutdown()

    @patch('mporg.organizer.Tagger')
    def test_process_file_spotify(self, tag):
        spotifyRes = mp.Track(track_name='Test Track', track_artists=('Test Artist',), album_name='Test Album',
                              album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                              album_artists=('Test Artist',), track_bpm='120', track_key='C',
                              album_genres='Rock')
        # Set up expected return values and mocks
        self.mporg.get_metadata = MagicMock(
            return_value=(spotifyRes, mp.TagType.SPOTIFY)
        )
        self.mporg.copy_file = MagicMock()
        self.mporg.update_metadata_from_spotify = MagicMock()
        self.mporg.get_lock = MagicMock(return_value=threading.Lock())

        file = Path('song1.mp3')
        root = self.search
        args = (root, file)

        with patch('mporg.organizer.Tagger', return_value=tag):
            self.mporg.process_file(args)

        self.mporg.get_metadata.assert_called_once_with(tag, Path(root, file))
        self.mporg.copy_file.assert_called_once_with(ANY, ANY,  # First two will be locks for src and destination
                                                     Path(root, file),  # Source file path
                                                     self.store / 'Test Artist' / '2023 - Test Album'
                                                     / '1. - Test Artist - Test Track.mp3')
        self.mporg.update_metadata_from_spotify.assert_called_once_with(ANY,
                                                                        self.store / 'Test Artist' / '2023 - Test Album'
                                                                        / '1. - Test Artist - Test Track.mp3',
                                                                        spotifyRes)

    def test_organize(self):
        file_generator_mock = MagicMock(
            return_value=[('/path/to/files', [], ["song1.mp3", "song2.mp3"])]
        )

        self.mporg.get_file_count = MagicMock(return_value=2)
        self.mporg.process_file = MagicMock()
        self.mporg.executor = MockThreadPoolExecutor()
        self.mporg.pattern = False

        with unittest.mock.patch('os.walk', file_generator_mock):
            with unittest.mock.patch('mporg.organizer.get_file_count', self.mporg.get_file_count):
                with unittest.mock.patch('concurrent.futures.wait', MagicMock):
                    self.mporg.organize()

        file_generator_mock.assert_called_once_with(self.search)
        self.mporg.get_file_count.assert_called_once_with(self.search)
        self.mporg.process_file.assert_has_calls([
            unittest.mock.call((Path('/path/to/files'), Path('song1.mp3'))),
            unittest.mock.call((Path('/path/to/files'), Path('song2.mp3')))
        ])


def test():
    if not mporg.CONFIG_DIR.exists():
        mporg.CONFIG_DIR.mkdir()
    unittest.main()


if __name__ == '__main__':
    test()
