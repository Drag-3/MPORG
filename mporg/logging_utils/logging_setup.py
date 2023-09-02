import logging
import os
from logging.handlers import RotatingFileHandler

from mporg import CONFIG_DIR, LOG_DIR
from mporg.logging_utils.custom_handlers import ColoredFormatter, ColorHandler

LOG_LEVEL_MAPPING = {
    1: logging.DEBUG,
    2: logging.INFO,
    3: logging.WARNING,
    4: logging.ERROR,
    5: logging.CRITICAL,
}


def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    https://stackoverflow.com/a/35804945
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


def setup_logging(log_lvl_input: int):
    # Set up logging
    logger = logging.getLogger()

    if log_lvl_input < 1:
        log_level_input = 1
    elif log_lvl_input > 5:
        log_level_input = 5

    log_lvl = log_lvl_input * 10
    logger.setLevel(1)

    if not CONFIG_DIR.exists():
        os.mkdir(CONFIG_DIR)
        logging.debug(f"Creating {CONFIG_DIR}")
    if not LOG_DIR.exists():
        LOG_DIR.mkdir()

    addLoggingLevel("TOP", logging.CRITICAL - 1)
    # Create a formatter
    c_formatter = ColoredFormatter(
        "%(asctime)s - %(module)s - %(levelname)s - %(message)s"
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(module)s - %(levelname)s - %(message)s"
    )
    # Create a file handler and set the formatter
    file_handler = RotatingFileHandler(
        LOG_DIR / "MPORG.log", maxBytes=1000000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG if log_lvl <= logging.DEBUG else logging.INFO)
    file_handler.setFormatter(formatter)

    # Create a console handler and set the formatter
    console_handler = ColorHandler()
    # console_handler.stream = sys.stderr
    console_handler.setLevel(log_lvl)
    console_handler.setFormatter(c_formatter)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
