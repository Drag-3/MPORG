from mporg import organizer, spotify_searcher, audio_fingerprinter


class MockTagger(organizer.Tagger):
    def __init__(self, file, fake=None):
        if fake is None:
            fake = dict()
        self.file = file
        self._fake_mutagen = fake

    def get(self, key, value=None):
        return self._fake_mutagen.get(key, value)

    def __getitem__(self, item):
        return self._fake_mutagen.__getitem__(item)

    def __setitem__(self, key, value):
        self._fake_mutagen.__setitem__(key, value)

    def add_tags(self):
        pass

    def save(self):
        pass


class MockSearcher:
    def search(self, name: str = None, artist: str = None, spot_id: str = None):
        return spotify_searcher.Track(track_name='Test Track', track_artists=['Test Artist'], album_name='Test Album',
                                      album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                                      album_artists=['Test Artist'], track_bpm='120', track_key='C',
                                      album_genres='Rock')


class MockFingerprinter(audio_fingerprinter.Fingerprinter):
    def fingerprint(self, path):
        return audio_fingerprinter.FingerprintResult(
            0, "spotify",
            spotify_searcher.Track(track_name='Test Track', track_artists=['Test Artist'], album_name='Test Album',
                                   album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                                   album_artists=['Test Artist'], track_bpm='120', track_key='C',
                                   album_genres='Rock')
        )


class MockPool:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def apply_async(self, func, args, callback):
        result = func(*args)
        callback(result)

    def close(self):
        pass

    def join(self):
        pass
