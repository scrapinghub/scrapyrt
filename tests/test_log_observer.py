# -*- coding: utf-8 -*-
import StringIO

from mock import patch
from twisted.trial import unittest

from scrapyrt.log import ScrapyrtFileLogObserver


@patch('twisted.python.log.FileLogObserver.emit')
class TestLogObserver(unittest.TestCase):

    def setUp(self):
        self.file = StringIO.StringIO()
        self.log_observer = ScrapyrtFileLogObserver(self.file)
        self.event_dict = {'system': 'scrapyrt', 'message': 'blah'}

    def test_emit_called(self, emit_mock):
        self.log_observer.emit(self.event_dict)
        self.assertTrue(emit_mock.called)

    def test_scrapy_filtering(self, emit_mock):
        self.event_dict['system'] = 'scrapy'
        self.log_observer.emit(self.event_dict)
        self.assertFalse(emit_mock.called)

    def test_log_start_messages_filtering(self, emit_mock):
        self.event_dict['system'] = 'HTTPChannel'
        self.event_dict['message'] = 'Log opened.'
        self.log_observer.emit(self.event_dict)
        self.assertFalse(emit_mock.called)

        self.event_dict['system'] = 'other'
        self.log_observer.emit(self.event_dict)
        self.assertTrue(emit_mock.called)
