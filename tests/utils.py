from concurrent.futures import Future, ThreadPoolExecutor

import mporg.types
from mporg import audio_fingerprinter


class MockTagger(mporg.types.Tagger):
    def __init__(self, file, fake=None):
        if fake is None:
            fake = dict()
        self.file = file
        self._fake_mutagen = fake

    def get(self, key, value=None):
        return self._fake_mutagen.get(key, value)

    def __getitem__(self, item):
        if item in self._fake_mutagen:
            return self._fake_mutagen[item]
        return "XXX"

    def __setitem__(self, key, value):
        self._fake_mutagen.__setitem__(key, value)

    def add_tags(self):
        pass

    def save(self):
        pass


class MockSearcher:
    def search(self, name: str = None, artist: str = None, spot_id: str = None):
        return mporg.types.Track(track_name='Test Track', track_artists=['Test Artist'], album_name='Test Album',
                                 album_year='2023', track_number=1, track_disk=1, track_url='http://example.com',
                                 album_artists=['Test Artist'], track_bpm='120', track_key='C',
                                 album_genres='Rock')


class MockFingerprinter(audio_fingerprinter.Fingerprinter):
    def fingerprint(self, path):
        return audio_fingerprinter.FingerprintResult(
            0, "spotify",
            mporg.types.Track(track_name='Test Track', track_artists=['Test Artist'], album_name='Test Album',
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


class MockThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def submit(self, func, *args, **kwargs):
        return MockFuture(func(*args, **kwargs))


class MockFuture(Future):
    def __init__(self, result=None):
        super().__init__()
        self.f_result = result
        self.callback = None

    def set_result(self, result):
        self.f_result = result
        super().set_result(result)

    def result(self, timeout=None):
        self.set_result(self.f_result)
        return self.result

    def add_done_callback(self, func):
        func(self)

