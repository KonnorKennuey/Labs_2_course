"""Схема записи для варианта 4."""

from dataclasses import dataclass, field


@dataclass
class QuoteItem:
    quote: str
    author: str
    author_url: str
    tags: list[str] = field(default_factory=list)
    source_tag: str | None = None
    list_page: str | None = None
    born_date_raw: str | None = None
    born_location: str | None = None
    biography: str | None = None
    born_date: str | None = None
    business_key: str | None = None
