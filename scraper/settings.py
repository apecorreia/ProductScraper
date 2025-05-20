""" Scrapy settings for scraper project"""

from datetime import datetime

BOT_NAME = "scraper"

SPIDER_MODULES = ["scraper.spiders"]

# Add Log settings
LOG_LEVEL = 'INFO' # Options: CRITICAL, ERROR, WARNING, INFO, DEBUG
LOG_ENABLED = True
LOG_STDOUT = False
LOG_FILE_APPEND = False
LOG_FILE = f'scraper/logs/scrapy_log_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'


#FEEDS = {
#    'scraper/output/products.json': {
#        'format': 'json',  # File format
#        'encoding': 'utf8',  # Encoding
#        'store_empty': False,  # Whether to store items if empty
#        'indent': 4,  # Indentation for pretty-printed JSON
#        'fields': None,  # Specify fields or leave `None` to include all fields
#    },
#}

# Add Feed Export settings
FEED_EXPORT_ENCODING = 'utf-8'
FEED_STORE_EMPTY = False
FEED_EXPORT_BATCH_ITEM_COUNT = 1000

# Execution categories limit and Not-to-scrape cattegoriies
CATEGORY_LIMIT = 10
CATEGORIES_TO_SKIP = ['61eede01fd2bff003f50830b', 'marcas-auchan', "produtos-locais", '61eedde9fd2bff003f508159', "papelaria-e-livraria"]

# Download Delay settings
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 20
DOWNLOAD_MAXSIZE = 1073741824
DOWNLOAD_WARNSIZE = 33554432

# Retry Settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_PRIORITY_ADJUST = -1

# Concurrent Requests Settings
CONCURRENT_REQUESTS_PER_DOMAIN = 128
CONCURRENT_REQUESTS = 128
#CONCURRENT_REQUESTS_PER_IP = 16
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 3
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0
#AUTOTHROTTLE_DEBUG = True

MEMUSAGE_ENABLED = True
MEMUSAGE_WARNING_MB = 0
MEMUSAGE_LIMIT_MB = 2048

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scraper.middlewares.ScrapeOpsFakeUserAgentMiddleware': 400,
    #'scraper.middlewares.RandomProxyMiddleware': 410,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 1,
    #'scraper.middlewares.BrightDataProxyMiddleware':405,
}

# Add Spider settings
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None,
    'scrapy.spidermiddlewares.referer.RefererMiddleware': None,
    'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': None,
    'scrapy.spidermiddlewares.depth.DepthMiddleware': None,
}


# Add Extension settings
EXTENSIONS = {
    'scrapy.extensions.memusage.MemoryUsage': 0,
    'scrapy.extensions.logstats.LogStats': 0,
    'scrapy.extensions.corestats.CoreStats': 0,
    #'scrapy.extensions.telnet.TelnetConsole': 0,
}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'scraper.pipelines.ProductScraperPipeline': 100,
    'scraper.pipelines.SaveToDatabase': 500,
    'scraper.pipelines.PostDatabaseProcessorPipeline': 600,
}

# Enable compression
COMPRESSION_ENABLED = True
DOWNLOAD_TIMEOUT = 15

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 43200
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [400, 401, 403, 404, 408, 429, 500, 502, 503, 504]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
ASYNCIO_EVENT_LOOP = "asyncio.SelectorEventLoop"
FEED_EXPORT_ENCODING = "utf-8"
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'

# DNS Settings
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# Optimize Memory usage
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 4096
MEMUSAGE_WARNING_MB = 3072
MEMUSAGE_CHECK_INTERVAL_SECONDS = 60

# Add Queue settings
DEPTH_PRIORITY = 1
SCHEDULER_PRIORITY_QUEUE = 'scrapy.pqueues.DownloaderAwarePriorityQueue'
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'
# Add Response compression
COMPRESSION_ENABLED = True
COMPRESSION_TYPE = 'deflate'

# Disable unnecessary features
COOKIES_ENABLED = False
ROBOTSTXT_OBEY = False
REDIRECT_ENABLED = False
AJAXCRAWL_ENABLED = False
MEDIA_ALLOW_REDIRECTS = False

# Add Stats collection optimization
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'
STATS_DUMP = True

# Enable HTTP/2 support
DOWNLOAD_HANDLERS = {
    "https": "scrapy.core.downloader.handlers.http2.H2DownloadHandler",
}

# Add Telnet Console for monitoring
TELNETCONSOLE_ENABLED = False
#TELNETCONSOLE_PORT = [6023, 6073]
#TELNETCONSOLE_HOST = '127.0.0.1'

# Add Request settings
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
DUPEFILTER_DEBUG = False
