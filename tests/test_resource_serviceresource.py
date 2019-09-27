# -*- coding: utf-8 -*-
import json

from mock import MagicMock, patch
from twisted.internet.defer import succeed, fail
from twisted.python.failure import Failure
from twisted.web import server
from twisted.web.error import Error, UnsupportedMethod
from twisted.web.server import Request
from twisted.trial import unittest

from scrapyrt.resources import ServiceResource


class TestServiceResource(unittest.TestCase):

    def setUp(self):
        self.resource = ServiceResource()
        self.request = MagicMock(spec=Request)
        self.request.code = 200

        def set_code(code):
            self.request.code = code

        self.request.setResponseCode.side_effect = set_code


@patch('scrapyrt.resources.log.err')
@patch('twisted.web.resource.Resource.render')
class TestRender(TestServiceResource):

    def setUp(self):
        super(TestRender, self).setUp()
        self.request_write_values = []

        def request_write(value):
            self.request_write_values.append(value)

        self.request.write.side_effect = request_write

    def test_render_ok(self, render_mock, log_err_mock):
        render_mock.return_value = {'status': 'ok'}
        result = self.resource.render(self.request)
        obj = json.loads(result.decode("utf8"))
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], 'ok')
        self.assertFalse(log_err_mock.called)

    def test_render_exception(self, render_mock, log_err_mock):
        exc = Exception('boom')
        render_mock.side_effect = exc
        result = self.resource.render(self.request)
        obj = json.loads(result.decode("utf8"))
        self.assertTrue(log_err_mock.called)
        self.assertEqual(obj['status'], 'error')
        self.assertEqual(obj['message'], str(exc))
        self.assertEqual(obj['code'], 500)

    def test_render_deferred_succeed(self, render_mock, log_err_mock):
        render_mock.return_value = succeed({'status': 'ok'})
        result = self.resource.render(self.request)
        self.assertEqual(result, server.NOT_DONE_YET)
        self.assertTrue(self.request.write.called)
        self.assertTrue(self.request.finish.called)
        self.assertEqual(len(self.request_write_values), 1)
        obj = json.loads(self.request_write_values[0].decode("utf8"))
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], 'ok')
        self.assertFalse(log_err_mock.called)

    def test_render_deferred_fail(self, render_mock, log_err_mock):
        exc = Exception('boom')
        render_mock.return_value = fail(exc)
        result = self.resource.render(self.request)
        self.assertEqual(result, server.NOT_DONE_YET)
        self.assertTrue(self.request.write.called)
        self.assertTrue(self.request.finish.called)
        self.assertEqual(len(self.request_write_values), 1)
        obj = json.loads(self.request_write_values[0].decode("utf8"))
        self.assertEqual(obj['status'], 'error')
        self.assertEqual(obj['message'], str(exc))
        self.assertEqual(obj['code'], 500)
        self.assertTrue(log_err_mock.called)


@patch('twisted.python.log.msg')
class TestHandleErrors(TestServiceResource):

    def setUp(self):
        super(TestHandleErrors, self).setUp()

    def _assert_log_err_called(self, log_msg_mock, failure):
        log_msg_mock.call_count = 1
        _, kwargs = log_msg_mock.call_args
        self.assertEqual(kwargs['isError'], 1)
        self.assertEqual(kwargs['system'], 'scrapyrt')
        if isinstance(failure, Failure):
            self.assertEqual(kwargs['failure'], failure)
        else:
            self.assertEqual(kwargs['failure'].value, failure)

    def test_exception(self, log_msg_mock):
        try:
            raise Exception('blah')
        except Exception as e:
            result = self.resource.handle_error(e, self.request)
            exc = e
        self.assertEqual(self.request.code, 500)
        self.assertEqual(result['message'], str(exc))
        self._assert_log_err_called(log_msg_mock, exc)

    def test_failure(self, log_msg_mock):
        exc = Exception('blah')
        failure = Failure(exc)
        result = self.resource.handle_error(failure, self.request)
        self.assertEqual(self.request.code, 500)
        self.assertEqual(result['message'], str(exc))
        self._assert_log_err_called(log_msg_mock, failure)

    def test_error_400(self, log_msg_mock):
        exc = Error('400', 'blah_400')
        result = self.resource.handle_error(exc, self.request)
        self.assertEqual(self.request.code, 400)
        self.assertFalse(log_msg_mock.called)
        self.assertEqual(result['message'], exc.message)

    def test_error_403(self, log_msg_mock):
        exc = Error('403', 'blah_403')
        result = self.resource.handle_error(exc, self.request)
        self.assertEqual(self.request.code, 403)
        self.assertFalse(log_msg_mock.called)
        self.assertEqual(result['message'], exc.message)

    def test_error_not_supported_method(self, log_msg_mock):
        exc = UnsupportedMethod(['GET'])
        result = self.resource.handle_error(exc, self.request)
        self.assertEqual(self.request.code, 405)
        self.assertFalse(log_msg_mock.called)
        self.assertIn('GET', result['message'])


class TestFormatErrorResponse(TestServiceResource):

    def test_format_error_response(self):
        code = 400
        self.request.code = code
        exc = Error(str(code), 'blah')
        response = self.resource.format_error_response(exc, self.request)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['message'], exc.message)
        self.assertEqual(response['code'], code)


class TestRenderObject(TestServiceResource):

    def setUp(self):
        super(TestRenderObject, self).setUp()
        self.obj = {'status': 'ok', 'key': 'value'}
        self.headers = []
        self.request = MagicMock(spec=Request)

        def add_header(name, value):
            self.headers.append((name, value))

        self.request.setHeader.side_effect = add_header

    def test_render_object(self):
        result = self.resource.render_object(self.obj, self.request)
        set_header_mock = self.request.setHeader
        self.assertEqual(set_header_mock.call_count, 5)
        set_header_mock.assert_any_call('Content-Type', 'application/json')
        set_header_mock.assert_any_call('Access-Control-Allow-Origin', '*')
        set_header_mock.assert_any_call('Access-Control-Allow-Headers',
                                        'X-Requested-With')
        set_header_mock.assert_any_call('Content-Length', str(len(result)))
        # request.setHeader('Access-Control-Allow-Methods',
        #                   ', '.join(getattr(self, 'allowedMethods', [])))
        headers = dict(self.headers)
        self.assertIn('Access-Control-Allow-Methods', headers)
        self.assertEqual(headers['Access-Control-Allow-Methods'], '')
        for key, value in self.obj.items():
            self.assertIn(key.encode("utf8"), result)
            self.assertIn(value.encode("utf8"), result)

    def _test_access_control_allow_methods_header(self):
        headers = dict(self.headers)
        self.assertIn('Access-Control-Allow-Methods', headers)
        access_control_allow_methods = headers['Access-Control-Allow-Methods']
        self.assertEqual(
            self.resource.allowedMethods,
            [s.strip() for s in access_control_allow_methods.split(',')]
        )

    def test_access_control_allow_methods_header_get(self):
        self.resource.allowedMethods = ['GET']
        self.resource.render_object(self.obj, self.request)
        self._test_access_control_allow_methods_header()

    def test_access_control_allow_methods_header_get_post(self):
        self.resource.allowedMethods = ['GET', 'POST']
        self.resource.render_object(self.obj, self.request)
        self._test_access_control_allow_methods_header()
