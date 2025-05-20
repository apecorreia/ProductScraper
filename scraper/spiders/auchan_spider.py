
"""
This module will define the AuchanSpider.

Role:
    -  Access to auchan.pt website and get categories and use these categories to scrape 
all the products from the online store
    - It uses Requests to access the url created using the categories scraped in parse method
    - Also extracts subcategories for more detailed product categorization
"""

# External imports
import re
import time
from urllib.parse import urlparse
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Internal Imports
from scraper.items import ProductItem
from scraper.spiders.spiders_progress import Progress

class AuchanSpider(scrapy.Spider):
    """
    Class that defines the auchan spider

    Args:
        scrapy (scrapy): Defines Inheritance for the created spider

    Yields:
        item: scrapy item ready to be processed via pipelines
    """

    name = "auchan_spider"
    allowed_domains = ["auchan.pt"]
    start_url = "https://www.auchan.pt"

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 32,
        'DOWNLOAD_DELAY': 0.25,  # Reduced from 1.0
        'COOKIES_ENABLED': False,
        'RETRY_TIMES': 3,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 3,  # Reduced from 5
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 16.0,  # Increased from 4.0
    }

    def __init__(self, *args, **kwargs):
        super(AuchanSpider, self).__init__(*args, **kwargs)
        self.progress = Progress().load_progress_file()
        self.items_scraped = 0
        self.pages_scraped = 0

    def start_requests(self):
        yield scrapy.Request(url=self.start_url, callback=self.parse)


    def parse(self, response):
        """
        Extract all category and subcategory links from the main navigation menu.
        """
        self.progress = Progress().load_progress_file()
        try:
            
            categories_to_skip = self.settings.getlist('CATEGORIES_TO_SKIP')
            categories_to_skip = set(categories_to_skip)
            
            if self.progress['activate_sellenium_to_get_categories_links']:
                self.logger.info("Starting category extraction process")
                categories_dict = self.get_categories(self.start_url, categories_to_skip)

                if categories_dict:
                    # Update progress
                    self.progress['activate_sellenium_to_get_categories_links'] = 0
                    self.progress["auchan_categories_dict"] = categories_dict
                    self.progress['total_categories']['auchan'] = len(categories_dict)

                    # Save progress
                    Progress().save_progress(self.progress)

                    self.logger.info(f"Successfully extracted {len(categories_dict)} categories")
                else:
                    self.logger.error("Failed to extract categories")
                    return

            # Get categories from progress file
            categories_dict = self.progress["auchan_categories_dict"]
            categories = categories_dict.keys()

            # Get scraped categories
            scraped_categories = set(self.progress.get('auchan_categories_scraped', []))
            # Implement category limit
            category_limit = self.settings.getint('CATEGORY_LIMIT', 2)
            
            if categories_to_skip:
                new_categories = [category for category in categories if
                            category not in scraped_categories and category not in categories_to_skip][:category_limit]
                
            else:
                new_categories = [category for category in categories if
                                category not in scraped_categories][:category_limit]

            # Start scraping products
            for category, category_info in categories_dict.items():
                if category in new_categories:
                    self.logger.info(f"Processing category: {category}")
                    for item in category_info:
                        try:
                            yield response.follow(
                                item['link'],
                                callback=self.parse_products,
                                cb_kwargs={
                                    'cat': category,
                                    'sub_cat': item['sub_category']
                                }
                            )
                                
                        except KeyError as e:
                            self.logger.error(f"Error processing category {category}: {str(e)}")
                            
                    scraped_categories.add(category)
                    self.progress['auchan_categories_scraped'] = list(scraped_categories)# pylint: disable=line-too-long
                    self.progress['scraped_categories']['auchan'] = len(scraped_categories)# pylint: disable=line-too-long
                    Progress().save_progress(self.progress)

        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error in parse method: {str(e)}")

    def parse_products(self, response, cat, sub_cat):
        """
        Args:
            response (_type_): _description_
            cat (_type_): _description_
            sub_cat (_type_): _description_

        Yields:
            _type_: _description_
        """
        self.pages_scraped += 1
        products = response.css('div.product-tile')

        for product in products:
            try:
                product_item = ProductItem()

                # Basic info
                product_item.update({
                    'store': 'Auchan',
                    'category': cat,
                    'sub_category': sub_cat,
                    'name': product.css('a.link::text').get('').strip()
                    #'brand': 'Unknown'
                })

                # Price handling
                price_data = self.extract_prices(product)
                product_item.update(price_data)

                # Image
                product_item['img_lnk'] = (
                    product.css('picture link::attr(href)').get() or
                    product.css('img.ct-tile-image::attr(data-src)').get()
                )

                #quantity = 1
                
                #product_item['quantity'] = quantity

                self.items_scraped += 1
                yield product_item

            except Exception as e: # pylint: disable=broad-exception-caught
                self.logger.error(f"Error processing product: {str(e)}")
                continue

        # Handle pagination
        if self.should_follow_next_page(response):
            next_page = response.css('button.auc-js-show-more-next-button::attr(data-url)').get()
            if next_page:
                yield response.follow(
                    next_page,
                    callback=self.parse_products,
                    cb_kwargs={'cat': cat, 'sub_cat': sub_cat},
                    dont_filter=True  # Important for pagination
                )

    def extract_prices(self, product):
        """Extract all price related information"""
        price_data = {
            'primary_price': '0.0',
            'before_discount_price': '0.0',
            'primary_price_unit': '/Un',
            'secondary_price': '0.0',
            'secondary_price_unit': '/Un'
        }

        try:
            # Primary price
            primary_price = (
                product.css('span.sales span.value::attr(content)').get() or
                product.css('span.list span.value::attr(content)').get() or
                '0.0'
            )
            price_data['primary_price'] = primary_price.replace('€', '').strip()

            # Before discount price
            before_price = product.css('span.list span.strike-through::attr(content)').get()
            if before_price:
                price_data['before_discount_price'] = before_price.replace('€', '').strip()


            # Secondary price
            secondary_price_text = product.css('span.auc-measures--price-per-unit::text').get()
            if secondary_price_text:
                parts = secondary_price_text.split()
                if len(parts) >= 2:
                    price_data['secondary_price'] = parts[0]
                    price_data['secondary_price_unit'] = parts[1]

        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Price extraction error: {str(e)}")

        return price_data

    def should_follow_next_page(self, response): # pylint: disable=unused-argument
        """Determine if we should follow the next page"""
        # Add your pagination control logic here
        return True  # Or implement your own conditions

    def closed(self, reason):
        """Called when spider is closed"""
        self.logger.info(f"""
        Spider closed: {reason}
        Total items scraped: {self.items_scraped}
        Total pages scraped: {self.pages_scraped}
        """)

    def get_categories(self, url, categories_to_skip):
        """_summary_

        Args:
            url (string): url to the target website

        Returns:
            dict: Dictionary with the format: 
                {
                    category : 
                        {"subcategory" : subcategory, 
                        "link": link}
                }
        """
        service = Service(ChromeDriverManager().install())# pylint: disable=line-too-long

        try:
            driver = webdriver.Chrome(service=service, options=self._get_chrome_options())
            wait = WebDriverWait(driver, 20)  # Increased timeout to 20 seconds

            self.logger.info("Starting category extraction with Selenium")
            driver.get(url)

            try:
                # Accept cookies
                self.logger.info("Attempting to accept cookies...")
                consent_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                consent_button.click()
                self.logger.info("Cookies accepted successfully")

                # Click burger menu
                self.logger.info("Attempting to open burger menu...")
                menu = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "auc-button--burger"))
                )
                menu.click()
                self.logger.info("Burger menu clicked successfully")

                # Wait for expanded menu
                self.logger.info("Waiting for menu expansion...")
                wait.until(
                    EC.presence_of_element_located((By.ID, "sg-navbar-collapse"))
                )
                self.logger.info("Menu expanded successfully")

                # Extract links with retry mechanism
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        links = driver.find_elements(By.XPATH, "//*[contains(@id, 'menu-subcategory')]")# pylint: disable=line-too-long
                        if links:
                            break
                        self.logger.warning(f"No links found, attempt {attempt + 1} of {max_retries}")# pylint: disable=line-too-long
                        time.sleep(2)
                    except Exception as e: # pylint: disable=broad-exception-caught
                        self.logger.error(f"Error finding links, attempt {attempt + 1}: {str(e)}")
                        if attempt == max_retries - 1:
                            raise

                # Extract hrefs
                link_list = []
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and 'auchan.pt' in href:  # Validate URL
                            link_list.append(href)
                    except Exception as e: # pylint: disable=broad-exception-caught
                        self.logger.error(f"Error extracting href: {str(e)}")
                        continue

                self.logger.info(f"Successfully extracted {len(link_list)} category links")

                categories_dict = self.extract_category_names(link_list, categories_to_skip)
                self.logger.info(f"Processed {len(categories_dict)} main categories")
                return categories_dict

            except Exception as e: # pylint: disable=broad-exception-caught
                self.logger.error(f"Error during category extraction: {str(e)}")
                return {}

        finally:
            try:
                driver.quit()
                self.logger.info("Selenium driver closed successfully")
            except Exception as e: # pylint: disable=broad-exception-caught
                self.logger.error(f"Error closing driver: {str(e)}")

    def extract_category_names(self, links, categories_to_skip):
        """
        Method to extract categories from the links returned from the response

        Args:
            links (list): links to every products section

        Returns:
            dict: Dictionary with the format: 
                {
                    category : 
                        {"subcategory" : subcategory, 
                        "link": link}
                }
        """
        categories_dict = {}

        try:
            for link in links:
                try:
                    parsed_url = urlparse(link)
                    path_segments = parsed_url.path.strip('/').split('/')

                    if len(path_segments) > 1:
                        category = path_segments[1].lower()  # Normalize category names
                        sub_category = path_segments[2].lower() if len(path_segments) > 2 else None

                        if category not in categories_dict and category not in categories_to_skip:
                            categories_dict[category] = []

                        # Avoid duplicate subcategories
                        entry = {'sub_category': sub_category, 'link': link}
                        if entry not in categories_dict[category]:
                            categories_dict[category].append(entry)

                except Exception as e:# pylint: disable=broad-exception-caught
                    self.logger.error(f"Error processing link {link}: {str(e)}")
                    continue

        except Exception as e:# pylint: disable=broad-exception-caught
            self.logger.error(f"Error in extract_category_names: {str(e)}")

        return categories_dict

    def _get_chrome_options(self):
        options = Options()

        # Headless mode
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

        # Security settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Performance settings
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--log-level=3")

        # Browser settings
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")

        # Additional performance settings
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")

        # Set specific preferences
        options.set_preference = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.images': 2,
        }

        return options
