BOT_NAME = "product_scraper"

SPIDER_MODULES = ["product_scraper.spiders"]
NEWSPIDER_MODULE = "product_scraper.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy
CONCURRENT_REQUESTS = 8

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Configure item pipelines
ITEM_PIPELINES = {
   "product_scraper.pipelines.ProductScraperPipeline": 300,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 5

# Enable scrapy-selenium middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy_selenium.SeleniumMiddleware': 800,  # Enable selenium middleware
}
SELENIUM_DRIVER_NAME = 'chrome'
SELENIUM_DRIVER_EXECUTABLE_PATH = r"C:\Users\ADMIN\WebDrivers\chromedriver.exe"
SELENIUM_DRIVER_ARGUMENTS = ['--headless', '--disable-gpu', '--no-sandbox']

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
