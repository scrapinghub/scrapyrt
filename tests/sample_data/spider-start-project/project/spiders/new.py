from collections.abc import AsyncGenerator
from typing import Any

from scrapy import Request, Spider
from scrapy.http import Response


class NewSpider(Spider):
    name = "new"

    async def start(self) -> AsyncGenerator[Any]:
        yield Request("https://start.example")

    async def parse(self, response: Response) -> AsyncGenerator[Any]:
        yield {"url": response.url}
