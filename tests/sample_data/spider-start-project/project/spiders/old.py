from collections.abc import AsyncGenerator, Generator
from typing import Any

from scrapy import Request, Spider
from scrapy.http import Response


class OldSpider(Spider):
    name = "old"

    def start_requests(self) -> Generator[Any]:
        yield Request("https://start_requests.example")

    async def parse(self, response: Response) -> AsyncGenerator[Any]:
        yield {"url": response.url}
