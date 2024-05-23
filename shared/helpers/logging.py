import logging

from colorlog import ColoredFormatter

logger_initialized: logging.Logger | None = None


def initlogger() -> logging.Logger:
    global logger_initialized
    if logger_initialized:
        return logger_initialized

    logger = logging.getLogger('dreadrise')
    logger.setLevel('INFO')

    console = logging.StreamHandler()
    console.setLevel('DEBUG')
    console.setFormatter(
        ColoredFormatter('%(log_color)s[%(asctime)s] [%(levelname)s] %(name)s: %(message)s', '%H:%M:%S'))
    logger.addHandler(console)
    logger_initialized = logger
    return logger
