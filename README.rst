==========================
Scrapyrt (Scrapy realtime)
==========================

.. image:: https://travis-ci.org/scrapinghub/scrapyrt.svg?branch=master
    :target: https://travis-ci.org/scrapinghub/scrapyrt

HTTP server which provides API for scheduling Scrapy spiders and
making requests with spiders.

.. contents::

Installation
============

To install Scrapyrt::

    python setup.py install

Now you can run Scrapyrt from within Scrapy project by just typing::

    scrapyrt

in Scrapy project directory. This should start server on port 9080.
You may change the port server will listen to using ``-p`` option
(see `Command line arguments`_)::

    scrapyrt -p 9081

Scrapyrt will look for ``scrapy.cfg`` file to determine your project settings,
and will raise error if it won't find one.  Note that you need to have all
your project requirements installed.

Pay attention to Scrapy version you're using in your spiders.
Scrapyrt makes use of recent improvements in `Scrapy Crawler`_ interface that
are not present in old Scrapy versions. Look closely at ``requirements.txt`` of
Scrapyrt and install most recent development Scrapy version if possible.
Unfortunately we are unable to support old Scrapy versions.

If you would like to play with source code and possibly contribute
to the project, you can install Scrapyrt in 'dev' mode::

    python setup.py develop

with this mode of installation changes you made to Scrapyrt source will be
reflected when you run ``scrapyrt`` command.

Scrapyrt HTTP API
=================

Scrapyrt supports endpoint ``/crawl.json`` that can be requested
with two methods.


GET
---

Arguments
~~~~~~~~~

Currently it accepts following arguments:

spider_name
    - type: string
    - required

    Name of the spider to be scheduled. If spider is not found api
    will return 404.

url
    - type: string
    - required

    Absolute URL to send request to. URL should be urlencoded so that
    querystring from url will not interfere with api parameters.

callback
    - type: string
    - optional

    Should exist as method of scheduled spider, does not need to contain self.
    If not passed or not found on spider default callback `parse`_ will be used.

max_requests
    - type: integer
    - optional

    Maximal amount of requests spider can generate. E.g. if it is set to ``1``
    spider will only schedule one single request, other requests generated
    by spider (for example in callback, following links in first response)
    will be ignored. If your spider generates many requests in callback
    and you don't want to wait forever for it to finish
    you should probably pass it.

If required parameters are missing api will return 400 Bad Request
with hopefully helpful error message.

Examples
~~~~~~~~

To run sample `dmoz spider`_ from `Scrapy educational dirbot project`_
parsing page about Ada programming language::

    curl "http://localhost:9080/crawl.json?spider_name=dmoz&url=http://www.dmoz.org/Computers/Programming/Languages/Ada/"


To run same spider only allowing one request and parsing url
with callback ``parse_foo``::

    curl "http://localhost:9080/crawl.json?spider_name=dmoz&url=http://www.dmoz.org/Computers/Programming/Languages/Ada/&callback=parse_foo&max_requests=1"

POST
----

Request body must contain valid JSON with information about request to be
scheduled with spider and spider name. All positional and  keyword arguments
for `Scrapy Request`_ should be placed in request JSON key. Sample JSON::

    {
        "request": {
            "url": "http://www.target.com/p/-/A-13631176",
            "callback": "parse_product",
            "dont_filter": "True"
        },
        "spider_name": "target.com_products"
    }

Slighty more complicated JSON::

    {
        "request": {
            "url": "http://www.target.com/p/-/A-13631176",
            "meta": {
                "category": "some category",
                "item": {
                    "discovery_item_id": "999"
                }
            },
            "callback": "parse_product",
            "dont_filter": "True",
            "cookies": {
                "foo": "bar"
            }
        },
        "spider_name": "target.com_products"
    }

Arguments
~~~~~~~~~

JSON in POST body must have following keys:

spider_name
    - type: string
    - required

    Name of the spider to be scheduled. If spider is not found api
    will return 404.

max_requests
    - type: integer
    - optional

    Maximal amount of requests spider can generate.

request
    - type: JSON object
    - required

    Should be valid JSON containing arguments to Scrapy request object
    that will be created and scheduled with spider.

**request** JSON object must contain following keys:

url
    - type: string
    - required

It can contain all keyword arguments supported by `Scrapy Request`_ class.

If required parameters are missing api will return 400 Bad Request with
hopefully helpful error message.

Examples
~~~~~~~~

To schedule spider dmoz with sample url using POST handler::

    curl localhost:9080/crawl.json \
        -d '{"request":{"url":"http://www.dmoz.org/Computers/Programming/Languages/Awk/"}, "spider_name": "dmoz"}'


to schedule same spider with some meta that will be passed to spider request::

    curl localhost:9080/crawl.json \
        -d '{"request":{"url":"http://www.dmoz.org/Computers/Programming/Languages/Awk/", "meta": {"alfa":"omega"}}, "spider_name": "dmoz"}'

Response
--------

``/crawl.json`` returns JSON object. Depending on whether request
was successful or not fields in json object can vary.

Success response
~~~~~~~~~~~~~~~~

JSON response for success has following keys:

status
    Success response always have status "ok".

spider_name
    Spider name from request.

stats
    `Scrapy stats`_ from finished job.

items
    List of scraped items.

items_dropped
    List of dropped items.

errors (optional)
    Contains list of strings with crawl errors tracebacks. Available only if
    `DEBUG`_ settings is set to ``True``.

Example::

    $ curl "http://localhost:9080/crawl.json?spider_name=dmoz&url=http://www.dmoz.org/Computers/Programming/Languages/Ada/"
    {
        "status": "ok"
        "spider_name": "dmoz",
        "stats": {
            "start_time": "2014-12-29 16:04:15",
            "finish_time": "2014-12-29 16:04:16",
            "finish_reason": "finished",
            "downloader/response_status_count/200": 1,
            "downloader/response_count": 1,
            "downloader/response_bytes": 8494,
            "downloader/request_method_count/GET": 1,
            "downloader/request_count": 1,
            "downloader/request_bytes": 247,
            "item_scraped_count": 16,
            "log_count/DEBUG": 17,
            "log_count/INFO": 4,
            "response_received_count": 1,
            "scheduler/dequeued": 1,
            "scheduler/dequeued/memory": 1,
            "scheduler/enqueued": 1,
            "scheduler/enqueued/memory": 1
        },
        "items": [
            {
                "description": ...,
                "name": ...,
                "url": ...
            },
            ...
        ],
        "items_dropped": [],
    }

Error response
~~~~~~~~~~~~~~

JSON error response has following keys:

status
    Error response always have status "error".

code
    Duplicates HTTP response code.

message
    Error message with some explanation why request failed.

Example::

    $ curl "http://localhost:9080/crawl.json?spider_name=foo&url=http://www.dmoz.org/Computers/Programming/Languages/Ada/"
    {
        "status": "error"
        "code": 404,
        "message": "Spider not found: foo",
    }

Tweaking spiders for realtime
=============================

If you have some standard values you would like to add to all requests
generated from realtime api and you don't want to pass them in each
GET request sent to api you can add a method ``modify_realtime_request``
to your spider, this method should accept request and return modified
request you would like to send. API will execute this method, modify request
and issue modified request.

For example::

    class SpiderName(Spider):
        name = "some_spider"

        def parse(self, response):
            pass

        def modify_realtime_request(self, request):
            request.meta["dont_redirect"] = True
            return request


Command line arguments
======================

Use ``scrapyrt -h`` to get help on command line options::

    $ scrapyrt -h
    usage: scrapyrt [-h] [-p PORT] [-i IP] [--project PROJECT] [-s name=value]
                    [-S project.settings]

    HTTP API server for Scrapy project.

    optional arguments:
      -h, --help            show this help message and exit
      -p PORT, --port PORT  port number to listen on
      -i IP, --ip IP        IP address the server will listen on
      --project PROJECT     project name from scrapy.cfg
      -s name=value, --set name=value
                            set/override setting (may be repeated)
      -S project.settings, --settings project.settings
                            custom project settings module path


Configuration
=============

You can pass custom settings to Scrapyrt using ``-S`` option
(see `Command line arguments`_)::

    scrapyrt -S config

Scrapyrt imports passed module, so it should be in one of the directories on
``sys.path``.

Another way to configure server is to use ``-s key=value`` option::

    scrapyrt -s TIMEOUT_LIMIT=120

Settings passed using ``-s`` option have the highest priority, settings passed
in ``-S`` configuration module have priority higher than default settings.


Available settings
------------------

SERVICE_ROOT
~~~~~~~~~~~~

Root server resource which is used to initialize Scrapyrt application.
You can pass custom resource here and start Scrapyrt with it.

Default: ``scrapyrt.resources.RealtimeApi``.

RESOURCES
~~~~~~~~~

Dictionary where keys are resource URLs and values are resource classes.
Used to setup Scrapyrt application with proper resources. If you want to add
some additional resources - this is the place to add them.

Default::

    RESOURCES = {
        'crawl.json': 'scrapyrt.resources.CrawlResource',
    }

LOG_DIR
~~~~~~~

Path to directory to store crawl logs from running spiders.

Default: ``log`` directory.

TIMEOUT_LIMIT
~~~~~~~~~~~~~

Use this setting to limit crawl time.

Default: ``1000``.

DEBUG
~~~~~

Run Scrapyrt in debug mode - in case of errors you will get Python tracebacks
in response, for example::

    {
        "status": "ok"
        "spider_name": "dmoz",
        "stats": {
            "start_time": "2014-12-29 17:26:11",
            "spider_exceptions/Exception": 1,
            "finish_time": "2014-12-29 17:26:11",
            "finish_reason": "finished",
            "downloader/response_status_count/200": 1,
            "downloader/response_count": 1,
            "downloader/response_bytes": 8494,
            "downloader/request_method_count/GET": 1,
            "downloader/request_count": 1,
            "downloader/request_bytes": 247,
            "log_count/DEBUG": 1,
            "log_count/ERROR": 1,
            "log_count/INFO": 4,
            "response_received_count": 1,
            "scheduler/dequeued": 1,
            "scheduler/dequeued/memory": 1,
            "scheduler/enqueued": 1,
            "scheduler/enqueued/memory": 1
        },
        "items": [],
        "items_dropped": [],
        "errors": [
            "Traceback (most recent call last): [...] \nexceptions.Exception: \n"
        ],
    }


Default: ``True``.

PROJECT_SETTINGS
~~~~~~~~~~~~~~~~

Automatically picked up from scrapy.cfg during initialization.

LOG_FILE
~~~~~~~~

Path to file to store logs from Scrapyrt with daily rotation.

Default: ``None``. Writing log to file is disabled by default.

Spider settings
---------------

Scrapyrt overrides some Scrapy project settings by default and most importantly
it disables some `Scrapy extensions`_::

        "EXTENSIONS": {
            'scrapy.contrib.logstats.LogStats': None,
            'scrapy.webservice.WebService': None,
            'scrapy.telnet.TelnetConsole': None,
            'scrapy.contrib.throttle.AutoThrottle': None
        }

There's usually no need and thus no simple way to change those settings,
but if you have reason to do so you need to override ``get_project_settings``
method of ``scrapyrt.core.CrawlManager``.

.. _dmoz spider: https://github.com/scrapy/dirbot/blob/master/dirbot/spiders/dmoz.py
.. _Scrapy educational dirbot project: https://github.com/scrapy/dirbot
.. _Scrapy Request: http://doc.scrapy.org/en/latest/topics/request-response.html#scrapy.http.Request
.. _Scrapy Crawler: http://doc.scrapy.org/en/latest/topics/api.html#scrapy.crawler.Crawler
.. _parse: http://doc.scrapy.org/en/latest/topics/spiders.html#scrapy.spider.Spider.parse
.. _Scrapy stats: http://doc.scrapy.org/en/latest/topics/stats.html
.. _Scrapy extensions: http://doc.scrapy.org/en/latest/topics/extensions.html
