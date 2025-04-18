import scrapy
import json
import numpy as np
from itertools import product
import re
import os
import time

from scrapy_selenium.http import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from ..items import ProductItem
from ..loaders import ProductLoader

class ProductSpider(scrapy.Spider):
    name = "product_spider"
    allowed_domains = ["rangdongstore.vn"]
    start_urls = [
        # Used as a fallback or single URL test; in practice, URLs are loaded from JSON
        "https://rangdongstore.vn/den-led-op-tran-vuong-de-nhua-170x17012w-ln12n-p-221222002669"
    ]

    # Custom spider settings to handle retries and configure output location
    custom_settings = {
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
        'DOWNLOAD_TIMEOUT': 15,

        # Output data to a file in the product_data directory
        'FEEDS': {
            'product_data/products.json': {
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'overwrite': True,
            }
        }
    }

    def start_requests(self):
        """
        Load product URLs from a JSON file and issue Selenium requests.
        Ensures the directory exists and handles errors gracefully.
        """
        # Ensure the output directory exists
        os.makedirs('product_data', exist_ok=True)

        # Path to the product links JSON file
        json_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'product_data',
            'product_links.json'
        )

        try:
            # Read the product links
            with open(json_file_path, 'r', encoding='utf-8') as f:
                product_urls = json.load(f)

            # Send SeleniumRequest for each URL
            for url in product_urls:
                yield SeleniumRequest(
                    url=url,
                    callback=self.parse,
                    errback=self.handle_error,
                    wait_time=5  # Let the page fully render
                )

        except FileNotFoundError:
            self.logger.error(f"JSON file not found: {json_file_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON file: {e}")

    def parse(self, response):
        """
        Entry point for each product page. Handles base product data and optional variants.
        """
        driver = response.meta["driver"]

        # Scrape the main product info
        yield self.parse_product_data(driver)

        # Scrape the variants if available
        try:
            yield from self.parse_product_variants(driver)
        except Exception as e:
            self.logger.warning(f"No variant was found: {e}")

    def parse_product_data(self, driver):
        """
        Extract core product information including structured data, breadcrumb categories,
        and specifications from the HTML using Selenium.
        """
        loader = ProductLoader(item=ProductItem(), selector=None)

        # ───── Parse JSON-LD Structured Product Data ─────
        try:
            script_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='product-structured-data-script']"))
            )
            script_data = script_element.get_attribute('innerHTML')

            if script_data:
                data = json.loads(script_data)
                loader.add_value("name", data.get("name"))
                loader.add_value("url", data.get("url"))
                loader.add_value("sku", data.get("sku"))
                loader.add_value("productID", data.get("productID"))
                loader.add_value("image", data.get("image"))
                loader.add_value("price", data.get("offers", {}).get("price"))
                loader.add_value("description", data.get("description"))

        except json.JSONDecodeError:
            self.logger.warning(f"Failed to decode product structured data at {driver.current_url}")

        # ───── Breadcrumb Categories from JSON-LD ─────
        try:
            breadcrumb_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='breadcrumblist-structured-data-script']"))
            )
            breadcrumb_json = breadcrumb_element.get_attribute('innerHTML')
            if breadcrumb_json:
                breadcrumb_data = json.loads(breadcrumb_json)
                breadcrumbs = breadcrumb_data.get("itemListElement", [])

                if len(breadcrumbs) >= 3:
                    # Extract main category and sub-categories (excluding home/product page)
                    loader.add_value("main_category", breadcrumbs[1].get("name"))
                    sub_cats = [b.get("name") for b in breadcrumbs[2:-1] if b.get("name")]
                    loader.add_value("sub_categories", sub_cats)
                elif len(breadcrumbs) == 2:
                    loader.add_value("main_category", breadcrumbs[1].get("name"))

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self.logger.warning(f"Breadcrumb parsing error on {driver.current_url}: {e}")

        # Return the populated item
        yield loader.load_item()

    def parse_product_variants(self, driver):
        """
        Extracts and simulates clicks for all combinations of product variant options,
        generating distinct items for each variant combination.
        """
        try:
            # Wait for the variant section to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="hidden lg:block"]'))
            )

            variant_block = driver.find_element(By.CSS_SELECTOR, 'div[class="hidden lg:block"]')
            features = variant_block.find_elements(By.CLASS_NAME, 'mb-3')

            num_variants = []     # Count of options per feature
            all_variants = []     # List of all option elements grouped by feature
            variant_names = []    # List of feature names

            # Identifies each group of variant options (e.g., a group for "Color" and another for "Size").
            # For each group:
            #  - Counts the number of selectable options.
            #  - Stores all option WebElements.
            #  - Extracts the feature name (e.g., "Color") using regex from the caption label.
            for feature in features:
                variants = feature.find_elements(By.CSS_SELECTOR, 'div[class*="mr-2"]')
                num_features = len(variants)
                num_variants.append(num_features)
                all_variants.append(variants)

                caption = feature.find_element(By.CSS_SELECTOR, 'div[class = "mb-2 caption"]')
                variant_names.append(' '.join(re.findall(string = caption.text, pattern='([\w\s]+):')))

            # Generate all combinations of variant options. Each combination is a unique set of indices.
            num_options = [np.arange(i) for i in num_variants]
            category_index = list(product(*num_options))

            for combination in category_index:
                combination = list(combination)
                variant_parts = []

                for i in range(len(combination)):
                    chosen_feature = all_variants[i][combination[i]]
                    ActionChains(driver).move_to_element(chosen_feature).click().perform()
                    chosen_feature_info = chosen_feature.find_element(By.CSS_SELECTOR, 'div[class *= "relative"]').text
                    variant_parts.append(f"{variant_names[i]}: {chosen_feature_info}")

                variant_name = " | ".join(variant_parts)

                # Load base product data again after clicking variant
                loader = ProductLoader(item=ProductItem(), selector=None)
                item = next(self.parse_product_data(driver))
                for key, value in item.items():
                    loader.add_value(key, value)
                loader.add_value("variant_name", variant_name)

                time.sleep(2)

                yield loader.load_item()

        except Exception as e:
            self.logger.warning(f"Product parsing error on {driver.current_url}: {e}")

    def handle_error(self, failure):
        """
        Handles SeleniumRequest failures. Useful for stats tracking and debugging.
        """
        self.logger.error(f"Request failed: {failure}")
        self.crawler.stats.inc_value("product_page_errors")