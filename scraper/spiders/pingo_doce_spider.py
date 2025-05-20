"""
This module will define the ContinenteSpider.

Role:
    -  Acess to continente.pt website and get categories and use this categories to scrape 
all the products from the online store
    - It uses Requests to acess the url created using the categories scraped in parse method
    ...
"""

#Import External modules
from urllib.parse import urlencode
import scrapy
from scrapy.http import JsonRequest
import re

#Import internal Modules
from scraper.items import ProductItem
from scraper.spiders.spiders_progress import Progress

class PingoDoceSpider(scrapy.Spider):

    name = "pingo_doce_spider"

    allowed_domains = ["mercadao.pt"]
    start_url = "https://mercadao.pt/store/pingo-doce"


    def __init__(self, *args, **kwargs):
        super(PingoDoceSpider, self).__init__(*args, **kwargs)
        self.progress = Progress().load_progress_file()


    def start_requests(self):
        yield JsonRequest(url=self.start_url, callback=self.parse)


    def parse(self, response):
        url = "https://mercadao.pt/api/catalogues/6107d28d72939a003ff6bf51/with-descendants"
        headers = self.get_pingo_doce_headers()
        yield JsonRequest(url=url, headers=headers, callback=self.parse_pingo_doce_categories)

    def parse_pingo_doce_categories(self, response):
        self.progress = Progress().load_progress_file()
        
        
        categories_to_skip = self.settings.getlist('CATEGORIES_TO_SKIP')
        categories_to_skip = set(categories_to_skip)

        categories = response.json()['tree']
        category_ids = [
            value['id']
            for value in categories.values()
            if 'id' in value and value['id'] not in categories_to_skip
        ]        
        category_limit = self.settings.getint('CATEGORY_LIMIT', 10)
        scraped_categories = set(self.progress.get('pingo_doce_categories_scraped', []))
        
        if categories_to_skip:
            new_categories = [cat_id for cat_id in category_ids
                          if cat_id not in categories_to_skip and cat_id not in scraped_categories][:category_limit]

        else:
            new_categories = [cat_id for cat_id in category_ids
                                if cat_id not in scraped_categories][:category_limit]

        self.progress['total_categories']['pingo_doce'] = len(category_ids)
        self.progress.setdefault('scraped_categories', {})  # Ensure dict exists
        self.progress['scraped_categories']['pingo_doce'] = len(scraped_categories)

        for category in new_categories:
            category_name = categories[category]['slug']
            start = 0

            yield from self.paginate_pingo_doce(
                category=category,
                start=start,
                category_name=category_name
            )

    def paginate_pingo_doce(self, category, start, category_name):
        url = "https://mercadao.pt/api/catalogues/6107d28d72939a003ff6bf51/products/search"
        querystring = {
            "mainCategoriesIds": f'["{category}"]',
            "sort": '{"activePromotion":"desc"}',
            "from": f"{start}",
            "size": "100",
            "esPreference": "0.396401689439551"
        }
        headers = self.get_pingo_doce_headers()

        yield JsonRequest(
            url=f"{url}?{urlencode(querystring)}",
            headers=headers,
            callback=self.parse_pingo_doce_products,
            cb_kwargs={'category': category, 'start': start, 'category_name': category_name},
            meta={'category': category, 'start': start, 'category_name': category_name}
        )

    def parse_pingo_doce_products(self, response, category, start, category_name):
        data = response.json()
        total_products = data['sections']['null']['total']
        products = data['sections']['null']['products']

        for product in products:
            try:
                product_item = ProductItem()
                product_item['store'] = 'Pingo Doce'
                product_item['category'] = category_name

                source = product['_source']
                product_item['name'] = source['firstName']

                # Subcategory
                product_item['sub_category'] = next(
                    (cat['name'] for cat in source['categories'] if cat['id'] != category), 'Unknown'
                )

                # Brand
                product_item['brand'] = source.get('brand', {}).get('name', 'Unknown')

                # Quantity
                raw_quantity = source['capacity'] if source['capacity'] != "0" else source.get('averageWeight', 'Unknown')
                try:
                    if 'kg' in product_item['name'].lower():
                        kg_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', product_item['name'].lower())
                        if kg_match:
                            quantity_value = float(kg_match.group(1)) * 1000
                            product_item['quantity'] = f"{quantity_value}g"
                        else:
                            product_item['quantity'] = raw_quantity
                    else:
                        quantity_value = float(raw_quantity)
                        product_item['quantity'] = f"{quantity_value}g" if quantity_value > 100 else f"{quantity_value}un"
                except:
                    product_item['quantity'] = raw_quantity

                # Prices
                price = source['buyingPrice']
                product_item['primary_price'] = price
                product_item['primary_price_unit'] = source.get('netContentUnit', 'un')
                product_item["before_discount_price"] = source["regularPrice"]

                net_content = source.get('netContent', 1)
                product_item['secondary_price'] = price / net_content if net_content else price
                product_item['secondary_price_unit'] = source.get('netContentUnit', 'un')

                # Image
                sku = source['sku']
                product_item['img_lnk'] = f'https://res.cloudinary.com/fonte-online/image/upload/c_fill,h_300,q_auto,w_300/v1/PDO_PROD/{sku}_1'

                yield product_item

            except Exception as e:
                self.logger.error(f"Error processing product: {e}")
                continue

        # Pagination logic
        start += 100
        if start < total_products:
            yield from self.paginate_pingo_doce(category, start, category_name)
        else:
            # All pages for this category done → mark as scraped
            self.mark_category_scraped(category)
            
    def mark_category_scraped(self, category_id):
        scraped = set(self.progress.get('pingo_doce_categories_scraped', []))
        scraped.add(category_id)
        self.progress['pingo_doce_categories_scraped'] = list(scraped)
        self.progress['scraped_categories']['pingo_doce'] = len(scraped)
        Progress().save_progress(self.progress)

    def get_pingo_doce_headers(self):
        return {
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }