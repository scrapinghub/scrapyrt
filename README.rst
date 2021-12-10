.. image:: https://raw.githubusercontent.com/scrapinghub/scrapyrt/master/artwork/logo.gif
   :width: 400px
   :align: center

==========================
ScrapyRT (Scrapy realtime)
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

Add HTTP API for your `Scrapy <https://scrapy.org/>`_ project in minutes.

You send a request to ScrapyRT with spider name and URL, and in response, you get items collected by a spider
visiting this URL. 

* All Scrapy project components (e.g. middleware, pipelines, extensions) are supported
* You run Scrapyrt in Scrapy project directory. It starts HTTP server allowing you to schedule spiders and get spider output in JSON.


Quickstart
===============

**1. install**

.. code-block:: shell

    > pip install scrapyrt

**2. switch to Scrapy project (e.g. quotesbot project)**

.. code-block:: shell

    > cd my/project_path/is/quotesbot

**3. launch ScrapyRT**

.. code-block:: shell

    > scrapyrt

**4. run your spiders**

.. code-block:: shell

    > curl "localhost:9080/crawl.json?spider_name=toscrape-css&url=http://quotes.toscrape.com/"

**5. run more complex query, e.g. specify callback for Scrapy request and zipcode argument for spider**

.. code-block:: shell

    >  curl --data '{"request": {"url": "http://quotes.toscrape.com/page/2/", "callback":"some_callback"}, "spider_name": "toscrape-css", "crawl_args": {"zipcode":"14000"}}' http://localhost:9080/crawl.json -v

Scrapyrt will look for ``scrapy.cfg`` file to determine your project settings,
and will raise error if it won't find one.  Note that you need to have all
your project requirements installed.

Note
====
* Project is not a replacement for `Scrapyd <https://scrapyd.readthedocs.io/en/stable/>`_ or `Scrapy Cloud <https://www.zyte.com/scrapy-cloud/>`_ or other infrastructure to run long running crawls
* Not suitable for long running spiders, good for spiders that will fetch one response from some website and return items quickly


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
