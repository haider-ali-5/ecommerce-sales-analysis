# Data

The raw Olist CSV files are **not** stored in this repository (about 120 MB in total).
Download them yourself and place them in this folder.

## 1. Download

Dataset: **Brazilian E-Commerce Public Dataset by Olist** (Kaggle)
<https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>

(Kaggle account required. Download the ZIP and extract the CSV files into `data/`.)

## 2. Expected filenames

| File | Used by |
|---|---|
| `olist_orders_dataset.csv` | Python, PostgreSQL (`orders`) |
| `olist_order_items_dataset.csv` | Python, PostgreSQL (`order_items`) |
| `olist_order_payments_dataset.csv` | Python, PostgreSQL (`order_payments`) |
| `olist_customers_dataset.csv` | Python, PostgreSQL (`customers`) |
| `olist_products_dataset.csv` | Python, PostgreSQL (`products`) |
| `olist_sellers_dataset.csv` | Python, PostgreSQL (`sellers`) |
| `olist_geolocation_dataset.csv` | PostgreSQL (`geolocation`), Power BI map |
| `product_category_name_translation.csv` | Python, PostgreSQL (`product_category_name_translation`) |
| `olist_order_reviews_dataset_clean3.csv` | Python, PostgreSQL (`order_reviews`) |

### Reviews file
`notebooks/analysis.py` reads `olist_order_reviews_dataset_clean3.csv`, a cleaned copy of the
original Kaggle file `olist_order_reviews_dataset.csv` that was prepared for the PostgreSQL import.
If you only have the original file, copy it to that name. The reviews are loaded by the script
but are not used in the KPI, RFM or chart calculations.

## 3. Generated file (committed)

`rfm_segments.csv` (about 5 MB) is **created by `notebooks/analysis.py`** and imported into
Power BI. It has one row per customer (`customer_unique_id`) with `recency`, `frequency`,
`monetary` and `segment`. The IDs are the anonymised hashes from the public Olist dataset.
Re-running the script overwrites it.
