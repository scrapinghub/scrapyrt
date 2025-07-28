import json
from unittest.mock import MagicMock, patch

from twisted.internet.defer import fail, succeed
from twisted.python.failure import Failure
from twisted.trial import unittest
from twisted.web import server
from twisted.web.error import Error, UnsupportedMethod
from twisted.web.server import Request

from scrapyrt.resources import ServiceResource


class TestServiceResource(unittest.TestCase):
    def setUp(self):
        self.resource = ServiceResource()
        self.request = MagicMock(spec=Request)
        self.request.code = 200

        def set_code(code):
            self.request.code = code

        self.request.setResponseCode.side_effect = set_code


@patch("scrapyrt.resources.log.err")
@patch("twisted.web.resource.Resource.render")
class TestRender(TestServiceResource):
    def setUp(self):
        super().setUp()
        self.request_write_values: list[bytes] = []

        def request_write(value):
            self.request_write_values.append(value)

        self.request.write.side_effect = request_write

    def test_render_ok(self, render_mock, log_err_mock):
        render_mock.return_value = {"status": "ok"}
        result = self.resource.render(self.request)
        obj = json.loads(result.decode("utf8"))
        assert "status" in obj
        assert obj["status"] == "ok"
        assert not log_err_mock.called

    def test_render_exception(self, render_mock, log_err_mock):
        exc = Exception("boom")
        render_mock.side_effect = exc
        result = self.resource.render(self.request)
        obj = json.loads(result.decode("utf8"))
        assert log_err_mock.called
        assert obj["status"] == "error"
        assert obj["message"] == str(exc)
        assert obj["code"] == 500

    def test_render_deferred_succeed(self, render_mock, log_err_mock):
        render_mock.return_value = succeed({"status": "ok"})
        result = self.resource.render(self.request)
        assert result == server.NOT_DONE_YET
        assert self.request.write.called
        assert self.request.finish.called
        assert len(self.request_write_values) == 1
        obj = json.loads(self.request_write_values[0].decode("utf8"))
        assert "status" in obj
        assert obj["status"] == "ok"
        assert not log_err_mock.called

    def test_render_deferred_fail(self, render_mock, log_err_mock):
        exc = Exception("boom")
        render_mock.return_value = fail(exc)
        result = self.resource.render(self.request)
        assert result == server.NOT_DONE_YET
        assert self.request.write.called
        assert self.request.finish.called
        assert len(self.request_write_values) == 1
        obj = json.loads(self.request_write_values[0].decode("utf8"))
        assert obj["status"] == "error"
        assert obj["message"] == str(exc)
        assert obj["code"] == 500
        assert log_err_mock.called


@patch("twisted.python.log.msg")
class TestHandleErrors(TestServiceResource):
    def _assert_log_err_called(self, log_msg_mock, failure):
        log_msg_mock.call_count = 1
        _, kwargs = log_msg_mock.call_args
        assert kwargs["isError"] == 1
        assert kwargs["system"] == "scrapyrt"
        if isinstance(failure, Failure):
            assert kwargs["failure"] == failure
        else:
            assert kwargs["failure"].value == failure

    def test_exception(self, log_msg_mock):
        try:
            raise Exception("blah")  # pylint: disable=broad-exception-raised
        except Exception as e:
            result = self.resource.handle_error(e, self.request)
            exc = e
        assert self.request.code == 500
        assert result["message"] == str(exc)  # pylint: disable=used-before-assignment
        self._assert_log_err_called(log_msg_mock, exc)

    def test_failure(self, log_msg_mock):
        exc = Exception("blah")
        failure = Failure(exc)
        result = self.resource.handle_error(failure, self.request)
        assert self.request.code == 500
        assert result["message"] == str(exc)
        self._assert_log_err_called(log_msg_mock, failure)

    def test_error_400(self, log_msg_mock):
        exc = Error(400, b"blah_400")
        result = self.resource.handle_error(exc, self.request)
        assert self.request.code == 400
        assert not log_msg_mock.called
        assert result["message"] == exc.message

    def test_error_403(self, log_msg_mock):
        exc = Error(403, b"blah_403")
        result = self.resource.handle_error(exc, self.request)
        assert self.request.code == 403
        assert not log_msg_mock.called
        assert result["message"] == exc.message

    def test_error_not_supported_method(self, log_msg_mock):
        exc = UnsupportedMethod(["GET"])
        result = self.resource.handle_error(exc, self.request)
        assert self.request.code == 405
        assert not log_msg_mock.called
        assert "GET" in result["message"]


class TestFormatErrorResponse(TestServiceResource):
    def test_format_error_response(self):
        code = 400
        self.request.code = code
        exc = Error(code, b"blah")
        response = self.resource.format_error_response(exc, self.request)
        assert response["status"] == "error"
        assert response["message"] == exc.message
        assert response["code"] == code


class TestRenderObject(TestServiceResource):
    def setUp(self):
        super().setUp()
        self.obj = {"status": "ok", "key": "value"}
        self.headers: list[tuple[bytes, bytes]] = []
        self.request = MagicMock(spec=Request)

        def add_header(name, value):
            self.headers.append((name, value))

        self.request.setHeader.side_effect = add_header

    def test_render_object(self):
        result = self.resource.render_object(self.obj, self.request)
        set_header_mock = self.request.setHeader
        assert set_header_mock.call_count == 5
        set_header_mock.assert_any_call(b"Content-Type", b"application/json")
        set_header_mock.assert_any_call(b"Access-Control-Allow-Origin", b"*")
        set_header_mock.assert_any_call(
            b"Access-Control-Allow-Headers",
            b"X-Requested-With",
        )
        set_header_mock.assert_any_call(b"Content-Length", str(len(result)).encode())
        headers = dict(self.headers)
        assert b"Access-Control-Allow-Methods" in headers
        assert headers[b"Access-Control-Allow-Methods"] == b""
        for key, value in self.obj.items():
            assert key.encode("utf8") in result
            assert value.encode("utf8") in result

    def _test_access_control_allow_methods_header(self):
        headers = dict(self.headers)
        assert b"Access-Control-Allow-Methods" in headers
        access_control_allow_methods = headers[b"Access-Control-Allow-Methods"]
        assert self.resource.allowedMethods == tuple(
            s.strip() for s in access_control_allow_methods.split(b",")
        )

    def test_access_control_allow_methods_header_get(self):
        self.resource.allowedMethods = (b"GET",)
        self.resource.render_object(self.obj, self.request)
        self._test_access_control_allow_methods_header()

    def test_access_control_allow_methods_header_get_post(self):
        self.resource.allowedMethods = (b"GET", b"POST")
        self.resource.render_object(self.obj, self.request)
        self._test_access_control_allow_methods_header()
