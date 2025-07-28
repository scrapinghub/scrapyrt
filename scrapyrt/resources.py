import json
from urllib.parse import unquote

from scrapy.utils.misc import load_object
from scrapy.utils.python import to_bytes
from scrapy.utils.serialize import ScrapyJSONEncoder
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.web import resource, server
from twisted.web.error import Error, UnsupportedMethod

from . import log
from .conf import app_settings
from .utils import extract_scrapy_request_args


class AdaptedScrapyJSONEncoder(ScrapyJSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return o.decode("utf8")
        return super().default(o)


class ServiceResource(resource.Resource):
    json_encoder = AdaptedScrapyJSONEncoder()

    def __init__(self, root=None):
        super().__init__()
        self.root = root

    def render(self, request):
        try:
            result = resource.Resource.render(self, request)
        except Exception as e:  # pylint: disable=broad-exception-caught
            result = self.handle_error(e, request)

        if not isinstance(result, Deferred):
            return self.render_object(result, request)

        # deferred result - add appropriate callbacks and errbacks
        result.addErrback(self.handle_error, request)

        def finish_request(obj):
            request.write(self.render_object(obj, request))
            request.finish()

        result.addCallback(finish_request)
        return server.NOT_DONE_YET

    def handle_error(self, exception_or_failure, request):
        """Override this method to add custom exception handling.

        :param request: twisted.web.server.Request
        :param exception_or_failure: Exception or
            twisted.python.failure.Failure
        :return: dict which will be converted to JSON error response

        """
        failure = None
        if isinstance(exception_or_failure, Exception):
            exception: BaseException = exception_or_failure
        else:
            assert isinstance(exception_or_failure, Failure)
            assert exception_or_failure.value is not None
            exception = exception_or_failure.value
            failure = exception_or_failure
        if request.code == 200:  # noqa: PLR2004
            # Default code - means that error wasn't handled
            if isinstance(exception, UnsupportedMethod):
                request.setResponseCode(405)
            elif isinstance(exception, Error):
                code = int(exception.status)
                request.setResponseCode(code)
            else:
                request.setResponseCode(500)
            if request.code == 500:  # noqa: PLR2004
                log.err(failure)
        return self.format_error_response(exception, request)

    def format_error_response(self, exception, request):
        # Python exceptions don't have message attribute in Python 3+ anymore.
        # Twisted HTTP Error objects still have 'message' attribute even in 3+
        # and they fail on str(exception) call.
        msg = exception.message if hasattr(exception, "message") else str(exception)

        return {"status": "error", "message": msg, "code": request.code}

    def render_object(self, obj, request):
        response = self.json_encoder.encode(obj) + "\n"
        request.setHeader(b"Content-Type", b"application/json")
        request.setHeader(b"Access-Control-Allow-Origin", b"*")
        request.setHeader(
            b"Access-Control-Allow-Methods",
            b", ".join(getattr(self, "allowedMethods", [])),
        )
        request.setHeader(b"Access-Control-Allow-Headers", b"X-Requested-With")
        request.setHeader(b"Content-Length", str(len(response)).encode())
        return response.encode("utf-8")


class RealtimeApi(ServiceResource):
    def __init__(self, **kwargs):
        super().__init__(self)
        for route, resource_path in app_settings.RESOURCES.items():
            resource_cls = load_object(resource_path)
            self.putChild(to_bytes(route), resource_cls(self, **kwargs))


class CrawlResource(ServiceResource):
    isLeaf = True
    allowedMethods = (b"GET", b"POST")

    def render_GET(self, request, **kwargs):  # pylint: disable=invalid-name
        """Request querysting must contain following keys: url, spider_name.

        At the moment kwargs for scrapy request are not supported in GET.
        They are supported in POST handler.
        """
        api_params = {
            name.decode("utf-8"): value[0].decode("utf-8")
            for name, value in request.args.items()
        }
        scrapy_request_args = extract_scrapy_request_args(api_params, raise_error=False)
        self.validate_options(scrapy_request_args, api_params)

        return self.prepare_crawl(api_params, scrapy_request_args, **kwargs)

    def render_POST(self, request, **kwargs):  # pylint: disable=invalid-name
        """
        :param request:
            body should contain JSON

        Required keys in JSON posted:

        :spider_name: string
            name of spider to be scheduled.

        :request: json object
            request to be scheduled with spider.
            Note: request must contain url for spider.
            It may contain kwargs to scrapy request.

        """
        request_body = request.content.getvalue()
        try:
            api_params = json.loads(request_body)
        except Exception as e:
            message = f"Invalid JSON in POST body. {e}".encode()
            raise Error(400, message=message) from e

        log.msg(f"{api_params}")
        if api_params.get("spider_start") or api_params.get("start_requests"):
            # start requests passed so 'request' argument is optional
            _request = api_params.get("request", {})
        else:
            # no spider_start/start_requests, 'request' is required
            _request = self.get_required_argument(api_params, "request")
        try:
            scrapy_request_args = extract_scrapy_request_args(
                _request,
                raise_error=True,
            )
        except ValueError as e:
            raise Error(400, str(e).encode()) from e

        self.validate_options(scrapy_request_args, api_params)
        return self.prepare_crawl(api_params, scrapy_request_args, **kwargs)

    def validate_options(self, scrapy_request_args, api_params):
        url = scrapy_request_args.get("url")
        spider_start = api_params.get("spider_start") or api_params.get(
            "start_requests",
        )
        if not url and not spider_start:
            raise Error(400, b"'url' is required if spider_start is not enabled")

    def get_required_argument(self, api_params, name, error_msg=None):
        """Get required API key from dict-like object.

        :param dict api_params:
            dictionary with names and values of parameters supplied to API.
        :param str name:
            required key that must be found in api_params
        :return: value of required param
        :raises Error: Bad Request response

        """
        if error_msg is None:
            error_msg = f"Missing required parameter: {name!r}".encode()
        try:
            value = api_params[name]
        except KeyError:
            raise Error(400, message=error_msg) from None
        if not value:
            raise Error(400, message=error_msg)
        return value

    def prepare_crawl(self, api_params, scrapy_request_args, *args, **kwargs):
        """Schedule given spider with CrawlManager.

        :param dict api_params:
            arguments needed to find spider and set proper api parameters
            for crawl (max_requests for example)

        :param dict scrapy_request_args:
            should contain positional and keyword arguments for Scrapy
            Request object that will be created
        """
        spider_name = self.get_required_argument(api_params, "spider_name")
        try:
            max_requests = api_params["max_requests"]
        except (KeyError, IndexError):
            max_requests = None

        crawl_args = api_params.get("crawl_args")
        if isinstance(crawl_args, str):
            try:
                crawl_args = json.loads(unquote(crawl_args))
            except Exception as e:
                msg = "crawl_args must be valid url encoded JSON"
                msg += " this string cannot be decoded with JSON"
                msg += f" {e!s}"
                raise Error(400, message=msg.encode()) from e

        dfd = self.run_crawl(
            spider_name,
            scrapy_request_args,
            max_requests,
            start_requests=api_params.get("start_requests"),
            crawl_args=crawl_args,
            spider_start=api_params.get("spider_start"),
            *args,  # noqa: B026
            **kwargs,  # type: ignore[misc]
        )
        dfd.addCallback(self.prepare_response, request_data=api_params, *args, **kwargs)  # noqa: B026
        return dfd

    def run_crawl(  # noqa: PLR0913  # pylint: disable=keyword-arg-before-vararg,too-many-positional-arguments
        self,
        spider_name,
        scrapy_request_args,
        max_requests=None,
        crawl_args=None,
        start_requests=None,
        spider_start=None,
        *args,
        **kwargs,
    ):
        crawl_manager_cls = load_object(app_settings.CRAWL_MANAGER)
        manager = crawl_manager_cls(
            spider_name,
            scrapy_request_args,
            max_requests,
            start_requests=start_requests,
            spider_start=spider_start,
        )
        if crawl_args:
            kwargs.update(crawl_args)
        return manager.crawl(*args, **kwargs)

    def prepare_response(self, result, request_data, *_args, **_kwargs):
        items = result.get("items")
        user_error = result.get("user_error", None)
        if user_error:
            raise user_error
        response = {
            "status": "ok",
            "items": items,
            "items_dropped": result.get("items_dropped", []),
            "stats": result.get("stats"),
            "spider_name": result.get("spider_name"),
        }
        errors = result.get("errors")
        if errors:
            response["errors"] = errors
        if "start_requests" in request_data:
            response["warnings"] = [
                "The start_requests parameter is deprecated, use spider_start instead.",
            ]
        return response
