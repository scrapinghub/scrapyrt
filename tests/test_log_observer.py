# -*- coding: utf-8 -*-
from six import StringIO

from mock import patch
from twisted.python.log import startLoggingWithObserver, removeObserver
from twisted.trial import unittest

from scrapyrt.log import ScrapyrtFileLogObserver, msg


@patch('twisted.python.log.FileLogObserver.emit')
class TestLogObserver(unittest.TestCase):

    def setUp(self):
        self.file = StringIO()
        self.log_observer = ScrapyrtFileLogObserver(self.file)
        startLoggingWithObserver(self.log_observer.emit, setStdout=False)
        self.event_dict = {'system': 'scrapyrt', 'message': 'blah'}

    def tearDown(self):
        removeObserver(self.log_observer.emit)

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

    def test_unicode_message(self, emit_mock):
        original_message = u'Привет, мир!'
        msg(original_message)
        transformed_message = emit_mock.call_args[0][1]['message'][0]
        self.assertEqual(transformed_message, original_message.encode('utf-8'))
