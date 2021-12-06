==========================
Scrapyrt (Scrapy realtime)
==========================

.. image:: https://github.com/scrapinghub/scrapyrt/workflows/CI/badge.svg
   :target: https://github.com/scrapinghub/scrapyrt/actions

.. image:: https://img.shields.io/pypi/pyversions/scrapyrt.svg
    :target: https://pypi.python.org/pypi/scrapyrt

.. image:: https://img.shields.io/pypi/v/scrapyrt.svg
    :target: https://pypi.python.org/pypi/scrapyrt

.. image:: https://img.shields.io/pypi/l/scrapyrt.svg
    :target: https://pypi.python.org/pypi/scrapyrt

.. image:: https://img.shields.io/pypi/dm/scrapyrt.svg
   :target: https://pypistats.org/packages/scrapyrt
   :alt: Downloads count

.. image:: https://readthedocs.org/projects/scrapyrt/badge/?version=latest
   :target: https://scrapyrt.readthedocs.io/en/latest/api.html

HTTP API for scheduling `Scrapy <https://scrapy.org/>`_ spiders and receiving their items in response.

Quickstart
===============

**1. install**

    > pip install scrapyrt

**2. switch to Scrapy project (e.g. quotesbot project)**

    > cd ../quotesbot

**3. launch ScrapyRT**

    > scrapyrt

**4. run your spiders**

    > curl "localhost:9080/crawl.json?spider_name=toscrape-css&url=http://quotes.toscrape.com/"

**5. run more complex query, e.g. specify callback**

    >  curl --data '{"request": {"url": "http://quotes.toscrape.com/page/2/"}, "spider_name": "toscrape-css", "crawl_args": {"callback":"other"}}' http://localhost:9080/crawl.json -v

Scrapyrt will look for ``scrapy.cfg`` file to determine your project settings,
and will raise error if it won't find one.  Note that you need to have all
your project requirements installed.

Features
========
* Allows you to easily add HTTP API to existing Scrapy project
* All Scrapy project components (e.g. middleware, pipelines, extensions) are supported out of the box. 
* You simply run Scrapyrt in Scrapy project directory and it starts HTTP server allowing you to schedule your spiders and get spider output in JSON format.

Note
====
* Project is not a replacement for `Scrapyd <https://scrapyd.readthedocs.io/en/stable/>`_ or `Scrapy Cloud <https://www.zyte.com/scrapy-cloud/>`_ or other infrastructure to run long running crawls
* Not suitable for long running spiders, good for spiders that will fetch one response from some website and return response


Documentation
=============

`Documentation is available on readthedocs <http://scrapyrt.readthedocs.org/en/latest/index.html>`_.

Support
=======

Open source support is provided here in Github. Please `create a question
issue`_ (ie. issue with "question" label).

Commercial support is also available by `Zyte`_.

.. _create a question issue: https://github.com/scrapinghub/scrapyrt/issues/new?labels=question
.. _Zyte: http://zyte.com

License
=======
ScrapyRT is offered under `BSD 3-Clause license <https://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_(%22BSD_License_2.0%22,_%22Revised_BSD_License%22,_%22New_BSD_License%22,_or_%22Modified_BSD_License%22)>`_.


Development
===========
Development taking place on `Github <https://github.com/scrapinghub/scrapyrt>`_.
