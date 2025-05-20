"""
Define the models for the scraped items
"""

import scrapy


class ProductItem(scrapy.Item):
    """
    Class that Inheritates from Scrapy Item

    Args:
        scrapy (scrapi.Item): provides a dict like API to be used in the Pipelines
    """
    store = scrapy.Field()
    name = scrapy.Field()
    category = scrapy.Field()
    sub_category = scrapy.Field()
    brand = scrapy.Field()
    quantity = scrapy.Field()
    quantity_value = scrapy.Field()
    quantity_unit = scrapy.Field()
    quantity_items = scrapy.Field()
    quantity_total = scrapy.Field()
    primary_price = scrapy.Field()
    primary_price_unit = scrapy.Field()
    before_discount_price = scrapy.Field()
    has_discount = scrapy.Field()
    secondary_price = scrapy.Field()
    secondary_price_unit = scrapy.Field()
    img_lnk = scrapy.Field()
