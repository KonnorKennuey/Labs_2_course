"""Вариант 4: каталог → страницы тегов → страницы авторов."""

import json
import time
from datetime import date, datetime
from pathlib import Path

import scrapy

from quotes_crawler.items import QuoteItem


def json_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


class QuotesTagsSpider(scrapy.Spider):
    name = "quotes_tags"
    allowed_domains = ["quotes.toscrape.com"]
    start_urls = ["https://quotes.toscrape.com/"]

    def __init__(self, run_id="final", stats_dir="data", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self.stats_dir = Path(stats_dir)
        self.started_at = time.perf_counter()

    def parse(self, response):
        """Уровень 1а: 10 страниц каталога, на которых ищутся все теги."""
        self.crawler.stats.inc_value("catalog/pages")

        for href in response.css(".quote .tags a.tag::attr(href)").getall():
            parts = href.strip("/").split("/")
            source_tag = parts[parts.index("tag") + 1]
            yield response.follow(
                href,
                callback=self.parse_tag,
                cb_kwargs={"source_tag": source_tag},
                errback=self.errback_request,
            )

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                errback=self.errback_request,
            )

    def parse_tag(self, response, source_tag):
        """Уровень 1б: цитаты конкретного тега и пагинация тега."""
        self.crawler.stats.inc_value("tag/pages")

        for quote in response.css(".quote"):
            text = quote.css(".text::text").get()
            author = quote.css(".author::text").get()
            author_href = quote.css("a[href*='/author/']::attr(href)").get()
            tags = quote.css(".tags a.tag::text").getall()

            if not author_href:
                self.crawler.stats.inc_value("dropped/missing_author_link")
                continue

            author_url = response.urljoin(author_href).replace(
                "http://quotes.toscrape.com",
                "https://quotes.toscrape.com",
                1,
            ).rstrip("/") + "/"
            yield response.follow(
                author_url,
                callback=self.parse_author,
                cb_kwargs={
                    "quote_text": text,
                    "author": author,
                    "tags": tags,
                    "source_tag": source_tag,
                    "list_page": response.url,
                },
                errback=self.errback_request,
                # Один автор связан с несколькими цитатами. Без этого Scrapy
                # оставил бы только первый контекст для страницы автора.
                dont_filter=True,
            )

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_tag,
                cb_kwargs={"source_tag": source_tag},
                errback=self.errback_request,
            )

    def parse_author(self, response, quote_text, author, tags, source_tag, list_page):
        """Уровень 2: детальные данные автора и формирование Item."""
        yield QuoteItem(
            quote=quote_text,
            author=author,
            author_url=response.url,
            tags=tags,
            source_tag=source_tag,
            list_page=list_page,
            born_date_raw=response.css(".author-born-date::text").get(),
            born_location=response.css(".author-born-location::text").get(),
            biography=response.css(".author-description::text").get(),
        )

    def errback_request(self, failure):
        self.crawler.stats.inc_value("network/errors")
        self.crawler.stats.inc_value(f"network/error_type/{failure.type.__name__}")
        self.logger.error("Request failed: %s", failure.request.url)

    def closed(self, reason):
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        stats = {
            key: json_value(value)
            for key, value in self.crawler.stats.get_stats().items()
        }
        stats["close_reason"] = reason
        stats["run_id"] = self.run_id
        stats["elapsed_wall_seconds"] = round(
            time.perf_counter() - self.started_at, 3
        )
        path = self.stats_dir / f"stats_{self.run_id}.json"
        path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
