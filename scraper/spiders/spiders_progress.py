"""
Module to create a Progress Object to keep tracking of the progress of the spiders
"""

# Import external modules
import os
import json

class Progress:
    """
    A class to manage and track the scraping progress across multiple categories and stores.

    Attributes:
        progress_file_path (str): The file path for storing the progress data.
        progress_file_default (dict): The default structure of the progress data.
    """

    progress_file_path = "utilities/json/progress_file.json"

    progress_file_default = {
    "continente_categories_scraped": [],
    "pingo_doce_categories_scraped": [],
    "auchan_categories_scraped": [],
    "activate_sellenium_to_get_categories_links": 1,

    "database_url" : "",
    "scraper_init_time": "",
    "scraped_items": 0,
    "total_categories" : {
        "continente": 0, 
        "pingo_doce": 0,
        "auchan": 0
        },
    "scraped_categories" : {
        "continente": 0,
        "pingo_doce": 0,
        "auchan": 0
        },

    "auchan_categories_dict" : {},
    "continente_subcategories_scraped":{}
    }

    def create_progress_file(self):
        """
        Creates the progress file if it doesn't already exist.
        
        If the file exists, a message is printed. If not, it initializes the file 
        with the default progress data.
        """
        with open(self.progress_file_path, 'w', encoding='utf-8') as file:
            json.dump(self.progress_file_default, file, indent=4)
        print("Progress file created.")

    def load_progress_file(self):
        """
        Loads the progress data from the file if it exists.

        Returns:
            dict: The progress data loaded from the file, or the default data if the file doesn't 
            exist.
        """
        if os.path.exists(self.progress_file_path):
            with open(self.progress_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            print("Progress file not found. Returning default progress data.")
            self.create_progress_file()

    def save_progress(self, progress_data):
        """
        Updates the progress file with the provided data.

        Args:
            progress_data (dict): The updated progress data to save.
        """
        with open(self.progress_file_path, 'w', encoding='utf-8') as file:
            json.dump(progress_data, file, indent=4)
        print("Progress file updated successfully.")
