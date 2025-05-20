"""
This module will define the ContinenteSpider.

Role:
    -  Access to continente.pt website and get categories and use these categories to scrape 
all the products from the online store
    - It uses Requests to access the url created using the categories scraped in parse method
    - Also extracts subcategories for more detailed product categorization
"""

# Import external modules
import json
import os
from urllib.parse import urljoin
import scrapy

# Import internal modules
from scraper.items import ProductItem
from scraper.spiders.spiders_progress import Progress


class ContinenteSpider(scrapy.Spider):
    """
    Class that defines the continente spider

    Args:
        scrapy (scrapy): Defines Inheritance for the created spider

    Yields:
        item: scrapy item ready to be processed via pipelines
    """

    name = "continente_spider"
    allowed_domains = ["continente.pt"]
    start_urls = [
        "https://www.continente.pt"  # Main website to extract subcategory links
    ]

    # Path to save the categories and subcategories mapping
    categories_file = "utilities/json/continente_categories.json"

    def __init__(self, *args, **kwargs):
        super(ContinenteSpider, self).__init__(*args, **kwargs)
        self.progress = Progress().load_progress_file()

        # Initialize progress tracking structures
        if 'continente_categories_scraped' not in self.progress:
            self.progress['continente_categories_scraped'] = []
        if 'continente_subcategories_scraped' not in self.progress:
            self.progress['continente_subcategories_scraped'] = {}
        if 'total_categories' not in self.progress:
            self.progress['total_categories'] = {}
        if 'scraped_categories' not in self.progress:
            self.progress['scraped_categories'] = {}

        # Load category mapping from file if exists
        self.category_subcategory_map = self.load_category_map() or {}
        self.current_run_categories = set()

    def load_category_map(self):
        """Load or create the category mapping file"""
        try:
            if os.path.exists(self.categories_file):
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except FileNotFoundError as e:
            self.logger.error(f"Error loading category map: {e}")
            return {}

    def save_category_map(self):
        """Save the current category mapping to file"""
        try:
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self.category_subcategory_map, f, indent=4, ensure_ascii=False)
        except FileNotFoundError as e:
            self.logger.error(f"Error saving category map: {e}")

    def start_requests(self):

        self.progress = Progress().load_progress_file()
        yield scrapy.Request(url=self.start_urls[0], callback=self.parse_category_links)

    def parse_category_links(self, response):
        """
        Extract all category and subcategory links from the main navigation menu.
        """
        # Get all dropdown links which represent the category structure
        links = response.css('a.dropdown-link::attr(href)').getall()

        # Get scraped categories and ignored categories
        scraped_categories = set(self.progress.get('continente_categories_scraped', []))
        if 'continente_subcategories_scraped' not in self.progress:
            self.progress['continente_subcategories_scraped'] = {}
        subcategories_scraped = self.progress['continente_subcategories_scraped']

        ignored_categories = self.get_ignored_categories()

        # Create a fresh category map (instead of using the loaded one)
        fresh_category_map = {}

        # Parse subcategory links and build category mapping
        valid_links = []
        for link in links:
            full_link = urljoin("https://www.continente.pt", link)
            parts = full_link.rstrip('/').split('/')

            # Look for proper category/subcategory structure (format: continente.pt/category/subcategory/)
            if len(parts) == 5 and not any(keyword in link for keyword in ["cgid", "lojas", "marcas"]):
                category = parts[3]
                sub_category = parts[4]

                # Skip ignored categories
                if category in ignored_categories or sub_category in ignored_categories:
                    continue

                # Store valid link for processing
                valid_links.append((category, sub_category, full_link))

                # Build fresh category-subcategory mapping
                if category not in fresh_category_map:
                    fresh_category_map[category] = []
                if {"sub_category": sub_category, "link": full_link} not in fresh_category_map[category] and sub_category != "bilheteira":
                    fresh_category_map[category].append({"sub_category": sub_category, "link": full_link})

        # Log changes between old and new category maps
        old_categories = set(self.category_subcategory_map.keys())
        new_categories = set(fresh_category_map.keys())
        
        added_categories = new_categories - old_categories
        removed_categories = old_categories - new_categories
        
        if added_categories:
            self.logger.info(f"Found {len(added_categories)} new categories: {', '.join(added_categories)}")
        
        if removed_categories:
            self.logger.info(f"Removed {len(removed_categories)} obsolete categories: {', '.join(removed_categories)}")
            
            # Clean up progress tracking for removed categories
            for category in removed_categories:
                if category in scraped_categories:
                    scraped_categories.remove(category)
                if category in subcategories_scraped:
                    del subcategories_scraped[category]
        
        # Check for changes in subcategories
        for category in old_categories & new_categories:  # Categories present in both old and new maps
            old_subcats = {item["sub_category"] for item in self.category_subcategory_map[category]}
            new_subcats = {item["sub_category"] for item in fresh_category_map[category]}
            
            added_subcats = new_subcats - old_subcats
            removed_subcats = old_subcats - new_subcats
            
            if added_subcats:
                self.logger.info(f"Category '{category}': Added {len(added_subcats)} new subcategories")
            
            if removed_subcats:
                self.logger.info(f"Category '{category}': Removed {len(removed_subcats)} obsolete subcategories")
                
                # Clean up progress tracking for removed subcategories
                if category in subcategories_scraped:
                    subcategories_scraped[category] = [
                        subcat for subcat in subcategories_scraped[category] 
                        if subcat in new_subcats
                    ]
                    
                    # If we've removed subcategories, check if the category is still fully scraped
                    all_subcategories = [info["sub_category"] for info in fresh_category_map.get(category, [])]
                    if set(subcategories_scraped[category]) < set(all_subcategories) and category in scraped_categories:
                        scraped_categories.remove(category)
                        self.logger.info(f"Category '{category}' is no longer fully scraped due to new subcategories")

        # Update the category map with the fresh data
        self.category_subcategory_map = fresh_category_map

        # Update total categories based on the URL structure
        self.progress['total_categories']['continente'] = len(self.category_subcategory_map)
        self.progress['scraped_categories']['continente'] = len(scraped_categories)
        self.progress['continente_categories_scraped'] = list(scraped_categories)
        self.progress['continente_subcategories_scraped'] = subcategories_scraped

        # Save the updated category mapping to file
        self.save_category_map()
        Progress().save_progress(self.progress)

        # Print summary of what we found
        self.logger.info(f"Found {len(self.category_subcategory_map)} categories with {sum(len(v) for v in self.category_subcategory_map.values())} subcategories")
        
        for category, subcategories in self.category_subcategory_map.items():
            self.logger.info(f"Category '{category}': {len(subcategories)} subcategories")

        # Implement category limit from settings
        category_limit = self.settings.getint('CATEGORY_LIMIT', 1)

        # Find categories to scrape (categories with unscraped subcategories)
        categories_to_scrape = set()
        links_to_scrape = []

        for category, subcategories in self.category_subcategory_map.items():
            # Skip already fully scraped categories
            if category in scraped_categories:
                continue

            # Skip ignored categories
            if category in ignored_categories:
                continue

            # Check if we have any unscraped subcategories for this category
            category_subcategories_scraped = subcategories_scraped.get(category, [])

            for subcategory_info in subcategories:
                sub_category = subcategory_info["sub_category"]
                link = subcategory_info["link"]

                # If this subcategory hasn't been scraped yet
                if sub_category not in category_subcategories_scraped:
                    categories_to_scrape.add(category)
                    links_to_scrape.append((category, sub_category, link))

            # If we've reached our category limit
            if len(categories_to_scrape) >= category_limit:
                break

        # Track categories being processed in this run
        self.current_run_categories = categories_to_scrape

        # Log what we're going to scrape
        self.logger.info(f"Will scrape {len(links_to_scrape)} unscraped subcategory links from {len(categories_to_scrape)} categories")# pylint: disable=line-too-long

        # Follow subcategory links for selected categories
        for category, sub_category, link in links_to_scrape:
            self.logger.info(f"Scraping subcategory: {category} -> {sub_category}")
            yield response.follow(
                link,
                callback=self.parse_products,
                meta={'category': category, 'sub_category': sub_category}
            )

    def parse_products(self, response):
        """
        Extract product information from a category/subcategory page.
        Metadata contains both category and subcategory information.
        """
        category_name = response.meta['category']
        sub_category = response.meta['sub_category']

        product_info = response.css('div.product-tile')
        # pylint: disable=line-too-long
        for product in product_info:
            product_item = ProductItem()
            product_item['store'] = 'Continente'
            product_item['category'] = category_name
            product_item['sub_category'] = sub_category
            product_item['name'] = product.css('h2.pwc-tile--description::text').get()
            product_item['brand'] = product.css('p.pwc-tile--brand::text').get(default='Continente') or product.css('span.pwc-tile--brand--productSet::text').get(default='Continente')
            product_item['quantity'] = product.css('p.pwc-tile--quantity::text').get(default='1')
            price = product.css('span.ct-price-formatted::text').get()
            product_item['primary_price'] = price
            product_item['primary_price_unit'] = product.css('span.sales.pwc-tile--price-primary span.pwc-m-unit::text').get(default='Unknown')
            product_item['before_discount_price'] = product.css('span.strike-through span.value::attr(content)').get(default=price)
            product_item['secondary_price'] = product.css('span.ct-price-value::text').get(default=product_item['primary_price'])
            product_item['secondary_price_unit'] = product.css('div.pwc-tile--price-secondary span.pwc-m-unit::text').get(default=product_item['primary_price_unit'])
            product_item['img_lnk'] = product.css('img.ct-tile-image::attr(data-src)').get() or product.css('img.ct-tile-image::attr(src)').get()

            yield product_item

        next_page = response.css('div.search-view-more-products-btn-wrapper::attr(data-url)').get()

        if next_page:
            # Continue to next page of the same subcategory
            yield response.follow(
                next_page,
                callback=self.parse_products,
                meta={'category': category_name, 'sub_category': sub_category}
            )
        else:
            # Subcategory completed - mark it as scraped
            self.progress = Progress().load_progress_file()

            # Initialize subcategories_scraped for this category if it doesn't exist
            if 'continente_subcategories_scraped' not in self.progress:
                self.progress['continente_subcategories_scraped'] = {}
            if category_name not in self.progress['continente_subcategories_scraped']:
                self.progress['continente_subcategories_scraped'][category_name] = []

            # Add this subcategory to the scraped list if not already there
            if sub_category not in self.progress['continente_subcategories_scraped'][category_name]:
                self.progress['continente_subcategories_scraped'][category_name].append(sub_category)
                self.logger.info(f"Marked subcategory '{sub_category}' as complete for category '{category_name}'")

            # Check if all subcategories for this category are now scraped
            all_subcategories = [info["sub_category"] for info in self.category_subcategory_map.get(category_name, [])]
            scraped_subcategories = self.progress['continente_subcategories_scraped'].get(category_name, [])

            # If we've scraped all subcategories, mark the category as complete
            if set(scraped_subcategories) >= set(all_subcategories) and all_subcategories:
                if category_name not in self.progress['continente_categories_scraped']:
                    self.progress['continente_categories_scraped'].append(category_name)

                    # Update the scraped categories count
                    self.progress['scraped_categories']['continente'] = len(self.progress['continente_categories_scraped'])

                    self.logger.info(f"Marked category '{category_name}' as complete. "
                                    f"All {len(all_subcategories)} subcategories scraped.")

            # Save progress after each subcategory is completed
            Progress().save_progress(self.progress)
    # pylint: enable=line-too-long
    def get_ignored_categories(self):
        """
        Used to hardcode some categories that dont matter to the scraper

        Returns:
            dict: dictionary containing the ignored categories
        """
        return {
            'col', 'col-produtos', 'destaques', 'campanhas', 'col-entregazero',
            'food-lab', 'negocios', 'teste-mariana', 'gifts-prendas-todas-ocasioes',
            'entregas-sustentaveis', 'a-melhor-colheita-de-presentes', 'escolhas-saudaveis',
            "cafe-cha-e-chocolate-soluvel", "oportunidades"
        }

    def closed(self, reason):
        """
        Called when spider is closed
        
        Updates the progress file at the end and lauchs some logs regarding the spider execution
        for debbuging
        """

        # Final update of progress stats
        self.progress = Progress().load_progress_file()
        scraped_categories = self.progress.get('continente_categories_scraped', [])
        self.progress['scraped_categories']['continente'] = len(scraped_categories)
        Progress().save_progress(self.progress)

        # Save the latest category mapping
        self.save_category_map()

        # Calculate completion percentage
        total_subcategories = sum(len(subcats) for subcats in self.category_subcategory_map.values())# pylint: disable=line-too-long
        scraped_subcategories = sum(len(subcats) for subcats in
                                  self.progress.get('continente_subcategories_scraped', {}).values())# pylint: disable=line-too-long

        completion_pct = (scraped_subcategories / total_subcategories * 100) if total_subcategories > 0 else 0# pylint: disable=line-too-long

        self.logger.info(f"Spider closed: {reason}."
                       f"Categories scraped: {len(scraped_categories)}/{len(self.category_subcategory_map)}. "# pylint: disable=line-too-long
                       f"Subcategories scraped: {scraped_subcategories}/{total_subcategories} ({completion_pct:.1f}%)")# pylint: disable=line-too-long
        