"""Настройки учебного промышленного краулера."""

BOT_NAME = "quotes_crawler"
SPIDER_MODULES = ["quotes_crawler.spiders"]
NEWSPIDER_MODULE = "quotes_crawler.spiders"

# Идентифицируем учебный краулер и соблюдаем правила площадки.
USER_AGENT = "course-crawler/1.0 (educational use; lab 5)"
ROBOTSTXT_OBEY = True

# Умеренная параллельность: не более двух запросов к учебному домену.
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.1

# AutoThrottle подстраивает скорость под задержки сервера.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.1
AUTOTHROTTLE_MAX_DELAY = 3.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Сетевые таймауты и ограниченные повторы временных ошибок.
DOWNLOAD_TIMEOUT = 20
RETRY_TIMES = 2
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]

# Предохранители. Лимит глубины позволяет пройти 10 страниц каталога,
# страницы тегов и карточки авторов.
DEPTH_LIMIT = 25
CLOSESPIDER_ITEMCOUNT = 300

# Кэш включён для воспроизводимой отладки.
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = ".scrapy/httpcache"
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

ITEM_PIPELINES = {
    "quotes_crawler.pipelines.ValidationPipeline": 100,
    "quotes_crawler.pipelines.CleanPipeline": 200,
    "quotes_crawler.pipelines.DedupPipeline": 300,
    "quotes_crawler.pipelines.SQLitePipeline": 400,
}

SQLITE_PATH = "data/crawl.db"
LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"
TELNETCONSOLE_ENABLED = False
