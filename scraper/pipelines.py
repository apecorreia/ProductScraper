
# pylint: skip-file
# Import External modules

import re
import os
from datetime import datetime
from collections import defaultdict
import logging
import numpy as np
from itemadapter import ItemAdapter
import pandas as pd
from tqdm.auto import tqdm

#Import internal modules
from configuration.connection import DBConnectionHandler as dbch
from configuration.base import Base
from entities.product import Product, Store
from entities.db_registry import DBRegistry
from scraper.spiders.spiders_progress import Progress
from utilities.qnt_brand_extraction import AuchanQuantityBrandExtractor, standardize_quantity
from utilities.category_normalizer import CategoryNormalizer
from utilities.db_manager import DBManager

class ProductScraperPipeline:
    """
    Cleans and standardizes scraped product data before database insertion.
    """

    def __init__(self):
        self.price_fields = ['primary_price', 'secondary_price', 'before_discount_price']
        self.unit_fields = ['primary_price_unit', 'secondary_price_unit']

        # Common unit mapping
        self.unit_mapping = {
            "kg": ["kg", "kgm"],
            "lt": ["l", "ltr"],
            "metro": ["m", "mtr", "cm"],
            "dose": ["dos"],
            "un": ["ro", "un", 'undefined', 'unknown', 'edt']
        }

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        excluded_fields = {'img_lnk'}

        # Normalize string fields
        for field_name in adapter.field_names():
            if field_name in excluded_fields:
                continue
    
            value = adapter.get(field_name)
            if isinstance(value, str) :
                cleaned = re.sub(r'[\s/€]+', ' ', value).strip().lower()
                adapter[field_name] = cleaned

        # Clean and convert price fields
        for price_key in self.price_fields:
            value = adapter.get(price_key)
            adapter[price_key] = self._parse_price(value)
            
        # Fill hasDiscount column
        primary = adapter.get('primary_price') or 0.0
        before_discount = adapter.get('before_discount_price') or 0.0
        adapter['has_discount'] = bool(before_discount > primary and before_discount != 0)


        # Standardize units
        for unit_key in self.unit_fields:
            value = adapter.get(unit_key, '').lower()
            adapter[unit_key] = self._standardize_unit(value)

        return item

    def _parse_price(self, value):
        """
        Parses and rounds price values.
        Handles formats like '1.150,23' or '1,150.23' or even '1,150,23'
        assuming the last separator is the decimal point.
        """
        if isinstance(value, (int, float)):
            return round(value, 2)

        if isinstance(value, str):
            # Remove currency symbols and whitespace
            value = re.sub(r'[^\d,.\s]', '', value).strip()

            # If both , and . are present, we guess the last one is the decimal separator
            if ',' in value and '.' in value:
                if value.rfind(',') > value.rfind('.'):
                    # Comma as decimal
                    value = value.replace('.', '').replace(',', '.')
                else:
                    # Dot as decimal
                    value = value.replace(',', '')

            elif value.count(',') > 1:
                # Assume comma is thousands sep except last one
                parts = value.split(',')
                value = ''.join(parts[:-1]) + '.' + parts[-1]

            elif value.count('.') > 1:
                # Same logic for dot as thousand separator
                parts = value.split('.')
                value = ''.join(parts[:-1]) + '.' + parts[-1]

            else:
                # Single separator — assume decimal
                value = value.replace(',', '.')

            try:
                return round(float(value), 2)
            except (ValueError, TypeError):
                return 0.00

        return 0.00


    def _standardize_unit(self, unit):
        """
        Converts various unit abbreviations to standard form.
        """
        for standard, aliases in self.unit_mapping.items():
            if unit in aliases:
                return standard
        return unit  # return original if no match
    
class SaveToDatabase:
    """
    Pipeline that saves the items to the database in batches to improve efficiency
    """

    BATCH_SIZE = 1000  # Defines the number of items to process before committing a batch

    def __init__(self):
        """
        Initialize the SaveToDatabase pipeline.
        - Initialize a list to hold items before committing them in batches.
        """
        self.items_batch = []  # List to store items before batch committing
        self.progress_handler = Progress()
        self.progress = self.progress_handler.load_progress_file()
        self.get_database_url()

    def get_database_url(self):
        """
        Checks if the progress file as a valid database url
        
        Returns:
            string: database URL
        """

        # Loads the progress file
        self.progress = self.progress_handler.load_progress_file()
        # Access to the database url in the progress file
        data_base_url = self.progress['database_url']

        if data_base_url:
            return data_base_url

        # In the cases where the database url is invalid or empty, creates a new one
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_data_base_path = f'sqlite:///databases/products_{timestamp}.db'
            self.create_new_database(new_data_base_path) # Create new database
            #new_data_base_path = self.create_new_postgres_database()

            self.progress['database_url'] = new_data_base_path # create a new database path
            
            # Get current datetime
            now = datetime.now().isoformat()
            
            self.progress['scraper_init_time'] = now if not self.progress['scraper_init_time'] else self.progress['scraper_init_time']

            # Update progress with the new database url
            self.progress_handler.save_progress(self.progress)

            return new_data_base_path

    @staticmethod
    def is_scraping_complete():
        progress = Progress().load_progress_file()
        return (
            progress['scraped_categories']['pingo_doce'] >= progress['total_categories']['pingo_doce'] and
            progress['scraped_categories']['continente'] >= progress['total_categories']['continente'] and
            progress['scraped_categories']['auchan'] >= progress['total_categories']['auchan']
        )

    def create_new_database(self, new_data_base_path):
        """
        Called when the spider opens.
        - Creates database tables for storing products.
        """
        try:
            # Establish a connection and create the necessary tables
            with dbch(new_data_base_path) as db:
                # Create tables for Continente, Auchan and Pingo Doce products
                Base.metadata.create_all(db.get_engine())
                # Insert initial stores into the Store table
                initial_stores = [
                    {"storeName": "continente"},
                    {"storeName": "pingo doce"},
                    {"storeName": "auchan"}
                ]
                for store in initial_stores:
                    new_store = Store(**store)
                    db.session.add(new_store)

                db.session.commit()  # Commit the changes

            return new_data_base_path

        except Exception as e: # pylint: disable=broad-exception-caught
            # Log any errors that occur during table creation
            return e

    def process_item(self, item, spider):
        """
        Process each scraped item and add it to the batch.
        - When the batch size is reached, commit the batch to the database.
        """
        self.items_batch.append(item)  # Add the item to the current batch

        # If the batch size is reached, commit the items to the database
        if len(self.items_batch) >= self.BATCH_SIZE:
            self._commit_batch(spider)

        return item  # Return the item for any additional processing

    def close_spider(self, spider):
        """
        Called when the spider closes.
        - Commits any remaining items in the batch to the database.
        - Updates the database url if 
        """

        self.progress = self.progress_handler.load_progress_file()

        if self.items_batch:
            # Commit any leftover items in the batch to the database
            self._commit_batch(spider)
            # Ensure 'scraped_items' key exists
            if 'scraped_items' not in self.progress:
                self.progress['scraped_items'] = 0

            # Get item_scraped_count from crawler stats
            item_scraped_count = spider.crawler.stats.get_value('item_scraped_count', 0)
            self.progress['scraped_items'] += item_scraped_count

        if self.is_scraping_complete():

            print('Scrape completed - Updating progress with a new template')
            self.progress_handler.create_progress_file()
            self.progress = self.progress_handler.load_progress_file()
            self.progress_handler.save_progress(self.progress)

        else:
            print('Scrape not completed - saving progress')
            self.progress_handler.save_progress(self.progress)


    def _commit_batch(self, spider):# pylint: disable=unused-argument
        try:
            self.progress = self.progress_handler.load_progress_file()
            data_base_url = self.progress['database_url']

            with dbch(data_base_url) as db:
                store_cache = {}
                products_added = 0

                for item in self.items_batch:
                    try:
                        store_name = item['store']

                        if store_name not in store_cache:
                            store = db.session.query(Store).filter_by(storeName=store_name).first()
                            if store is None:
                                print(f"Store not found: {store_name}")
                                continue
                            store_cache[store_name] = store.storeId

                        store_id = store_cache[store_name]

                        # Convert price fields to float
                        primary_price = float(item['primary_price']) if item['primary_price'] else 0.0# pylint: disable=line-too-long
                        secondary_price = float(item['secondary_price']) if item['secondary_price'] else 0.0# pylint: disable=line-too-long
                        before_discount_price = float(item.get('before_discount_price', 0.0))
                        
                        # Skip if primary price is zero
                        if primary_price == 0.0 or secondary_price == 0.0:
                            print(f"Skipping product: {item['name']}")
                            with open("utilities/txt/skiped_products.txt", 'a', encoding='utf-8') as file:
                                file.write(f"{item['store']} || {item['name']} \n")
                            continue

                        attributes = {
                            'storeId': store_id,
                            'category': str(item['category']),
                            'sub_category': str(item['sub_category']),
                            'name': str(item['name']),
                            'brand': item.get('brand'),
                            'quantity': item.get('quantity'),
                            'quantity_value': item.get('quantity_value'),
                            'quantity_unit': item.get('quantity_unit'),
                            'quantity_items': item.get('quantity_items'),
                            'quantity_total': item.get('quantity_total'),
                            'primaryPrice': primary_price,
                            'primaryPriceUnit': str(item['primary_price_unit']),
                            'beforeDiscountPrice': before_discount_price,
                            'hasDiscount': item.get('has_discount'),
                            'secondaryPrice': secondary_price,
                            'secondaryPriceUnit': str(item['secondary_price_unit']),
                            'image': str(item['img_lnk'])
                        }

                        product = Product(**attributes)
                        db.session.add(product)
                        products_added += 1

                    except Exception as item_error:# pylint: disable=broad-exception-caught
                        print(f"Error processing item: {item_error} at: \n{item['name']} - {item['category']}")# pylint: disable=line-too-long
                        continue

                try:

                    db.session.commit()
                    self.items_batch = []

                except Exception:# pylint: disable=broad-exception-caught
                    db.session.rollback()
                    raise

        except Exception as e:# pylint: disable=broad-exception-caught
            print(f"Batch processing error: {e}")
            raise
    


class PostDatabaseProcessorPipeline:
    """
    Pipeline component that triggers post-processing after scraping is complete.
    Last pipeline in the chain.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load Progress
        self.progress = Progress().load_progress_file()
        
        # Initrialize paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.mapping_file = os.path.join(base_dir, 'utilities/json', 'category_mapping.json')
        
        # Initialize Helpers
        self.extractor = AuchanQuantityBrandExtractor()
        self.normalizer = CategoryNormalizer(self.mapping_file)
        self.total_ptoducts = None

    def close_spider(self, spider):
        """Called when spider closes - triggers post-processing if scraping is complete"""
        
        tqdm.pandas()
        try:
            if SaveToDatabase.is_scraping_complete():
                self.logger.info("Scraping is complete. Starting post-processing...")
                
                
                db_url = self.progress.get('database_url')
                
                #Instance Objects
                db_manager = DBManager(db_url)
                

                # Get products from database
                db_manager.get_products(columns=[
                    "id", "storeId", "category", "sub_category", "name",
                    "brand", "quantity", "quantity_value", "quantity_unit",
                    "quantity_items", "quantity_total", "primaryPrice",
                    "primaryPriceUnit", "secondaryPrice", "secondaryPriceUnit"
                ])

                # Create and save DataFrame
                df = db_manager.export_products_to_csv(output_file="utilities/csv/products.csv")
                
                # Using progress_apply for debugging - progress bar
                '''df[['quantity', 'brand']] = df.progress_apply(
                    lambda row: pd.Series(self.extract_from_row(row)), axis=1
                )'''
                
                # Exctact Brand and Quantity from Auchan Products names
                # Filter rows for storeId == 3
                store3_df = df[df['storeId'] == 3].copy()

                # Apply brand and quantity extraction safely
                extracted = store3_df.progress_apply(
                    lambda row: pd.Series(self.extract_from_row(row), index=['quantity', 'brand']),
                    axis=1
                )

                # Assign back to original df using index alignment
                df.loc[store3_df.index, ['quantity', 'brand']] = extracted
                print(" Successfully extracted brand and quantity from auchan product names.")
                
                # Standartization of quantity into [value, unit, items, total]
                df = df.progress_apply(self.apply_standardization, axis=1)
                print(f"✅ Successfully standardizated quantity.")
                
                print(f"✅ Starting categories inconsistency verification...")
                df = self.normalizer._verify_category_consistency_from_csv(df)

                print(f"✅ Normalizing categories...")
                df = self.normalizer.post_process_categories(df)
                
                df.to_csv("utilities/csv/products.csv", index=False, encoding='utf-8')
                print(f"✅ Successfully saved updated dataframe to CSV.")
                
                print(f"✅ Check categories inconsistency after changes applied...")
                df = self.normalizer._verify_category_consistency_from_csv(df)
                
                # Push updates to DB
                self._update_database_from_df(df, db_url)
                
                with dbch('sqlite:///databases/registry.db') as register_db:
                    register_attrs = self.get_register_attrs(db_url)
                    
                    register = DBRegistry(**register_attrs)
                    register_db.session.add(register)
                    register_db.session.commit()
                
        except Exception as e:
            self.logger.error(f"Error in post-processing pipeline: {e}")
            print(f"Error in post-processing pipeline: {e}")
            
    def extract_from_row(self, row):
        quantity, brand = self.extractor.extract_info({'name': row['name']})
        return [quantity, brand]
    
    def apply_standardization(self, row):
        result = standardize_quantity(row['quantity'], row.get('secondaryPriceUnit'))
        row['quantity_value'] = result['quantity_value']
        row['quantity_unit'] = result['quantity_unit']
        row['quantity_items'] = result['quantity_items']
        row['quantity_total'] = result['quantity_total']
        return row
    
    def _update_database_from_df(self, df: pd.DataFrame, db_url):
        """Update the database using the modified DataFrame."""
        self.logger.info("Updating database with modified data...")

        try:
            with dbch(db_url) as db:
                            
                # Track updates
                updated_rows = 0
                batch_size = 1000

                # Only update rows where the category/sub_category changed
                df_to_update = df[df['updated'] == True] if 'updated' in df.columns else df

                # Convert DataFrame to dicts in chunks
                for i in range(0, len(df_to_update), batch_size):
                    batch = df_to_update.iloc[i:i+batch_size]

                    for _, row in batch.iterrows():
                        product = db.session.query(Product).filter(Product.id == row['id']).first()
                        if product:
                            product.category = row['category']
                            product.sub_category = row['sub_category']
                            product.brand = row['brand']
                            product.quantity = row['quantity']
                            product.quantity_value = row['quantity_value']
                            product.quantity_unit = row['quantity_unit']
                            product.quantity_items = row['quantity_items']
                            product.quantity_total = row['quantity_total']
                            product.primaryPrice = row['primaryPrice']
                            product.primaryPriceUnit = row['primaryPriceUnit']
                            product.secondaryPrice = row['secondaryPrice']
                            product.secondaryPriceUnit = row['secondaryPriceUnit']
                            updated_rows += 1
                            
                        if not row['brand']:
                            db.session.query(Product).filter(Product.id == row['id']).delete()

                    db.session.commit()
                    print(f"Committed batch {i//batch_size + 1}")

                print(f"✅ Updated {updated_rows} records in the database.")
                self.total_ptoducts = db.session.query(Product).count()
                
                return True

        except Exception as e:
            self.logger.error(f"❌ Error updating database from DataFrame: {e}", exc_info=True)
            db.session.rollback()
            return False

    def get_register_attrs(self, db_url):
        init_time = datetime.fromisoformat(self.progress['scraper_init_time'])

        creation_date = init_time.strftime("%Y-%m-%d")
        creation_time = init_time.strftime("%H:%M:%S")

        finish_time = datetime.now()
        run_time = finish_time - init_time

        scraped_items = self.progress['scraped_items']
        products_count = self.total_ptoducts

        return {
            'creation_date': creation_date,
            'creation_time': creation_time,
            'run_time': str(run_time), 
            'scraped_items': scraped_items,
            'products_count': products_count,
            'db_url': db_url,
        }
        

    