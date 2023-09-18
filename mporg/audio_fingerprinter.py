import json
import logging
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

import diskcache
from acrcloud.recognizer import ACRCloudRecognizer
from ftfy import ftfy

from mporg import CONFIG_DIR
from mporg.types import Track

logging.getLogger("__main." + __name__)
logging.propagate = True


class Fingerprinter:
    """
    Abstract class for fingerprinting audio files
    """

    @abstractmethod
    def fingerprint(self, path_to_fingerprint: Path) -> "FingerprintResult":
        pass


@dataclass
class FingerprintResult:
    code: int = None # 0 - success
    type: str = None # "track" - information on the track, "spotify" - spotify id, "fail" - failed to fingerprint
    results: Track | dict = None # Track object or dict with spotify id
