Changes
=======

0.17.0 (unreleased)
-------------------

- errback method for spider made configurable, errback for spiders will default
  to None instead of parse


0.16 (2023-02-14)
-----------------

- errback method for spider made configurable, errback for spiders will default
  to None instead of parse


0.12 (2021-03-08)
-----------------

- added crawl arguments for API
- removed Python 2 support
- added Python 3.9 support
- docs clean up
- removed superfluous requirements (demjson, six)
- fixed API crash when spider returns bytes in items output
- updated unit tests
- development improvements, moved from Travis to Github Workflows
