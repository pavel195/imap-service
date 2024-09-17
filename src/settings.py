from pathlib import Path
from logging import config as logconfig
from src import app

Path(app.config.LOG_DIR).mkdir(parents=True, exist_ok=True)
Path(app.config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "InfoFilter": {
            "()": "src.logger.InfoFilter",
        },
        "HTTPFilter": {
            "()": "src.logger.HTTPFilter",
        },
        "DebugFilter": {
            "()": "src.logger.DebugFilter",
        },
        "WarningFilter": {
            "()": "src.logger.WarningFilter",
        },
        "ErrorFilter": {
            "()": "src.logger.ErrorFilter",
        },
    },
    "formatters": {
        "default": {
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "format": "%(asctime)s - %(message)s",
        },
        "simple": {
            "()": "src.logger.CustomFormatter",
            "datefmt": "%d-%m-%Y %H:%M:%S",
            "format": "%(asctime)s - {}%(message)s{}",
        },
        "verbose": {
            "()": "src.logger.CustomFormatter",
            "datefmt": "%d-%m-%Y %H:%M:%S",
            "format": "%(asctime)s - {}%(message)s{} %(exc_info)s %(name)s:%(lineno)d %(exc_info)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "format": """
                    levelno: %(levelno)s
                    levelname: %(levelname)s
                    asctime: %(asctime)s
                    name: %(name)s
                    module: %(module)s
                    lineno: %(lineno)d
                    message: %(message)s
                    created: %(created)f
                    filename: %(filename)s
                    funcName: %(funcName)s
                    msec: %(msecs)d
                    pathname: %(pathname)s
                    process: %(process)d
                    processName: %(processName)s
                    relativeCreated: %(relativeCreated)d
                    thread: %(thread)d
                    threadName: %(threadName)s
                    exc_info: %(exc_info)s
                """,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "filters": ["InfoFilter"],
            "formatter": "simple",
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "logfile": {
            "filters": ["InfoFilter"],
            "formatter": "default",
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": app.config.ENCONING,
            "filename": Path(app.config.LOG_DIR, app.config.INFO_LOG_FILENAME),
            "maxBytes": 100 * 2**10,
            "backupCount": 2,
        },
        "debug": {
            "filters": ["DebugFilter"],
            "formatter": "default",
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": app.config.ENCONING,
            "filename": Path(app.config.LOG_DIR, app.config.DEBUG_LOG_FILENAME),
            "maxBytes": 100 * 2**10,
            "backupCount": 2,
            "delay": True,
        },
        "warning": {
            "filters": ["WarningFilter"],
            "formatter": "verbose",
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": app.config.ENCONING,
            "filename": Path(app.config.LOG_DIR, app.config.WARNING_LOG_FILENAME),
            "maxBytes": 100 * 2**10,
            "backupCount": 2,
            "delay": True,
        },
        "error": {
            "filters": ["ErrorFilter"],
            "formatter": "verbose",
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": app.config.ENCONING,
            "filename": Path(app.config.LOG_DIR, app.config.ERROR_LOG_FILENAME),
            "maxBytes": 100 * 2**10,
            "backupCount": 2,
            "delay": True,
        },
        "json": {
            "filters": ["ErrorFilter"],
            "formatter": "json",
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": app.config.ENCONING,
            "filename": Path(app.config.LOG_DIR, app.config.ERROR_LOG_FILENAME),
            "maxBytes": 100 * 2**10,
            "backupCount": 2,
            "delay": True,
        },
    },
    "loggers": {
        "debug": {
            "level": "DEBUG",
            "handlers": ["console", "debug"],
            "propagate": False,
        },
        "asyncio": {
            "level": "WARNING",
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": [
            "console",
            "logfile",
            "warning",
            "debug",
            "error",
            # "json",
        ],
    },
}

logconfig.dictConfig(LOGGING)

try:
    from src import settings_local
finally:
    pass

