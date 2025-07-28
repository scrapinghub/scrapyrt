from __future__ import annotations

from copy import deepcopy
from importlib import import_module

from . import default_settings


class Settings:
    CRAWL_MANAGER: str
    DEBUG: bool
    DEFAULT_ERRBACK_NAME: str | None
    LOG_DIR: str
    LOG_ENCODING: str
    LOG_FILE: str | None
    PROJECT_SETTINGS: str | None
    RESOURCES: dict[str, str]
    SERVICE_ROOT: str
    SPIDER_LOG_FILE_TIMEFORMAT: str
    TIMEOUT_LIMIT: int
    TWISTED_REACTOR: str | None

    def __init__(self):
        self.frozen = False
        self.setmodule(default_settings)

    def setmodule(self, module):
        if isinstance(module, str):
            module = import_module(module)
        for setting in dir(module):
            self.set(setting, getattr(module, setting))

    def __setattr__(self, key, value):
        if key == "frozen":
            super().__setattr__(key, value)
            return None
        if self.frozen:
            raise TypeError("Trying to modify a frozen Settings object")
        return super().__setattr__(key, value)

    def set(self, name, value):
        if not name.startswith("_") and name.isupper():
            # Deepcopy objects here, or we will have issues with mutability,
            # like changing mutable object stored in settings leads to
            # change of object in default_settings module.
            setattr(self, name, deepcopy(value))

    def freeze(self):
        self.frozen = True


app_settings = Settings()
