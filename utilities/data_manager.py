import re
import pandas as pd
from nltk.corpus import stopwords
from unidecode import unidecode
import swifter
from tqdm import tqdm
import numpy as np



class DataManager:
    def __init__(self, df, brands_file_path="utilities/csv/brands.csv"):
        self.df = df

        self.quantity_pattern = re.compile(r'\b\d+\s*(g|kg|l|ml|un|gr|cl|mg|lt|litros?)\b', re.IGNORECASE)
        self.unit_range_pattern = re.compile(r'\b\d{1,3}/\d{1,3}\b')  # like 80/100
        self.certification_pattern = re.compile(r'\b(MSC|ASC|UHT|DOP|IGP|BIO|100%|Zero|Light|Integral|Um)\b', re.IGNORECASE)
        self.unit_size_pattern = re.compile(r'\b(M/L|L|XL|S|M|G|GG|EG)\b', re.IGNORECASE)
        self.number_isolated_pattern = re.compile(r'\b\d+\b')  # remove stand-alone numbers
        self.special_chars_pattern = re.compile(r'[^\w\s]', re.UNICODE)
        self.multi_space_pattern = re.compile(r'\s+')
        
        try:
            self.stopwords_set = set(stopwords.words('portuguese')).union({
            'com', 'sem', 'para', 'de', 'em', 'grande', 'pequena', 'media', 'pequeno', 'medio', "cunhaiguarias", "iguarias",
            'naco', "fatiado", "fatiados", "fatia", "fatias", "inteiro", "metade", "meio", "completo", "magro", 'uht',
            'recheio', 'recheado', "cozido", "cozidos", "congelado", "congelados", "ultracongelado", "ultracongelados", 
            "ultra-congelado", "ultra-congelados"
        })
        except LookupError:
            import nltk
            nltk.download('stopwords')
            
        finally:
            self.stopwords_set = set(stopwords.words('portuguese')).union({
            'com', 'sem', 'para', 'de', 'em', 'grande', 'pequena', 'media', 'pequeno', 'medio', "cunhaiguarias", "iguarias",
            'naco', "fatiado", "fatiados", "fatia", "fatias", "inteiro", "metade", "meio", "completo", "magro", 'uht',
            'recheio', 'recheado', "cozido", "cozidos", "congelado", "congelados", "ultracongelado", "ultracongelados", 
            "ultra-congelado", "ultra-congelados"
        })

        

        brands = pd.read_csv(brands_file_path, header=None)[0].str.lower().apply(unidecode).tolist()
        self.brand_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, brands)) + r')\b', re.IGNORECASE)

    def simplify_product_names(self, name: str, user_input=False) -> str:
        if not name or not isinstance(name, str):
            return ""

        processed = name.lower()
        processed = unidecode(processed)

        processed = self.quantity_pattern.sub('', processed)
        processed = self.unit_range_pattern.sub('', processed)
        processed = self.certification_pattern.sub('', processed)
        processed = self.unit_size_pattern.sub('', processed)
        processed = self.number_isolated_pattern.sub('', processed)
        
        if not user_input:
            processed = self.brand_pattern.sub('', processed)

        processed = self.special_chars_pattern.sub('', processed)
        processed = ' '.join(word for word in processed.split() if word not in self.stopwords_set)
        processed = self.multi_space_pattern.sub(' ', processed).strip()

        return processed

    def preprocess_all_product_names(self):
        tqdm.pandas()
        self.df["name"] = self.df["name"].astype(str).swifter.apply(self.simplify_product_names)
        

    def save_cleaned_csv(self, output_path="utilities/csv/products_cleaned.csv"):

        cleaned_df = self.df.dropna()
        cleaned_df = cleaned_df[cleaned_df["name"].str.strip() != ""]

        # Replace NaN and "nan"/"NaN" strings in 'brand' column with "Nan Brand"
        cleaned_df['brand'] = cleaned_df['brand'].fillna("Nan Brand")
        cleaned_df['brand'] = cleaned_df['brand'].replace(
            to_replace=r"(?i)^nan$", value="Nan Brand", regex=True
        )

        cleaned_df = cleaned_df[
            (cleaned_df['quantity'].str.strip() != "") &
            (cleaned_df['quantity'].str.strip().str.lower() != "null")
        ]

        cleaned_df.to_csv(output_path, index=False, encoding='utf-8')