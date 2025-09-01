import scrapy
import json
import os
from urllib.parse import urljoin, urlencode, urlparse, parse_qs

from scraper.items import ProductItem
from scraper.spiders.spiders_progress import Progress


class PingoDoceSpider(scrapy.Spider):
    name = "pingo_doce_spider"
    allowed_domains = ["pingodoce.pt"]
    start_urls = ["https://www.pingodoce.pt/home/produtos"]

    category_map_file = "utilities/json/pingo_doce_category_map.json"

    def __init__(self, *args, **kwargs):
        super(PingoDoceSpider, self).__init__(*args, **kwargs)
        self.progress = Progress().load_progress_file()

        # Initialize progress tracking structures if missing
        self.progress.setdefault("pingo_doce_categories_scraped", [])
        self.progress.setdefault("pingo_doce_subcategories_scraped", {})
        self.progress.setdefault("total_categories", {})
        self.progress.setdefault("scraped_categories", {})

    def parse(self, response):
        """
        Step 1: Scrape categories & subcategories and save/update map
        """
        category_limit = self.settings.getint('CATEGORY_LIMIT', 1)
        
        self.progress = Progress().load_progress_file()
        categories = {}

        links = response.css("a.sub-category::attr(href)").getall()
        
        ignored_categories = self.get_ignored_categories()
        
        
        
        for link in links:
            full_link = urljoin(response.url, link)  # keep whole URL
            parts = full_link.strip("/").split("/")

            # find 'produtos' index
            try:
                produtos_idx = parts.index("produtos")
            except ValueError:
                continue  # skip links without 'produtos'

            if len(parts) > produtos_idx + 2:
                category = parts[produtos_idx + 1]
                sub_category = parts[produtos_idx + 2]
                
                if category in ignored_categories:
                    continue 

                if category not in categories:
                    categories[category] = []

                # rebuild link only up to subcategory
                clean_link = "/".join(parts[:produtos_idx + 3])
                clean_link = urljoin("https://www.pingodoce.pt/", clean_link)

                if {sub_category: clean_link} not in categories[category]:
                    categories[category].append({sub_category: clean_link})

        # Save / update JSON file
        if os.path.exists(self.category_map_file):
            with open(self.category_map_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        else:
            old_data = {}

        for cat, subs in categories.items():
            old_data[cat] = subs

        with open(self.category_map_file, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=4)

        # Update progress file with total categories
        self.progress["total_categories"]["pingo_doce"] = len(categories.keys())
        Progress().save_progress(self.progress)

        scraped = set(self.progress.get("pingo_doce_categories_scraped", []))
        all_categories = list(old_data.items())

        # categories still left to scrape
        remaining = [(cat, subs) for cat, subs in all_categories if cat not in scraped]

        # take only up to CATEGORY_LIMIT
        categories_to_scrape = remaining[:category_limit]

        # update scraped categories progress
        scraped.update([cat for cat, _ in categories_to_scrape])
        self.progress["pingo_doce_categories_scraped"] = list(scraped)

        # update counter in progress
        self.progress["scraped_categories"]["pingo_doce"] = len(self.progress["pingo_doce_categories_scraped"])
        Progress().save_progress(self.progress)

        self.log(f"✅ Category map saved to {self.category_map_file}")
        self.log(f"➡️ Scraping {len(categories_to_scrape)} Pingo Doce categories (limit {category_limit})")

        # Now follow each subcategory link
        for category, subcats in categories_to_scrape:
            for sub in subcats:
                for sub_name, url in sub.items():
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_products,
                        meta={
                            'category': category,
                            'sub_category': sub_name,
                            'start': 0,
                            'total_subcategories': len(subcats)
                        }
                    )

    def parse_products(self, response):
        """
        Step 2: Scrape products from each subcategory page with pagination
        """
        category = response.meta["category"]
        sub_category = response.meta["sub_category"]
        start = response.meta.get("start", 0)
        total_subcategories = response.meta.get("total_subcategories", 0)

        # Extract product cards
        products = response.css("div.product-tile-pd")
        for product in products:
            product_item = ProductItem()

            product_item["store"] = "Pingo Doce"
            product_item["category"] = category
            product_item["sub_category"] = sub_category
            product_item["name"] = product.css("div.product-name-link a::text").get(default="").strip()
            product_item["brand"] = product.css("div.product-brand-name::text").get(default="").strip()
            quantity_text = product.css("div.product-unit::text").get(default="").strip()
            
            if "|" in quantity_text:
                quantity_part, secondary_price_part = quantity_text.split("|", 1)
            else:
                quantity_part = quantity_text
                secondary_price_part = ""
                
            product_item["quantity"] = quantity_part.strip() or None
            primary_price = product.css("span.sales .value::attr(content)").get()
            if not primary_price:
                # fallback: scrape text and clean
                primary_price = product.css("span.sales::text").get(default="0").strip().replace(",", ".")

            product_item["primary_price"] = primary_price

            # Unit / currency
            currency = product.css("span.sales::text").re_first(r"[\d.,\s]*(\D+)$")  # captures € or UN
            product_item["primary_price_unit"] = (currency or "UN").strip()

            # Before discount price (if any)
            before_discount_price = product.css(
                "div.product-price .strike-through .value::attr(content)"
            ).get(default=primary_price)

            product_item["before_discount_price"] = before_discount_price
            
            product_item["secondary_price"] = secondary_price_part.strip() or primary_price
            product_item["img_lnk"] = product.css("img.product-tile-component-image::attr(src)").get()

            yield product_item

        # Pagination: if products found, request next page
        if products:
            next_start = start + 12
            parsed = urlparse(response.url)
            query = parse_qs(parsed.query)
            query["start"] = [str(next_start)]

            next_url = parsed._replace(query=urlencode(query, doseq=True)).geturl()

            yield scrapy.Request(
                url=next_url,
                callback=self.parse_products,
                meta={
                    "category": category,
                    "sub_category": sub_category,
                    "start": next_start,
                    "total_subcategories": total_subcategories,
                },
            )
        else:
            # ✅ Subcategory finished scraping
            self.progress["pingo_doce_subcategories_scraped"].setdefault(category, [])
            if sub_category not in self.progress["pingo_doce_subcategories_scraped"][category]:
                self.progress["pingo_doce_subcategories_scraped"][category].append(sub_category)

            # Check if all subcategories of this category are scraped
            if (
                len(self.progress["pingo_doce_subcategories_scraped"][category])
                == total_subcategories
            ):
                if category not in self.progress["pingo_doce_categories_scraped"]:
                    self.progress["pingo_doce_categories_scraped"].append(category)

            Progress().save_progress(self.progress)
            self.log(f"✅ Finished subcategory {category}/{sub_category}")
            
    def get_ignored_categories(self):
        ignored_categories = ['promocoes', "as-nossas-marcas"]
        
        return ignored_categories
