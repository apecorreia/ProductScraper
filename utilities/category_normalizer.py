
#pylint: skip-file
import json
import logging
import os
import pandas as pd

class CategoryNormalizer:
    """
    Normalizes product categories and subcategories based on a standardized mapping.
    """

    def __init__(self, mapping_file):
        """Initialize the normalizer with mapping file."""
        self.mapping_file = mapping_file
        self.category_mapping = {}
        self.sub_category_mapping = {}
        self.reverse_category_mapping = {}
        self.category_subcategory_relationships = {}

        # Load mappings
        self._load_mappings()
        
        self.logger = logging.getLogger(__name__)

    def _load_mappings(self):
        """Load category and subcategory mappings from JSON file."""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract mappings
            self.category_mapping = data.get("category_mapping", {})
            self.sub_category_mapping = data.get("sub_category_mapping", {})
            self.category_subcategory_relationships = data.get("category_subcategory_relationships", {})

            # Create reverse mapping for categories (old -> new)
            for new_category, old_categories in self.category_mapping.items():
                for old_category in old_categories:
                    self.reverse_category_mapping[old_category.lower()] = new_category

            logging.info(f"Loaded {len(self.category_mapping)} category mappings and "
                       f"{len(self.sub_category_mapping)} subcategory mappings")

        except Exception as e:
            logging.error(f"Error loading mappings: {e}")
            # Initialize empty mappings instead of raising
            self.category_mapping = {}
            self.sub_category_mapping = {}
            self.category_subcategory_relationships = {}
            self.reverse_category_mapping = {}

    def _get_normalized_category(self, old_category):
        """Get the normalized category name for an old category."""
        if not old_category:
            return None

        # Try direct match
        normalized = self.reverse_category_mapping.get(old_category.lower())
        if normalized:
            return normalized

        # Try partial match
        for old_cat_pattern, new_cat in self.reverse_category_mapping.items():
            if old_cat_pattern in old_category.lower() or old_category.lower() in old_cat_pattern:
                return new_cat

        return old_category  # Return original if no mapping found

    def _get_normalized_subcategory(self, old_subcategory, normalized_category):
        """Get the normalized subcategory name for an old subcategory."""
        if not old_subcategory or not normalized_category:
            return old_subcategory if old_subcategory else None

        # Check if this category has defined subcategories
        valid_subcategories = self.category_subcategory_relationships.get(normalized_category, [])

        # First try to find a direct match in the valid subcategories
        for valid_subcategory in valid_subcategories:
            for old_sub in self.sub_category_mapping.get(valid_subcategory, []):
                if self._is_subcategory_match(old_subcategory, old_sub):
                    return valid_subcategory

        # If no direct match, try all subcategories but verify they're valid for this category
        for new_subcategory, old_subcategories in self.sub_category_mapping.items():
            if new_subcategory in valid_subcategories:
                for old_sub in old_subcategories:
                    if self._is_subcategory_match(old_subcategory, old_sub):
                        return new_subcategory

        # If still no match, return original
        return old_subcategory

    def _is_subcategory_match(self, subcategory1, subcategory2):
        """Check if two subcategory strings match (case-insensitive, partial match)."""
        if not subcategory1 or not subcategory2:
            return False

        s1 = subcategory1.lower()
        s2 = subcategory2.lower()

        return s1 == s2 or s1 in s2 or s2 in s1
    
    
    def _verify_category_consistency_from_csv(self, df: pd.DataFrame):
        """Verify category consistency from CSV instead of DB."""
        self.logger.info("Verifying category consistency from CSV...")

        report_path = os.path.join('utilities', 'txt', 'category_inconsistencies.txt')

        try:
            # Normalize category-subcategory using the normalizer (optional here or before)
            df = df.progress_apply(self.normalize_categories, axis=1)

            # Build mapping of valid subcategories
            valid_subcategories = {
                category: set(subcats) 
                for category, subcats in self.category_subcategory_relationships.items()
            }

            # Group and count occurrences
            grouped = df.groupby(['category', 'sub_category']).size().reset_index(name='count')

            inconsistencies = []
            for _, row in grouped.iterrows():
                category = row['category']
                subcategory = row['sub_category']
                count = row['count']
                if category in valid_subcategories and subcategory not in valid_subcategories[category]:
                    inconsistencies.append((category, subcategory, count))

            if inconsistencies:
                self.logger.warning(f"Found {len(inconsistencies)} inconsistent category-subcategory pairs")

                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("Category Inconsistencies Report\n")
                    f.write("============================\n\n")

                    for category, subcategory, count in inconsistencies:
                        f.write(f"{category}: {subcategory} ({count} products)\n")
                        matching_rows = df[
                            (df['category'] == category) & (df['sub_category'] == subcategory)
                        ].head(10)

                        f.write("- ID | Name | Price\n")
                        for _, product in matching_rows.iterrows():
                            name = (product['name'][:47] + "...") if len(product['name']) > 50 else product['name']
                            f.write(f"- {product['id']} | {name} | {product['primary_price']}\n")

                        # Suggest possible correct categories
                        possible = [
                            cat for cat, subcats in self.category_subcategory_relationships.items()
                            if subcategory in subcats
                        ]
                        if possible:
                            f.write(f"\nPossible correct categories for '{subcategory}': {', '.join(possible)}\n")
                        else:
                            f.write(f"\nConsider adding '{subcategory}' to the '{category}' category in your mapping\n")

                        f.write("\n" + "-" * 50 + "\n\n")

                    total_affected = sum(count for _, _, count in inconsistencies)
                    f.write(f"\nTotal affected products: {total_affected}\n")

                self.logger.warning(f"See {report_path} for details")
            else:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("All category-subcategory pairs are consistent!")
                self.logger.info("All category-subcategory pairs are consistent!")

        except Exception as e:
            self.logger.error(f"Error verifying category consistency from CSV: {e}", exc_info=True)
            
        return df
    
    def normalize_categories(self, row):
        """Normalize category and subcategory for a single row."""
        category = row['category']
        subcategory = row['sub_category']

        normalized_cat = self._get_normalized_category(category)
        normalized_subcat = self._get_normalized_subcategory(subcategory, normalized_cat)

        row['category'] = normalized_cat
        row['sub_category'] = normalized_subcat
        return row

            
    def _optimize_category_processing_from_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimized category standardization using DataFrame operations."""
        self.logger.info("Starting optimized category standardization...")

        try:
            # Drop rows with missing categories
            df = df.dropna(subset=['category'])

            # Get unique category-subcategory combinations
            unique_combinations = df[['category', 'sub_category']].drop_duplicates()
            self.logger.info(f"Found {len(unique_combinations)} unique category-subcategory combinations")

            # Build a mapping of original → normalized categories
            category_map = {}

            for _, row in unique_combinations.iterrows():
                old_cat, old_subcat = row['category'], row['sub_category']
                new_cat = self._get_normalized_category(old_cat)
                new_subcat = self._get_normalized_subcategory(old_subcat, new_cat)

                if new_cat != old_cat or new_subcat != old_subcat:
                    category_map[(old_cat, old_subcat)] = (new_cat, new_subcat)

            # Apply normalization to DataFrame
            def normalize_row(row):
                key = (row['category'], row['sub_category'])
                if key in category_map:
                    row['category'], row['sub_category'] = category_map[key]
                return row

            df = df.progress_apply(normalize_row, axis=1)
            self.logger.info(f"Updated {len(category_map)} unique category mappings across the DataFrame")

            return df

        except Exception as e:
            self.logger.error(f"Error during optimized category processing from DataFrame: {e}", exc_info=True)
            return df  # Return unmodified df on error

        
    def _fix_specific_issues_from_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix specific known category-subcategory inconsistencies in a DataFrame."""
        self.logger.info("Fixing specific category inconsistencies...")

        try:
            # Known issues (bad category/subcategory → corrected ones)
            inconsistencies = [
                ('Animais', 'Alimentação Infantil', 'Bebé', 'Alimentação Infantil'),
                ('Animais', 'Desporto, Atividades e Viagem', 'Desporto e Malas de Viagem', 'Desporto, Atividades e Viagem'),
                ('Mercearia', 'Vegetariano e Vegan', 'Bio, Eco e Saudável', 'Vegetariano e Vegan'),
                ('Congelados', 'Vegetariano e Vegan', 'Bio, Eco e Saudável', 'Vegetariano e Vegan')
            ]

            total_fixes = 0

            for wrong_cat, wrong_subcat, correct_cat, correct_subcat in inconsistencies:
                mask = (df['category'] == wrong_cat) & (df['sub_category'] == wrong_subcat)
                affected_rows = df[mask].shape[0]
                if affected_rows > 0:
                    df.loc[mask, 'category'] = correct_cat
                    df.loc[mask, 'sub_category'] = correct_subcat
                    total_fixes += affected_rows
                    self.logger.info(f"Fixed {affected_rows} products: '{wrong_subcat}' under '{wrong_cat}'")

            self.logger.info(f"Total fixed entries: {total_fixes}")
            return df

        except Exception as e:
            self.logger.error(f"Error fixing specific issues from DataFrame: {e}", exc_info=True)
            return df

    def post_process_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._optimize_category_processing_from_df(df)
        df = self._fix_specific_issues_from_df(df)
        
        return df