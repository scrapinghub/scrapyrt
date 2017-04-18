# -*- coding: utf-8 -*-
import six
from copy import deepcopy
from importlib import import_module

from . import default_settings


class Settings(object):

    def __init__(self):
        self.setmodule(default_settings)

    def setmodule(self, module):
        if isinstance(module, six.string_types):
            module = import_module(module)
        for setting in dir(module):
            self.set(setting, getattr(module, setting))

    def __setattr__(self, key, value):
        if self.frozen:
            raise TypeError("Trying to modify a frozen Settings object")
        return super(Settings, self).__setattr__(key, value)

    def set(self, name, value):
        if not name.startswith('_') and name.isupper():
            # Deepcopy objects here, or we will have issues with mutability,
            # like changing mutable object stored in settings leads to
            # change of object in default_settings module.
            setattr(self, name, deepcopy(value))

    def freeze(self):
        self._frozen = True

    @property
    def frozen(self):
        return bool(getattr(self, '_frozen', False))


settings = Settings()
