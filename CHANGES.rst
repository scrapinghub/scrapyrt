Changes
=======

ScrapyRT 0.17.0 (unreleased)
----------------------------

-   …

-   Removed the ``CrawlManager.create_crawler()`` method, , which had been
    deprecated in 0.10. Use ``CrawlManager.crawl()`` instead.

    Also removed the ``decorators`` and ``exceptions`` modules, which were only
    used by the deprecated method.

-   …


ScrapyRT 0.16 (2023-02-14)
--------------------------

- errback method for spider made configurable, errback for spiders will default
  to None instead of parse


ScrapyRT 0.12 (2021-03-08)
--------------------------

- added crawl arguments for API
- removed Python 2 support
- added Python 3.9 support
- docs clean up
- removed superfluous requirements (demjson, six)
- fixed API crash when spider returns bytes in items output
- updated unit tests
- development improvements, moved from Travis to Github Workflows
