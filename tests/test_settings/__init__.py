# -*- coding: utf-8 -*-
from mock import patch
from twisted.trial import unittest

from scrapyrt.conf import Settings

from . import default_settings


class TestSettings(unittest.TestCase):

    @patch('scrapyrt.conf.default_settings', default_settings)
    def setUp(self):
        self.settings = Settings()

    def test_getattr(self):
        self.assertEqual(self.settings.A, 'A')
        self.assertEqual(self.settings.TEST, [1, 2, 3])

        # invalid (or hidden in this way) settings should not be visible
        self.assertRaises(AttributeError, getattr, self.settings, '_HIDDEN')
        self.assertRaises(AttributeError, getattr, self.settings, 'hidden')
        self.assertRaises(AttributeError, getattr, self.settings, 'HiDdEn')

    def test_setmodule(self):
        from . import settings
        self.assertEqual(self.settings.A, 'A')
        self.settings.setmodule(settings)
        self.assertEqual(self.settings.A, 'B')
        self.assertEqual(self.settings.TEST, [1, 2, 3])

    def test_setmodule_string(self):
        self.assertEqual(self.settings.A, 'A')
        self.settings.setmodule('tests.test_settings.settings')
        self.assertEqual(self.settings.A, 'B')
        self.assertEqual(self.settings.TEST, [1, 2, 3])

    def test_set(self):
        self.assertEqual(self.settings.A, 'A')
        self.settings.set('A', 'C')
        self.assertEqual(self.settings.A, 'C')

        self.assertEqual(self.settings.TEST, [1, 2, 3])
        self.settings.set('TEST', [])
        self.assertEqual(self.settings.TEST, [])

        # invalid setting names
        self.settings.set('_HIDDEN', 1)
        self.assertRaises(AttributeError, getattr, self.settings, '_HIDDEN')
        self.settings.set('hidden', 1)
        self.assertRaises(AttributeError, getattr, self.settings, 'hidden')
        self.settings.set('HiDdEn', 1)
        self.assertRaises(AttributeError, getattr, self.settings, 'HiDdEn')

    def test_freeze(self):
        self.assertEqual(self.settings.A, 'A')
        self.settings.set('A', 'D')
        self.assertEqual(self.settings.A, 'D')
        self.assertFalse(self.settings.frozen)
        self.settings.freeze()
        self.assertTrue(self.settings.frozen)
        self.assertRaises(TypeError, self.settings.set, 'A', 'E')
