# Olist Geospatial Analysis

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)
![GeoPandas](https://img.shields.io/badge/GeoPandas-1.0+-green)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-yellow?logo=powerbi)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## Problem Statement

In Brazilian e-commerce, geographic scale introduces hidden complexity: a seller in São Paulo and a buyer in Manaus may share an identical product category yet see radically different delivery times, freight costs, and satisfaction scores. Standard aggregate KPIs miss this spatial signal entirely.

This project applies **advanced geospatial analytics** to the public Olist dataset (100k orders, 2016–2018) to answer:
- Where do seller clusters form, and which are under-served regions?
- How does distance *locally* predict delivery time across Brazil?
- Are low-satisfaction states spatially autocorrelated (LISA clusters)?

## Key Findings

- **Seller clusters** identified via DBSCAN (eps=50 km) — highest concentration in the Southeast (São Paulo, Minas Gerais, Paraná corridor).
- GWR reveals that the effect of distance on delivery days varies significantly by region, highlighting logistics bottlenecks in the North and Northeast.
- Moran's I confirms spatial autocorrelation in satisfaction scores — low-satisfaction clusters concentrate in specific state groupings visible in the LISA map.
- **68,079 order flows** originate from São Paulo state alone (71% of total), making it the dominant logistics hub.
- Average flow distance across all OD pairs: **~1,500 km**, reflecting Brazil's continental scale.

## Architecture

```
PROYECTO_3/
├── src/                        # Reusable Python modules
│   ├── data_loader.py          # Download + cache Olist tables via kagglehub
│   ├── quality_checks.py       # Geospatial data quality validation
│   ├── geospatial_utils.py     # Haversine distance, GeoDataFrame helpers
│   └── models.py               # DBSCAN, GWR, Moran's I / LISA
├── notebooks/
│   ├── 01_eda.ipynb            # Profile all 8 tables, order timeline
│   ├── 02_data_quality.ipynb   # Null report, out-of-bounds filter, ZIP centroids
│   ├── 03_predictive_models.ipynb  # DBSCAN clustering, GWR, Moran's I / LISA
│   └── 04_powerbi_prep.ipynb   # Export 4 CSVs for the dashboard
├── outputs/
│   ├── maps/                   # Interactive Folium HTML maps
│   │   ├── seller_clusters.html
│   │   ├── gwr_coefficients.html
│   │   └── lisa_satisfaction.html
│   ├── reports/                # CSV quality reports
│   └── processed_data/         # Cached tables (git-ignored)
│       ├── orders_geo.csv
│       ├── state_summary.csv
│       ├── od_flows.csv
│       └── seller_clusters.csv
└── powerbi/
    ├── version_avanzada.pbix   # Main dashboard file
    └── screenshots/
```

## Quickstart

```bash
# 1. Create conda environment
conda env create -f environment.yml
conda activate olist-geo

# 2. Register kernel
python -m ipykernel install --user --name olist-geo --display-name "olist-geo"

# 3. Run notebooks in order
jupyter notebook notebooks/01_eda.ipynb
# → then 02_data_quality, 03_predictive_models, 04_powerbi_prep
```

Data downloads automatically via `kagglehub` on first run (requires a Kaggle account configured locally).

## Interactive Maps (Folium)

| Map | Description |
|---|---|
| `outputs/maps/seller_clusters.html` | DBSCAN clusters — interactive bubble map by seller ZIP centroid |
| `outputs/maps/gwr_coefficients.html` | GWR local coefficients — distance effect on delivery days by location |
| `outputs/maps/lisa_satisfaction.html` | LISA quadrant map — HH/LL/HL/LH satisfaction spatial clusters |

## Power BI Dashboard

File: `powerbi/version_avanzada.pbix`

| Page | Content |
|---|---|
| **Geospatial Overview** | KPI cards (orders, avg ticket, avg delivery, avg review) + bar charts by state + date/category slicers |
| **OD Flow Analysis** | Azure Maps bubble chart (flows per seller state) + Top 10 OD routes table + state slicers |
| **Satisfaction** | Satisfaction KPIs + delivery vs satisfaction bar + low-performance state indicator |

### Power BI Data Model

The dashboard uses a star-schema approach with a key dimension table to enable correct geospatial filtering:

- **`DimSellerState`** — one row per seller state (22 rows). Created as a calculated table:
  ```dax
  DimSellerState =
  DISTINCT(SELECTCOLUMNS(od_flows,
      "seller_state",      od_flows[seller_state],
      "seller_state_full", od_flows[seller_state_full],
      "Country",           od_flows[Country]
  ))
  ```
  Relationship: `od_flows[seller_state]` → `DimSellerState[seller_state]` (Many-to-One, BothDirections).
  This is required because Azure Maps needs a dimension-table field as Location to propagate filter context correctly — using a fact-table field causes all bubbles to show the grand total.

### Key DAX Measures

```dax
-- orders_geo table
Total Orders       = COUNTROWS(orders_geo)
Avg Ticket         = AVERAGE(orders_geo[price])
Avg Delivery Days  = AVERAGE(orders_geo[delivery_days])

-- state_summary table
Avg Review Score   = AVERAGE(state_summary[avg_review_score])
Low Perf States    = CALCULATE(COUNTROWS(state_summary), state_summary[avg_review_score] < 3.5)

-- od_flows table (OD Flow display folder)
Total Flows        = SUM(od_flows[count])
Avg Flow Distance  = AVERAGE(od_flows[avg_distance_km])
```

Screenshots: `powerbi/screenshots/`

## Tech Stack

| Layer | Tools |
|---|---|
| Data ingestion | `kagglehub`, `pandas` |
| Geospatial processing | `geopandas` 1.0+, `shapely` |
| Spatial statistics | `esda`, `libpysal`, `pysal` |
| Machine learning | `scikit-learn` (DBSCAN), `mgwr` (GWR) |
| Visualization | `folium`, `matplotlib`, `seaborn` |
| Dashboard | Power BI Desktop (Azure Maps, DAX, star schema) |

## Dataset

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100k orders across 8 relational tables, 2016–2018.

Raw CSVs are cached to `outputs/processed_data/` on first notebook run and are git-ignored.
