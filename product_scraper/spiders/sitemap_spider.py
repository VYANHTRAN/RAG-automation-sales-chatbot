import scrapy
import os
import json


class SitemapSpider(scrapy.Spider):
    name = "sitemap_spider"
    allowed_domains = ["rangdongstore.vn"]
    start_urls = ["https://rangdongstore.vn/sitemap.xml"]

    # Custom retry and timeout settings to improve resilience on flaky requests
    custom_settings = {
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
        'DOWNLOAD_TIMEOUT': 15,
        'ITEM_PIPELINE': {}
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A set to store all collected URLs (ensures uniqueness)
        self.collected_urls = set()

    def parse(self, response):
        """
        Parse the top-level sitemap index and request each sub-sitemap.
        Uses local-name() to ignore XML namespaces.
        """
        sitemap_urls = response.xpath(
            '//*[local-name()="sitemap"]/*[local-name()="loc"]/text()'
        ).getall()

        for sitemap_url in sitemap_urls:
            # Schedule a request to each child sitemap for further parsing
            yield scrapy.Request(url=sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        """
        Parse each individual sitemap and look for product pages.
        Product pages are identified by URLs containing "-p-".
        """
        page_urls = response.xpath(
            '//*[local-name()="url"]/*[local-name()="loc"]/text()'
        ).getall()

        for url in page_urls:
            if "-p-" in url:  # Heuristic to identify product pages
                # Go deeper to check if the product has URL-based variants
                yield scrapy.Request(url=url, callback=self.parse_url_based_variants)

    def parse_url_based_variants(self, response):
        """
        On each product page, detect variant URLs presented as separate links.
        This step ensures all variants (like size/color combinations) are collected.
        """
        urls = [response.url]  # Always include the base product URL

        try:
            # Attempt to collect any clickable variant URLs
            # Typically rendered as <a> elements inside radio-content blocks
            urls += [
                response.urljoin(href)
                for href in response.css('.mb-4 [class*="radio-content"] a::attr(href)').getall()
            ]
        except Exception as e:
            self.logger.warning(f"Error extracting variants from {response.url}: {e}")

        # Add all unique URLs to the in-memory set
        for url in urls:
            self.collected_urls.add(url)

    def closed(self, reason):
        """
        When the spider finishes, dump the collected URLs to a JSON file.
        Ensures the product_data folder exists and logs the output.
        """
        output_dir = 'product_data'
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, 'product_links.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted(self.collected_urls), f, ensure_ascii=False, indent=2)

        self.logger.info(f"Wrote {len(self.collected_urls)} URLs to {output_path}")
