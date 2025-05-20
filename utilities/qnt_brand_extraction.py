
import re
import csv

class AuchanQuantityBrandExtractor:
    def __init__(self, brand_patterns_path="utilities/csv/brands.csv"):
        # Compile regex patterns
        self.patterns = {
            'weight_volume': re.compile(r'(?:^|\s)(\d+(?:[.,]\d+)?)\s*(g|gr|kg|ml|l|cl)(?:\s|$)', re.IGNORECASE),
            'multi_pack': re.compile(r'(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(g|gr|kg|ml|l|cl|un)', re.IGNORECASE),
            'units': re.compile(r'(\d+)\s*(unidades|und|un|par|doses|dúzia|dúzias|saquetas)', re.IGNORECASE),
            'dimensions': re.compile(r'(\d+)\s*x\s*(\d+)\s*cm', re.IGNORECASE),
            'net_weight': re.compile(r'\((\d+(?:[.,]\d+)?)\s*(g|gr|kg|ml|l|cl)\)', re.IGNORECASE),
            'pack_with_net_weight': re.compile(r'(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(g|gr|kg|ml|l|cl)\s*\((\d+(?:[.,]\d+)?)\s*(g|gr|kg|ml|l|cl)\)', re.IGNORECASE),
            'pack_units': re.compile(r'(\d+)\s*x\s*(\d+)\s*un', re.IGNORECASE),
            'unit_only': re.compile(r'\s(kg|g|gr|ml|l|cl)\s*$', re.IGNORECASE),
        }

        self.special_cases = {
            'uma dúzia': '12 un',
            'duas dúzias': '24 un',
            'três dúzias': '36 un',
            'meia dúzia': '6 un',
        }

        # Preload brand patterns once
        self.compiled_patterns = []
        try:
            with open(brand_patterns_path, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    brand = row[0].strip()
                    if brand:
                        pattern = re.compile(r'\b' + re.escape(brand.lower()) + r'\b')
                        self.compiled_patterns.append((brand, pattern))
        except Exception as e:
            print(f"Error reading brands file: {e}")

    def extract_info(self, item):
        product_name = item.get('name', '').lower()
        product_brand = 'Auchan'
        quantity = None

        for case, value in self.special_cases.items():
            if case in product_name:
                quantity = value
                break

        if not quantity:
            for pattern_key in ['pack_units', 'pack_with_net_weight', 'multi_pack', 'weight_volume', 'units', 'unit_only']:
                match = self.patterns[pattern_key].search(product_name)
                if match:
                    groups = match.groups()
                    if pattern_key == 'pack_units':
                        quantity = f"{groups[0]}x{groups[1]}un"
                    elif pattern_key == 'pack_with_net_weight':
                        quantity = f"{groups[0]}x{groups[1]}{groups[2]}({groups[3]}{groups[4]})"
                    elif pattern_key == 'multi_pack':
                        quantity = f"{groups[0]}x{groups[1]}{groups[2]}"
                    elif pattern_key == 'weight_volume':
                        quantity = f"{groups[0]}{groups[1]}"
                    elif pattern_key == 'units':
                        quantity = f"{groups[0]}un"
                    elif pattern_key == 'unit_only':
                        quantity = f"1{groups[0]}"
                    break

        if not quantity:
            for unit in ['kg', 'g', 'gr', 'ml', 'l', 'cl']:
                if f" {unit}" in product_name:
                    quantity = f"1{unit}"
                    break

        # Use preloaded compiled patterns
        matched_brand = None
        for brand, pattern in self.compiled_patterns:
            if pattern.search(product_name):
                matched_brand = brand
                break

        if matched_brand:
            product_brand = matched_brand
        elif "livro" in product_name:
            product_brand = None
        else:
            product_brand = "Auchan"

        return quantity, product_brand

def standardize_quantity(quantity_str, secondary_price_unit=None):
    """
    Takes a quantity string and returns a dict with:
    - quantity_value
    - quantity_unit
    - quantity_items
    - quantity_total
    """
    def convert_to_base_unit(value, unit):
        unit = unit.lower()
        if unit == 'kg':
            return value * 1000
        if unit in ['l', 'lt']:
            return value * 1000
        if unit == 'cl':
            return value * 10
        return value

    def standardize_unit(unit):
        unit = unit.lower()
        if unit in ['g', 'gr', 'kg']:
            return 'g'
        if unit in ['ml', 'l', 'lt', 'cl']:
            return 'ml'
        return 'UN'

    def empty_result():
        return {'quantity_value': 1, 'quantity_unit': 'un', 'quantity_items': 1, 'quantity_total': 1}

    if isinstance(quantity_str, (int, float)):
        if secondary_price_unit == 'KGM':
            quantity_str = f"{quantity_str}g"
        elif secondary_price_unit == 'LTR':
            quantity_str = f"{quantity_str}ml"
        else:
            quantity_str = f"{quantity_str}un"

    if not quantity_str or not isinstance(quantity_str, str):
        return empty_result()

    quantity_str = quantity_str.lower().strip()
    quantity_str = re.sub(r'\b(emb\.?|quant\. mínima =|aprox\.?|grátis|aproximadamente|cerca de)\b', '', quantity_str)
    quantity_str = quantity_str.strip()

    patterns = [
        # "1,075 gr (38 un)"
        (r'(\d+[\.,]?\d*)\s*(g|gr|ml|l|lt|cl|kg)\s*\((\d+)\s*un\)',
         lambda m: {
             'quantity_value': convert_to_base_unit(float(m[1].replace(',', '.')), m[2]) / int(m[3]),
             'quantity_unit': standardize_unit(m[2]),
             'quantity_items': int(m[3]),
             'quantity_total': convert_to_base_unit(float(m[1].replace(',', '.')), m[2])
         }),

        # "peso escorrido 41 gr"
        (r'peso\s*escorrido\s*(\d+)\s*(g|gr|ml|l|lt|cl|kg)',
         lambda m: {
             'quantity_value': convert_to_base_unit(float(m[1].replace(',', '.')), m[2]),
             'quantity_unit': standardize_unit(m[2]),
             'quantity_items': 1,
             'quantity_total': convert_to_base_unit(float(m[1].replace(',', '.')), m[2])
         }),

        # "12 x 1 lt"
        (r'(\d+)\s*x\s*(\d+[\.,]?\d*)\s*(g|gr|ml|l|lt|cl|kg)',
         lambda m: {
             'quantity_value': convert_to_base_unit(float(m[2].replace(',', '.')), m[3]),
             'quantity_unit': standardize_unit(m[3]),
             'quantity_items': int(m[1]),
             'quantity_total': int(m[1]) * convert_to_base_unit(float(m[2].replace(',', '.')), m[3])
         }),

        # "100 un + 20 GRÁTIS"
        (r'(\d+)\s*un\s*\+\s*(\d+)',
         lambda m: {
             'quantity_value': int(m[1]) + int(m[2]),
             'quantity_unit': 'un',
             'quantity_items': 1,
             'quantity_total': int(m[1]) + int(m[2])
         }),

        # "2 x emb. 10 un"
        (r'(\d+)\s*x\s*(?:emb\.)?\s*(\d+)\s*un',
         lambda m: {
             'quantity_value': int(m[2]),
             'quantity_unit': 'un',
             'quantity_items': int(m[1]),
             'quantity_total': int(m[1]) * int(m[2])
         }),

        # "40 un"
        (r'^(\d+)\s*un',
         lambda m: {
             'quantity_value': int(m[1]),
             'quantity_unit': 'un',
             'quantity_items': 1,
             'quantity_total': int(m[1])
         }),

        # "200g", "1.5kg"
        (r'(\d+[\.,]?\d*)\s*(g|gr|ml|l|lt|cl|kg)',
         lambda m: {
             'quantity_value': convert_to_base_unit(float(m[1].replace(',', '.')), m[2]),
             'quantity_unit': standardize_unit(m[2]),
             'quantity_items': 1,
             'quantity_total': convert_to_base_unit(float(m[1].replace(',', '.')), m[2])
         }),

        # "emb. 20 comprimidos"
        (r'emb\.?\s*(\d+)\s*(comprimidos|cápsulas|drageias|doses)',
         lambda m: {
             'quantity_value': int(m[1]),
             'quantity_unit': 'un',
             'quantity_items': 1,
             'quantity_total': int(m[1])
         }),

        # "90 cápsulas"
        (r'(\d+)\s*(comprimidos|cápsulas|drageias|doses)',
         lambda m: {
             'quantity_value': int(m[1]),
             'quantity_unit': 'un',
             'quantity_items': 1,
             'quantity_total': int(m[1])
         }),
    ]

    for pattern, processor in patterns:
        match = re.search(pattern, quantity_str)
        if match:
            return processor(match)

    return empty_result()
