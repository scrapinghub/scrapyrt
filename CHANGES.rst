Changes
=======

ScrapyRT 0.17.0 (2025-07-28)
----------------------------

-   Added support for Scrapy 2.13+.

-   Lowered the minimum required Scrapy version from 2.10 to 2.7.

-   The ``start_requests`` API parameter is deprecated in favor of a new
    ``spider_start`` API parameter.

    Same with the corresponding ``__init__`` parameter and attribute of the
    ``CrawlManager`` class.


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
