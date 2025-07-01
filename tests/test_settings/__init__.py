from unittest.mock import patch

import pytest
from twisted.trial import unittest

from scrapyrt.conf import Settings

from . import default_settings, settings


class TestSettings(unittest.TestCase):
    @patch("scrapyrt.conf.default_settings", default_settings)
    def setUp(self):
        self.settings = Settings()

    def test_getattr(self):
        assert self.settings.A == "A"
        assert self.settings.TEST == [1, 2, 3]

        # invalid (or hidden in this way) settings should not be visible
        with pytest.raises(AttributeError):
            self.settings._HIDDEN  # noqa: B018
        with pytest.raises(AttributeError):
            self.settings.hidden  # noqa: B018
        with pytest.raises(AttributeError):
            self.settings.HiDdEn  # noqa: B018

    def test_setmodule(self):
        assert self.settings.A == "A"
        self.settings.setmodule(settings)
        assert self.settings.A == "B"
        assert self.settings.TEST == [1, 2, 3]

    def test_setmodule_string(self):
        assert self.settings.A == "A"
        self.settings.setmodule("tests.test_settings.settings")
        assert self.settings.A == "B"
        assert self.settings.TEST == [1, 2, 3]

    def test_set(self):
        assert self.settings.A == "A"
        self.settings.set("A", "C")
        assert self.settings.A == "C"

        assert self.settings.TEST == [1, 2, 3]
        self.settings.set("TEST", [])
        assert self.settings.TEST == []

        # invalid setting names
        self.settings.set("_HIDDEN", 1)
        with pytest.raises(AttributeError):
            self.settings._HIDDEN  # noqa: B018
        self.settings.set("hidden", 1)
        with pytest.raises(AttributeError):
            self.settings.hidden  # noqa: B018
        self.settings.set("HiDdEn", 1)
        with pytest.raises(AttributeError):
            self.settings.HiDdEn  # noqa: B018

    def test_freeze(self):
        assert self.settings.A == "A"
        self.settings.set("A", "D")
        assert self.settings.A == "D"
        assert not self.settings.frozen
        self.settings.freeze()
        assert self.settings.frozen
        with pytest.raises(TypeError):
            self.settings.set("A", "E")
