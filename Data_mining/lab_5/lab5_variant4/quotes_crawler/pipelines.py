"""Четыре обязательных звена Item Pipeline."""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class StatsMixin:
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def __init__(self, crawler):
        self.crawler = crawler

    def count(self, key, value=1):
        self.crawler.stats.inc_value(key, value)


class ValidationPipeline(StatsMixin):
    """100 — обязательные поля."""

    REQUIRED = (
        "quote",
        "author",
        "author_url",
        "tags",
        "born_date_raw",
        "born_location",
        "biography",
    )

    def process_item(self, item):
        adapter = ItemAdapter(item)
        missing = [name for name in self.REQUIRED if not adapter.get(name)]
        if missing:
            self.count("dropped/missing_fields")
            raise DropItem(f"нет обязательных полей: {missing}")
        return item


class CleanPipeline(StatsMixin):
    """200 — очистка текста, тегов и даты."""

    def process_item(self, item):
        adapter = ItemAdapter(item)
        quote = " ".join(adapter["quote"].split()).strip("\"“”")
        author = " ".join(adapter["author"].split())
        tags = sorted({tag.strip().lower() for tag in adapter["tags"] if tag.strip()})

        try:
            born_date = datetime.strptime(
                adapter["born_date_raw"].strip(), "%B %d, %Y"
            ).date().isoformat()
        except (TypeError, ValueError):
            self.count("dropped/bad_date")
            raise DropItem(f"дата не разбирается: {adapter.get('born_date_raw')!r}")

        adapter["quote"] = quote
        adapter["author"] = author
        adapter["tags"] = tags
        adapter["born_date"] = born_date
        adapter["born_location"] = " ".join(adapter["born_location"].split())
        adapter["biography"] = " ".join(adapter["biography"].split())

        raw_key = f"{author.casefold()}|{quote.casefold()}"
        adapter["business_key"] = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return item


class DedupPipeline(StatsMixin):
    """300 — дедупликация по паре автор + цитата."""

    def open_spider(self):
        self.seen = set()

    def process_item(self, item):
        key = ItemAdapter(item)["business_key"]
        if key in self.seen:
            self.count("dropped/duplicate")
            raise DropItem(f"дубль цитаты: {key[:12]}")
        self.seen.add(key)
        return item


class SQLitePipeline(StatsMixin):
    """400 — пакетная запись цитат и связей цитата–тег в SQLite."""

    BATCH_SIZE = 20

    def open_spider(self):
        db_path = Path(self.crawler.settings.get("SQLITE_PATH", "data/crawl.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                business_key TEXT PRIMARY KEY,
                quote TEXT NOT NULL,
                author TEXT NOT NULL,
                author_url TEXT NOT NULL,
                born_date TEXT NOT NULL,
                born_location TEXT NOT NULL,
                biography TEXT NOT NULL,
                source_tag TEXT,
                list_page TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_tags (
                business_key TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (business_key, tag),
                FOREIGN KEY (business_key) REFERENCES quotes(business_key)
            )
            """
        )
        self.conn.commit()
        self.buffer = []

    def process_item(self, item):
        self.buffer.append(dict(ItemAdapter(item)))
        if len(self.buffer) >= self.BATCH_SIZE:
            self._flush()
        return item

    def _flush(self):
        if not self.buffer:
            return

        quote_rows = [
            (
                row["business_key"], row["quote"], row["author"],
                row["author_url"], row["born_date"], row["born_location"],
                row["biography"], row.get("source_tag"), row.get("list_page"),
            )
            for row in self.buffer
        ]
        tag_rows = sorted(
            {
                (row["business_key"], tag)
                for row in self.buffer
                for tag in row["tags"]
            }
        )

        self.conn.executemany(
            "INSERT OR REPLACE INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            quote_rows,
        )
        before_tags = self.conn.total_changes
        self.conn.executemany(
            "INSERT OR IGNORE INTO quote_tags VALUES (?, ?)",
            tag_rows,
        )
        inserted_tags = self.conn.total_changes - before_tags
        self.conn.commit()

        self.count("db/quotes_written", len(quote_rows))
        self.count("db/tag_links_written", inserted_tags)
        self.count("db/batches")
        self.buffer.clear()

    def close_spider(self):
        self._flush()
        self.conn.close()
