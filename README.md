# 🛠️ ProductScraper 

![https://img.shields.io/badge/License-MIT-yellow.svg](./LICENSE)

**ProductScraper** is a scalable web scraping framework designed to collect, clean, and store product data from multiple Portuguese supermarkets (e.g., **Continente, Pingo Doce, Auchan**).  
It powers downstream applications like **SmartCart**, enabling real-time price comparison and optimized shopping lists.

--- 

## 🔥 FEATURES 
- **Multi-Site Scraping** 
  - Scrapy spiders for HTML and JSON-based APIs
  - Splash integration for JavaScript-heavy sites
- **Database Integration**
  - PostgreSQL & SQLite support with SQLAlchemy ORM
  - Automatic database versioning with timestamps
  - Deduplication logic to avoid duplicate entries
- **Scalability & Performance**
  - Batch commits of 1000 items
  - Proxy/IP rotation (Bright Data) to bypass restrictions
  - Daily scraping limits with JSON-based progress tracking
- **Data Collected**
  - Product name, brand, category
  - Quantity & packaging
  - Prices (primary & secondary units)
  - Image links
    
--- 

## 📐 TECH STACK 
  
  - **Language:** Python 3.11+ 
  - **Frameworks & Libraries:** Scrapy, SQLAlchemy, Flask 
  - **Database:** PostgreSQL / SQLite 
  - **Tools:** Splash (for dynamic pages), Bright Data (proxy rotation), JSON 

--- 

## 📂 PROJECT STRUCTURE 

```bash
ProductScraper/
├── configuration/
│ ├── base.py # Base object initialization
│ └── connection.py # Database connection handler
│
├── entities/ # Project models
│ ├── db_registry.py
│ └── product.py # SQLAlchemy models for product tables
│
├── scraper/
│ ├── spiders/ # Scrapy spiders for each store
│ │ ├── continente_spider.py
│ │ ├── pingo_doce_spider.py
│ │ ├── auchan_spider.py
│ │ └── spiders_progress.py # Spiders progress handler
│ ├── items.py # ProductItem definition
│ ├── middlewares.py # Middleware (incl. fake user-agent)
│ ├── pipelines/ # Data pipelines (deduplication, batching, DB commits)
│ └── settings.py # Scrapy settings
│
├── utilities/ # Helper functions & post-processing tools
│ ├── csv/
│ │ ├── brands.csv
│ │ ├── products.csv
│ │ └── products_cleaned.csv
│ ├── json/
│ │ ├── category_mapping.json
│ │ └── continente_categories.json
│ ├── txt/
│ │ ├── category_inconsistencies.txt
│ │ └── skipped_products.txt
│ ├── category_normalizer.py # Category normalization across stores
│ ├── data_manager.py # Data processing tools
│ ├── db_manager.py # Database handling tools
│ └── qnt_brand_extraction.py# Quantity & brand extraction
│
├── app.py # Entry point for running spiders
├── requirements.txt # Python dependencies
├── scrapy.cfg # Scrapy configuration
└── README.md
```

---

# ⚡INSTALATION

1. Clone the repository:
   ```bash
   git clone https://github.com/apecorreia/ProductScraper.git
   cd ProductScraper
   ```

2. Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

4. Configure database (PostgreSQL or SQLite) in settings.py:
    ```bash
    DATABASE_URL = "postgresql://user:password@localhost:5432/product_scraper"
    ```
  ### or SQLite example:
  
  ```bash
    DATABASE_URL = "sqlite:///path_to_db/database.db"
  ```
---

## ▶️ USAGE
- Run a specific spider:
    ```bash
    scrapy crawl continente_spider
    scrapy crawl pingo_doce_spider
    scrapy crawl auchan_spider
    ```

  ### OR

- Run all spiders at once
    ```bash
    python app.py
    ```

### 📊 Example Output
| id | store       | category  | sub_category   | name               | brand | quantity | primary_price | secondary_price | img_lnk                                                        |
| -- | ----------- | --------- | -------------- |------------------- | ----- | -------- | -------------- | ---------------- | ------------------------------------------------------------ |
| 1  | continente  | Bebidas   | Águas          | Água Mineral 1.5L  | Luso  | 1.5L     | €0.89          | €0.59/L          | [https://.../images/luso.jpg](https://.../images/luso.jpg)   |
| 2  | pingo\_doce | Mercearia | Arroz e Massas | Arroz Carolino 1kg | Pingo | 1kg      | €1.25          | €1.25/kg         | [https://.../images/arroz.jpg](https://.../images/arroz.jpg) |


NOTE: Each execution has a default limit of 10 categories per scrape process.
This can be adjusted in settings.py, but increasing it too much may result in IP bans.


---


👨‍💻 Author

Developed by António Correia
📩 Contact: [Linkedin Profile](https://www.linkedin.com/in/antónio-correia-4013242b7)
 • Email: antoniocorreia0708@gmail.com
