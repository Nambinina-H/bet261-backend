import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("bet261")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = TimedRotatingFileHandler(
        "logs/app.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)
    return logger
