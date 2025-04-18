from scrapy.exceptions import DropItem
import logging


class ProductScraperPipeline:
    """
    A Scrapy pipeline to clean and deduplicate product items.

    - Filters out duplicate SKUs.
    - Tracks basic stats for logging and reporting.
    """

    def __init__(self):
        # Track already-seen SKUs to avoid duplicates
        self.seen_skus = set()

        # Statistics to log at the end of the crawl
        self.stats = {
            "processed": 0,  # Successfully accepted items
            "dropped": 0,    # Dropped due to duplication or bad data
            "errors": 0,     # External error tracking (can be incremented elsewhere)
        }

    def process_item(self, item, spider):
        sku = item.get('sku')

        # ── Check for duplicate SKUs ──
        if sku in self.seen_skus:
            self.stats["dropped"] += 1
            raise DropItem(f"Duplicate item found: {sku}")

        # ── Passed all checks ──
        self.seen_skus.add(sku)
        self.stats["processed"] += 1
        return item

    def close_spider(self, spider):
        """
        Called automatically when the spider closes.

        Logs a summary and pushes stats to Scrapy's stats collector.
        """
        logging.info("Product scraping summary:")
        logging.info(f"Processed: {self.stats['processed']}")
        logging.info(f"Duplicates/Invalid Dropped: {self.stats['dropped']}")
        logging.info(f"Failed URLs: {self.stats['errors']}")

        # Push stats into Scrapy’s internal stats collector (useful for dashboards/logging)
        spider.crawler.stats.set_value("products_processed", self.stats['processed'])
        spider.crawler.stats.set_value("products_dropped_duplicates", self.stats['dropped'])
        spider.crawler.stats.set_value("product_page_errors", self.stats['errors'])  # Tracked elsewhere