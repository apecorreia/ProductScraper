from configuration.connection import DBConnectionHandler as dbch
from entities.product import Product, Store
import pandas as pd

class DBManager:

    def __init__(self, db_path):
        self.db_path = db_path
        self.query_statement = None
        self.engine = None


    def get_products(self, columns=None):
        """Get products with optional column selection.
        
        Args:
            db_path: Path to the database
            columns: List of column names to retrieve (if None, gets all columns)
            
        Returns:
            None
        """
        db_handler = dbch(self.db_path)

        with db_handler:
            if columns:
                # Query only specific columns
                selected_columns = [getattr(Product, col) for col in columns]
                query = db_handler.session.query(*selected_columns, Store.storeName).join(Store, Product.storeId == Store.storeId)
            else:
                query = db_handler.session.query(Product, Store.storeName).join(Store, Product.storeId == Store.storeId)

            self.query_statement = query.statement
            self.engine = db_handler.get_engine()

    def export_products_to_csv(self, output_file="csv/products.csv"):
        """
        Export product data to CSV using Pandas (more efficient for large datasets).
        
        Args:
            db_path (str): Path to the SQLite database.
            output_file (str): Output CSV filename (default: "products.csv").
            columns (list): List of column names to export (None = all columns).
        """
        
        # Convert SQLAlchemy query to Pandas DataFrame
        df = pd.read_sql(self.query_statement, self.engine)

        # Export to CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"✅ Successfully exported {len(df)} products to '{output_file}'")
        
        return df

        
